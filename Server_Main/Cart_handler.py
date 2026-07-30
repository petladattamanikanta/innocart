"""
=============================================================================
  CART OPERATIONS HANDLER — Smart Retail Cart
  File    : cart_handler.py
  Version : 1.0.0
  PURPOSE
  ───────
  Handles all basic cart lifecycle operations for the Smart Retail Cart.
  This is the PRIMARY communication layer between the ESP32-S3 and the
  server — it processes every EPC scan, manages the cart session state,
  and exposes a clean HTTP API.

  AI STYLING IS DELIBERATELY SEPARATE.
  This file never calls the StylingEngine. Styling is triggered only
  when the customer explicitly taps "Style Me" on the cart display.
  The styling endpoint lives in styling_engine.py (/api/get_style).

  WHAT THIS FILE HANDLES
  ──────────────────────
  ┌──────────────────────────────────────────────────────────────────────┐
  │  OPERATION             TRIGGER                ENDPOINT               │
  ├──────────────────────────────────────────────────────────────────────┤
  │  Scan & Add Item       EPC tag detected       POST /cart/scan        │
  │  Remove Item           EPC tag removed        POST /cart/remove      │
  │  View Cart             Customer views cart    GET  /cart/<session>   │
  │  Update Quantity       Qty change request     POST /cart/qty         │
  │  Clear Cart            Cart reset             DELETE /cart/<session> │
  │  Checkout Summary      Checkout tap           GET  /cart/<s>/summary │
  │  Health Check          ESP32 boot probe       GET  /health           │
  └──────────────────────────────────────────────────────────────────────┘

  FLOW DIAGRAM
  ────────────
  ESP32 detects EPC tag (via Arduino Mega RFID)
         │
         ▼
  POST /cart/scan   { epc_id, session_id }
         │
         ├─ Step 1: Validate session
         ├─ Step 2: EPC → SKU  (inventory_live table)
         ├─ Step 3: SKU → Product details  (product_master table)
         ├─ Step 4: Add to cart session (in-memory + DB)
         └─ Step 5: Return lightweight product card JSON to ESP32
                    { sku, name, price, image_url, cart_total,
                      item_count, already_in_cart }

  CUSTOMER TAPS "Style Me" on display
         │
         ▼
  (Handled by styling_engine.py → POST /api/get_style)
  This file does NOT get involved.

  SESSION MODEL
  ─────────────
  Each physical cart has a session_id (e.g. "CART-001").
  Sessions live in memory during the shopping trip and are written
  to the cart_sessions + cart_items tables in MySQL on every mutation.
  Sessions auto-expire after SESSION_TTL_SECONDS of inactivity.

  DATABASE TABLES USED
  ────────────────────
  READ   : inventory_live, product_master   (from smart_cart_db.sql)
  WRITE  : cart_sessions, cart_items        (created by this file's
                                             ensure_tables() on startup)

  DEPENDENCIES
  ────────────
  pip install mysql-connector-python flask
=============================================================================
"""

import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

import mysql.connector
from mysql.connector import Error as MySQLError

from flask import Flask, request, jsonify

# ── Logger ────────────────────────────────────────────────────────────────────
logger = logging.getLogger("cart_handler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter(
        "%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(_h)

# ── Constants ─────────────────────────────────────────────────────────────────
SESSION_TTL_SECONDS = 3600   # 1 hour of inactivity clears the session
MAX_QTY_PER_ITEM    = 10     # safety cap — prevents accidental bulk adds


# =============================================================================
# SECTION 1 — DATA CONTAINERS
# =============================================================================

@dataclass
class ProductCard:
    """
    Lightweight product summary returned to the ESP32 on every scan.
    Contains exactly what the cart display needs to render a cart item card.
    Nothing more.
    """
    sku:       str
    name:      str
    price:     float
    image_url: str


@dataclass
class CartLine:
    """
    A single line in the shopping cart.
    One CartLine per unique SKU. Quantity increments on repeat scans.
    """
    sku:        str
    name:       str
    price:      float      # unit price
    image_url:  str
    quantity:   int   = 1
    added_at:   str   = field(default_factory=lambda: _utc_now())

    @property
    def line_total(self) -> float:
        """price × quantity, rounded to 2 decimal places."""
        return round(self.price * self.quantity, 2)


@dataclass
class CartSession:
    """
    Represents one shopping cart's session for a customer trip.
    Keyed by session_id (e.g. "CART-001" assigned to a physical cart).
    """
    session_id:   str
    created_at:   str = field(default_factory=lambda: _utc_now())
    updated_at:   str = field(default_factory=lambda: _utc_now())
    lines:        dict = field(default_factory=dict)   # { sku: CartLine }

    # ── Computed properties ───────────────────────────────────────────────

    @property
    def item_count(self) -> int:
        """Total number of individual items (sum of quantities)."""
        return sum(line.quantity for line in self.lines.values())

    @property
    def unique_sku_count(self) -> int:
        """Number of distinct SKUs in the cart."""
        return len(self.lines)

    @property
    def cart_total(self) -> float:
        """Grand total across all lines."""
        return round(sum(line.line_total for line in self.lines.values()), 2)

    def touch(self):
        """Update the last-activity timestamp (used for TTL expiry)."""
        self.updated_at = _utc_now()

# =============================================================================
# SECTION 2 — HELPERS
# =============================================================================

def _utc_now() -> str:
    """Returns current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _session_expired(session: CartSession) -> bool:
    """
    Returns True if the session has been inactive longer than SESSION_TTL_SECONDS.
    Compares updated_at (ISO string) against the current UTC time.
    """
    try:
        last = datetime.fromisoformat(session.updated_at)
        age  = (datetime.now(timezone.utc) - last).total_seconds()
        return age > SESSION_TTL_SECONDS
    except Exception:
        return False


# =============================================================================
# SECTION 3 — DATABASE LAYER
# =============================================================================

class CartDB:
    """
    All database operations for the cart handler.
    Reads product data from the existing smart_cart schema.
    Writes cart session state to cart_sessions + cart_items tables.

    Design: every public method opens and closes its own connection.
    In production, replace with a connection pool.
    """

    # ── SQL: READ ─────────────────────────────────────────────────────────────

    _SQL_RESOLVE_EPC = """
        SELECT
            pm.sku,
            pm.name,
            pm.price,
            pm.image_url,
            pm.garment_category,
            pm.garment_type,
            pm.style_profile,
            pm.color_family
        FROM  inventory_live  il
        INNER JOIN product_master pm ON il.sku = pm.sku
        WHERE il.epc_id    = %s
          AND il.is_active = 1
          AND pm.is_active = 1
        LIMIT 1
    """

    _SQL_GET_PRODUCT_BY_SKU = """
        SELECT sku, name, price, image_url,
               garment_category, garment_type,
               style_profile, color_family
        FROM  product_master
        WHERE sku       = %s
          AND is_active = 1
        LIMIT 1
    """

    # ── SQL: WRITE (cart state persistence) ───────────────────────────────────

    _SQL_UPSERT_SESSION = """
        INSERT INTO cart_sessions (session_id, created_at, updated_at, is_active)
        VALUES (%s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE
            updated_at = VALUES(updated_at),
            is_active  = 1
    """

    _SQL_UPSERT_CART_ITEM = """
        INSERT INTO cart_items
            (session_id, sku, name, price, image_url, quantity, added_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            quantity   = VALUES(quantity),
            updated_at = VALUES(updated_at)
    """

    _SQL_DELETE_CART_ITEM = """
        DELETE FROM cart_items
        WHERE session_id = %s AND sku = %s
    """

    _SQL_CLEAR_SESSION_ITEMS = """
        DELETE FROM cart_items WHERE session_id = %s
    """

    _SQL_CLOSE_SESSION = """
        UPDATE cart_sessions
        SET    is_active = 0, updated_at = %s
        WHERE  session_id = %s
    """

    # ── Table bootstrap SQL ───────────────────────────────────────────────────
    # These tables extend smart_cart_db.sql with cart runtime state.

    _SQL_CREATE_SESSIONS_TABLE = """
        CREATE TABLE IF NOT EXISTS cart_sessions (
            session_id   VARCHAR(40)   NOT NULL,
            created_at   DATETIME      NOT NULL,
            updated_at   DATETIME      NOT NULL,
            is_active    TINYINT(1)    NOT NULL DEFAULT 1,
            CONSTRAINT pk_cart_sessions PRIMARY KEY (session_id),
            INDEX idx_cs_active (is_active)
        ) ENGINE=InnoDB COMMENT='One row per active shopping cart trip'
    """

    _SQL_CREATE_ITEMS_TABLE = """
        CREATE TABLE IF NOT EXISTS cart_items (
            id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            session_id   VARCHAR(40)   NOT NULL,
            sku          VARCHAR(20)   NOT NULL,
            name         VARCHAR(120)  NOT NULL,
            price        DECIMAL(8,2)  NOT NULL,
            image_url    VARCHAR(255)  NOT NULL,
            quantity     TINYINT UNSIGNED NOT NULL DEFAULT 1,
            added_at     DATETIME      NOT NULL,
            updated_at   DATETIME      NOT NULL,
            CONSTRAINT pk_cart_items   PRIMARY KEY (id),
            CONSTRAINT uq_session_sku  UNIQUE (session_id, sku),
            CONSTRAINT fk_ci_session   FOREIGN KEY (session_id)
                                       REFERENCES cart_sessions (session_id)
                                       ON DELETE CASCADE,
            INDEX idx_ci_session (session_id)
        ) ENGINE=InnoDB COMMENT='Line items for each cart session'
    """

    # ─────────────────────────────────────────────────────────────────────────

    def __init__(self, config: dict):
        self._config = config
        self._probe()
        self.ensure_tables()

    def _probe(self):
        """Fast startup connectivity check."""
        try:
            conn = mysql.connector.connect(**self._config)
            conn.close()
            logger.info("CartDB probe OK  db=%s", self._config.get("database"))
        except MySQLError as e:
            logger.error("CartDB probe FAILED: %s", e)
            raise

    def _conn(self):
        """Returns a fresh connection. Caller must close it."""
        return mysql.connector.connect(**self._config)

    def ensure_tables(self):
        """
        Creates cart_sessions and cart_items tables if they don't exist.
        Safe to call on every startup — uses CREATE TABLE IF NOT EXISTS.
        """
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(self._SQL_CREATE_SESSIONS_TABLE)
            cur.execute(self._SQL_CREATE_ITEMS_TABLE)
            conn.commit()
            logger.info("Cart tables verified (cart_sessions, cart_items)")
        finally:
            conn.close()

    # ── READ operations ───────────────────────────────────────────────────────

    def resolve_epc(self, epc_id: str) -> Optional[dict]:
        """
        Translates a raw UHF RFID EPC string to its full product record.
        Returns None if the EPC is unknown or inactive.

        This is a READ-ONLY operation against the existing schema —
        no cart state is modified here.
        """
        conn = self._conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(self._SQL_RESOLVE_EPC, (epc_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_product_by_sku(self, sku: str) -> Optional[dict]:
        """
        Fetches a product directly by SKU.
        Used for cart reconstruction and manual add-by-SKU flows.
        """
        conn = self._conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(self._SQL_GET_PRODUCT_BY_SKU, (sku,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ── WRITE operations ──────────────────────────────────────────────────────

    def persist_session(self, session: CartSession):
        """
        Upserts the cart session record into cart_sessions.
        Called after every mutation so the DB reflects live state.
        """
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(self._SQL_UPSERT_SESSION, (
                session.session_id,
                session.created_at,
                session.updated_at,
            ))
            conn.commit()
        finally:
            conn.close()

    def persist_cart_line(self, session_id: str, line: CartLine):
        """
        Upserts a single cart line into cart_items.
        ON DUPLICATE KEY UPDATE handles both insert (new item) and
        update (quantity change) in a single round-trip.
        """
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(self._SQL_UPSERT_CART_ITEM, (
                session_id,
                line.sku,
                line.name,
                line.price,
                line.image_url,
                line.quantity,
                line.added_at,
                _utc_now(),
            ))
            conn.commit()
        finally:
            conn.close()

    def delete_cart_line(self, session_id: str, sku: str):
        """Removes a single SKU from a cart session in the DB."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(self._SQL_DELETE_CART_ITEM, (session_id, sku))
            conn.commit()
        finally:
            conn.close()

    def clear_session(self, session_id: str):
        """
        Removes all cart_items for a session and marks the session inactive.
        Called on checkout completion or explicit cart clear.
        """
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(self._SQL_CLEAR_SESSION_ITEMS, (session_id,))
            cur.execute(self._SQL_CLOSE_SESSION, (_utc_now(), session_id))
            conn.commit()
        finally:
            conn.close()


# =============================================================================
# SECTION 4 — CART SESSION MANAGER
# =============================================================================

class CartManager:
    """
    In-memory session store with MySQL persistence.

    Responsibilities:
      • Maintain { session_id: CartSession } in memory for fast reads
      • Sync every mutation to MySQL via CartDB
      • Expire stale sessions automatically
      • Provide all cart operations: scan, remove, qty update, clear

    This class has ZERO knowledge of the AI Styling Engine.
    Styling is the customer's explicit choice and handled elsewhere.
    """

    def __init__(self, db: CartDB):
        self._db       = db
        self._sessions: dict[str, CartSession] = {}
        logger.info("CartManager ready.")

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def get_or_create_session(self, session_id: str) -> CartSession:
        """
        Returns an existing session or creates a fresh one.
        Also evicts any expired sessions from memory.
        """
        self._evict_expired()

        if session_id not in self._sessions:
            session = CartSession(session_id=session_id)
            self._sessions[session_id] = session
            self._db.persist_session(session)
            logger.info("New cart session created: %s", session_id)
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[CartSession]:
        """
        Returns an existing session, or None if it doesn't exist / has expired.
        """
        self._evict_expired()
        return self._sessions.get(session_id)

    def clear_session(self, session_id: str) -> bool:
        """
        Clears all items from a cart session (checkout or explicit reset).
        Returns True if the session existed, False if it wasn't found.
        """
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]
        self._db.clear_session(session_id)
        logger.info("Cart session cleared: %s", session_id)
        return True

    def _evict_expired(self):
        """Removes sessions that have exceeded SESSION_TTL_SECONDS inactivity."""
        expired = [
            sid for sid, sess in self._sessions.items()
            if _session_expired(sess)
        ]
        for sid in expired:
            logger.info("Session expired and evicted: %s", sid)
            del self._sessions[sid]

    # ── Cart operations ───────────────────────────────────────────────────────

    def scan_and_add(self, session_id: str, epc_id: str) -> dict:
        """
        Core operation — called every time the ESP32 detects a new EPC tag.

        Flow:
          1. Resolve EPC → product details from DB
          2. Get or create the cart session
          3. If item already in cart → increment quantity
             If new item → add as a new line
          4. Persist the mutation to MySQL
          5. Return a lightweight response for the ESP32 display

        Args:
            session_id : Physical cart identifier (e.g. "CART-001").
            epc_id     : Raw EPC string from the UHF RFID reader.

        Returns:
            dict with scan result for ESP32 rendering.

        Raises:
            EPCNotFoundError : EPC not in inventory_live.
            CartError        : Any operational fault.
        """
        # Step 1 — EPC resolution (NO AI, just a DB lookup)
        product = self._db.resolve_epc(epc_id)
        if not product:
            raise EPCNotFoundError(
                f"EPC '{epc_id}' is not registered in inventory or is inactive."
            )

        sku = product["sku"]

        # Step 2 — Get/create session
        session = self.get_or_create_session(session_id)

        # Step 3 — Add or increment
        already_in_cart = sku in session.lines

        if already_in_cart:
            # Increment quantity (capped at MAX_QTY_PER_ITEM)
            line = session.lines[sku]
            if line.quantity >= MAX_QTY_PER_ITEM:
                logger.warning(
                    "Max quantity reached for SKU %s in session %s", sku, session_id
                )
                return self._scan_response(
                    product, session,
                    already_in_cart=True,
                    qty_capped=True,
                )
            line.quantity += 1
            logger.info(
                "Qty incremented: session=%s  sku=%s  qty=%d",
                session_id, sku, line.quantity,
            )
        else:
            # New item — create a fresh CartLine
            line = CartLine(
                sku=sku,
                name=product["name"],
                price=float(product["price"]),
                image_url=product["image_url"],
                quantity=1,
            )
            session.lines[sku] = line
            logger.info(
                "Item added: session=%s  sku=%s  name=%s",
                session_id, sku, product["name"],
            )

        # Step 4 — Persist
        session.touch()
        self._db.persist_session(session)
        self._db.persist_cart_line(session_id, session.lines[sku])

        # Step 5 — Return display response
        return self._scan_response(product, session, already_in_cart=already_in_cart)

    def remove_item(self, session_id: str, sku: str) -> dict:
        """
        Removes a specific SKU from the cart entirely.
        Called when the ESP32 detects an item was physically taken out.

        Args:
            session_id : Cart session identifier.
            sku        : SKU to remove.

        Returns:
            Updated cart summary.

        Raises:
            SessionNotFoundError : No active session for this cart.
            ItemNotFoundError    : SKU not currently in the cart.
        """
        session = self.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"No active session '{session_id}'.")

        if sku not in session.lines:
            raise ItemNotFoundError(
                f"SKU '{sku}' is not in cart session '{session_id}'."
            )

        removed_name = session.lines[sku].name
        del session.lines[sku]
        session.touch()

        # Persist deletion
        self._db.delete_cart_line(session_id, sku)
        self._db.persist_session(session)

        logger.info(
            "Item removed: session=%s  sku=%s  name=%s",
            session_id, sku, removed_name,
        )

        return {
            "status":       "removed",
            "removed_sku":  sku,
            "removed_name": removed_name,
            "item_count":   session.item_count,
            "cart_total":   session.cart_total,
        }

    def update_quantity(self, session_id: str, sku: str, quantity: int) -> dict:
        """
        Sets a specific quantity for a line item.
        If quantity <= 0, the item is removed entirely.

        Args:
            session_id : Cart session identifier.
            sku        : SKU to update.
            quantity   : New quantity (0 = remove).

        Returns:
            Updated line item summary.
        """
        session = self.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"No active session '{session_id}'.")

        if sku not in session.lines:
            raise ItemNotFoundError(
                f"SKU '{sku}' is not in cart session '{session_id}'."
            )

        if quantity <= 0:
            # Treat as a remove
            return self.remove_item(session_id, sku)

        # Cap at max
        quantity = min(quantity, MAX_QTY_PER_ITEM)

        line          = session.lines[sku]
        line.quantity = quantity
        session.touch()

        self._db.persist_cart_line(session_id, line)
        self._db.persist_session(session)

        logger.info(
            "Qty updated: session=%s  sku=%s  qty=%d", session_id, sku, quantity
        )

        return {
            "status":     "updated",
            "sku":        sku,
            "name":       line.name,
            "quantity":   line.quantity,
            "line_total": line.line_total,
            "cart_total": session.cart_total,
            "item_count": session.item_count,
        }

    def get_cart_contents(self, session_id: str) -> dict:
        """
        Returns the full cart contents for a session.
        Called when the customer views the cart screen on the ESP32 display.

        Args:
            session_id : Cart session identifier.

        Returns:
            Complete cart state dict.
        """
        session = self.get_session(session_id)
        if not session:
            # Return empty cart — session may have expired or not started yet
            return {
                "session_id": session_id,
                "status":     "empty",
                "items":      [],
                "item_count": 0,
                "cart_total": 0.0,
                "created_at": None,
                "updated_at": None,
            }

        return {
            "session_id": session.session_id,
            "status":     "active",
            "items": [
                {
                    "sku":        line.sku,
                    "name":       line.name,
                    "price":      line.price,
                    "image_url":  line.image_url,
                    "quantity":   line.quantity,
                    "line_total": line.line_total,
                    "added_at":   line.added_at,
                }
                for line in session.lines.values()
            ],
            "item_count": session.item_count,
            "cart_total": session.cart_total,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

    def get_checkout_summary(self, session_id: str) -> dict:
        """
        Returns a final checkout-ready summary.
        Called when the customer taps "Checkout" on the display.
        This does NOT clear the cart — confirmation is a separate step.

        Args:
            session_id : Cart session identifier.

        Returns:
            Checkout summary dict with itemised breakdown and totals.
        """
        session = self.get_session(session_id)
        if not session or not session.lines:
            raise CartError(f"No active cart found for session '{session_id}'.")

        lines_summary = [
            {
                "sku":        line.sku,
                "name":       line.name,
                "unit_price": line.price,
                "quantity":   line.quantity,
                "line_total": line.line_total,
            }
            for line in session.lines.values()
        ]

        return {
            "session_id":   session_id,
            "items":        lines_summary,
            "unique_skus":  session.unique_sku_count,
            "item_count":   session.item_count,
            "cart_total":   session.cart_total,
            "generated_at": _utc_now(),
            # Hint to the ESP32 UI: this is read-only; send /cart/<id>/confirm to finalise
            "next_action":  f"POST /cart/{session_id}/confirm",
        }

    # ── Response builder ──────────────────────────────────────────────────────

    @staticmethod
    def _scan_response(
        product: dict,
        session: CartSession,
        already_in_cart: bool = False,
        qty_capped: bool = False,
    ) -> dict:
        """
        Builds the lightweight JSON response sent back to the ESP32
        immediately after a successful scan.

        The ESP32 uses this to:
          • Render the scanned item card (name, price, image)
          • Update the cart badge (item_count, cart_total)
          • Show "Already in cart" state if applicable

        Note: This response intentionally contains NO style suggestions.
        The customer must explicitly tap "Style Me" to trigger the AI engine.
        """
        sku  = product["sku"]
        line = session.lines.get(sku)

        return {
            # ── Scanned item details (for the item card on display) ────────
            "sku":            sku,
            "name":           product["name"],
            "price":          float(product["price"]),
            "image_url":      product["image_url"],
            "garment_type":   product.get("garment_type", ""),
            "style_profile":  product.get("style_profile", ""),
            "color_family":   product.get("color_family", ""),

            # ── Cart state (for the cart badge / header) ───────────────────
            "quantity":       line.quantity if line else 1,
            "line_total":     line.line_total if line else float(product["price"]),
            "cart_total":     session.cart_total,
            "item_count":     session.item_count,

            # ── Scan status flags ──────────────────────────────────────────
            "already_in_cart": already_in_cart,
            "qty_capped":      qty_capped,

            # ── Style suggestion hint (UI hint only — NOT a suggestion) ────
            # The ESP32 display uses this to show/hide the "Style Me" button.
            # Actual AI suggestions are fetched only when the customer taps it.
            "style_available": True,
        }


# =============================================================================
# SECTION 5 — CUSTOM EXCEPTIONS
# =============================================================================

class CartError(Exception):
    """Base exception for cart operations (HTTP 500)."""
    http_status = 500

class EPCNotFoundError(CartError):
    """EPC not in inventory_live (HTTP 404)."""
    http_status = 404

class SessionNotFoundError(CartError):
    """No active session for this cart ID (HTTP 404)."""
    http_status = 404

class ItemNotFoundError(CartError):
    """SKU not present in the session (HTTP 404)."""
    http_status = 404

class InvalidInputError(CartError):
    """Bad request payload (HTTP 400)."""
    http_status = 400


# =============================================================================
# SECTION 6 — FLASK APPLICATION
# =============================================================================

from flask_cors import CORS
flask_app = Flask(__name__)
CORS(flask_app)   # ← add this line

# ── Database & manager singletons ─────────────────────────────────────────────
# PRODUCTION: load credentials from environment variables.
#
#   import os
#   DB_CONFIG = {
#       "host":     os.environ["DB_HOST"],
#       "port":     int(os.environ.get("DB_PORT", 3306)),
#       "user":     os.environ["DB_USER"],
#       "password": os.environ["DB_PASSWORD"],
#       "database": os.environ["DB_NAME"],
#   }

DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "cart_user",
    "password": "yourpassword",
    "database": "smart_cart",
}

_db:      Optional[CartDB]      = None
_manager: Optional[CartManager] = None


def get_manager() -> CartManager:
    """Lazy singleton — initialised on first request."""
    global _db, _manager
    if _manager is None:
        _db      = CartDB(DB_CONFIG)
        _manager = CartManager(_db)
    return _manager


def _error(msg: str, status: int) -> tuple:
    return jsonify({"error": True, "message": msg}), status


def _validate_fields(data: dict, required: list) -> Optional[str]:
    """Returns an error message string if any required fields are missing."""
    missing = [f for f in required if not data.get(f)]
    return f"Missing required fields: {missing}" if missing else None


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 1: GET /health
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/health", methods=["GET"])
def health():
    """
    Liveness probe.
    The ESP32 calls this at boot to confirm the server is reachable and
    the DB connection is healthy before starting any cart operations.

    Response 200:
      { "status": "ok", "active_sessions": N, "timestamp": "..." }
    Response 503:
      { "status": "error", "detail": "..." }
    """
    try:
        mgr = get_manager()
        mgr._manager_db_check = True   # triggers lazy init if needed
        return jsonify({
            "status":          "ok",
            "active_sessions": len(mgr._sessions),
            "timestamp":       _utc_now(),
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 503


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 2: POST /cart/scan
#
# PRIMARY ENDPOINT — called every time the Arduino Mega reads an EPC tag.
# This is the most frequent operation in the entire system.
#
# Request:
#   {
#     "session_id": "CART-001",
#     "epc_id":     "E200009"
#   }
#
# Success Response 200:
#   {
#     "sku":             "KRT-MRN-LNN",
#     "name":            "Ember Maroon Linen Kurta",
#     "price":           1799.0,
#     "image_url":       "https://...",
#     "garment_type":    "Kurta",
#     "style_profile":   "Ethnic",
#     "color_family":    "Maroon",
#     "quantity":        1,
#     "line_total":      1799.0,
#     "cart_total":      1799.0,
#     "item_count":      1,
#     "already_in_cart": false,
#     "qty_capped":      false,
#     "style_available": true      ← ESP32 uses this to show the "Style Me" button
#   }
#
# NOTE: style_available = true is a UI HINT only.
# The ESP32 shows the "Style Me" button but does NOT auto-call the AI engine.
# The AI engine is invoked ONLY when the customer explicitly taps "Style Me".
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/cart/scan", methods=["POST"])
def scan_item():
    """
    EPC tag scanned → add/increment item in cart.
    NO AI styling is performed here.
    """
    data = request.get_json(force=True, silent=True) or {}
    err  = _validate_fields(data, ["session_id", "epc_id"])
    if err:
        return _error(err, 400)

    session_id = str(data["session_id"]).strip()
    epc_id     = str(data["epc_id"]).strip()

    try:
        result = get_manager().scan_and_add(session_id, epc_id)
        return jsonify(result), 200

    except EPCNotFoundError   as e: return _error(str(e), 404)
    except CartError          as e: return _error(str(e), e.http_status)
    except Exception          as e:
        logger.exception("Unexpected error in /cart/scan")
        return _error(f"Internal server error: {e}", 500)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 3: POST /cart/remove
#
# Called when the ESP32 detects an item was physically removed from the cart
# (RFID tag no longer present), OR when the customer taps "Remove" on the UI.
#
# Request:
#   { "session_id": "CART-001", "sku": "KRT-MRN-LNN" }
#
# Response 200:
#   { "status": "removed", "removed_sku": "...", "removed_name": "...",
#     "item_count": N, "cart_total": X.XX }
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/cart/remove", methods=["POST"])
def remove_item():
    """Remove a specific SKU from the active cart session."""
    data = request.get_json(force=True, silent=True) or {}
    err  = _validate_fields(data, ["session_id", "sku"])
    if err:
        return _error(err, 400)

    session_id = str(data["session_id"]).strip()
    sku        = str(data["sku"]).strip()

    try:
        result = get_manager().remove_item(session_id, sku)
        return jsonify(result), 200

    except (SessionNotFoundError, ItemNotFoundError) as e:
        return _error(str(e), 404)
    except CartError as e:
        return _error(str(e), e.http_status)
    except Exception as e:
        logger.exception("Unexpected error in /cart/remove")
        return _error(f"Internal server error: {e}", 500)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 4: POST /cart/qty
#
# Called when the customer manually adjusts quantity on the display
# (e.g. taps + / − buttons).
# Setting quantity to 0 removes the item.
#
# Request:
#   { "session_id": "CART-001", "sku": "KRT-MRN-LNN", "quantity": 2 }
#
# Response 200:
#   { "status": "updated", "sku": "...", "quantity": 2,
#     "line_total": X.XX, "cart_total": X.XX, "item_count": N }
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/cart/qty", methods=["POST"])
def update_quantity():
    """Set an explicit quantity for a cart line item."""
    data = request.get_json(force=True, silent=True) or {}
    err  = _validate_fields(data, ["session_id", "sku"])
    if err:
        return _error(err, 400)

    if "quantity" not in data:
        return _error("Missing required field: 'quantity'", 400)

    try:
        quantity = int(data["quantity"])
    except (TypeError, ValueError):
        return _error("'quantity' must be an integer.", 400)

    session_id = str(data["session_id"]).strip()
    sku        = str(data["sku"]).strip()

    try:
        result = get_manager().update_quantity(session_id, sku, quantity)
        return jsonify(result), 200

    except (SessionNotFoundError, ItemNotFoundError) as e:
        return _error(str(e), 404)
    except CartError as e:
        return _error(str(e), e.http_status)
    except Exception as e:
        logger.exception("Unexpected error in /cart/qty")
        return _error(f"Internal server error: {e}", 500)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 5: GET /cart/<session_id>
#
# Returns the full cart contents for a given session.
# Called when the customer swipes to the "My Cart" screen on the display.
#
# Response 200:
#   {
#     "session_id": "CART-001",
#     "status":     "active",
#     "items":      [ { sku, name, price, image_url, quantity, line_total }, ... ],
#     "item_count": N,
#     "cart_total": X.XX,
#     "created_at": "...",
#     "updated_at": "..."
#   }
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/cart/<session_id>", methods=["GET"])
def get_cart(session_id: str):
    """Return full cart contents for a session."""
    try:
        result = get_manager().get_cart_contents(session_id.strip())
        return jsonify(result), 200
    except Exception as e:
        logger.exception("Unexpected error in GET /cart/<session_id>")
        return _error(f"Internal server error: {e}", 500)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 6: GET /cart/<session_id>/summary
#
# Returns the checkout-ready summary.
# Called when the customer taps "Checkout" — renders the final bill screen.
# This does NOT finalise the purchase; it's read-only.
#
# Response 200:
#   {
#     "session_id":   "CART-001",
#     "items":        [ { sku, name, unit_price, quantity, line_total }, ... ],
#     "unique_skus":  N,
#     "item_count":   N,
#     "cart_total":   X.XX,
#     "generated_at": "...",
#     "next_action":  "POST /cart/CART-001/confirm"
#   }
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/cart/<session_id>/summary", methods=["GET"])
def checkout_summary(session_id: str):
    """Return checkout summary for the final bill screen."""
    try:
        result = get_manager().get_checkout_summary(session_id.strip())
        return jsonify(result), 200
    except CartError as e:
        return _error(str(e), e.http_status)
    except Exception as e:
        logger.exception("Unexpected error in GET /cart/<session_id>/summary")
        return _error(f"Internal server error: {e}", 500)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 7: DELETE /cart/<session_id>
#
# Clears the cart and closes the session.
# Called after checkout confirmation or when the customer resets the cart.
#
# Response 200:
#   { "status": "cleared", "session_id": "CART-001" }
# Response 404:
#   { "error": true, "message": "No active session '...'" }
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/cart/<session_id>", methods=["DELETE"])
def clear_cart(session_id: str):
    """Clear and close a cart session (post-checkout or manual reset)."""
    try:
        success = get_manager().clear_session(session_id.strip())
        if not success:
            return _error(f"No active session '{session_id}'.", 404)
        return jsonify({"status": "cleared", "session_id": session_id}), 200
    except Exception as e:
        logger.exception("Unexpected error in DELETE /cart/<session_id>")
        return _error(f"Internal server error: {e}", 500)


# =============================================================================
# SECTION 7 — ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    print("=" * 65)
    print("  Smart Retail Cart — Cart Operations Handler  v1.0.0")
    print()
    print("  POST   /cart/scan              ← EPC scanned by RFID")
    print("  POST   /cart/remove            ← Item removed from cart")
    print("  POST   /cart/qty               ← Customer adjusts quantity")
    print("  GET    /cart/<session_id>      ← View cart screen")
    print("  GET    /cart/<session_id>/summary  ← Checkout screen")
    print("  DELETE /cart/<session_id>      ← Clear cart / post-checkout")
    print("  GET    /health                 ← ESP32 boot probe")
    print()
    print("  AI Styling  →  styling_engine.py  POST /api/get_style")
    print("  (Triggered only on explicit customer tap — not here)")
    print("=" * 65)

    flask_app.run(host="0.0.0.0", port=5001, debug=True)