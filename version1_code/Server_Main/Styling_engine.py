"""
=============================================================================
  AI STYLING ENGINE  —  Smart Retail Cart
  File    : styling_engine.py
  Version : 3.0.0  (Database-Driven Edition)

  PURPOSE
  ───────
  Standalone AI module that powers the recommendation logic for the Smart
  Retail Cart backend.  All scoring weights, pairing rules, color matrices,
  and skin-tone tables are read directly from the MySQL database defined in
  smart_cart_db.sql — zero hardcoded dicts anywhere in this file.

  INTEGRATION
  ───────────
  from styling_engine import StylingEngine

  engine = StylingEngine(db_config)          # build once at app startup
  result = engine.recommend(
      epc_id         = "E200009",
      user_style     = "Ethnic",
      user_skin_tone = "Warm",
      top_n          = 3,
  )

  PIPELINE (per recommendation call)
  ───────────────────────────────────
  ┌─────────────────────────────────────────────────────────────────┐
  │  EPC  ──► resolve_epc()     ──► cart_item (CartItem)            │
  │                │                                                │
  │         Phase A  load_scoring_tables()  (cached at startup)     │
  │                │                                                │
  │         Phase B  anatomy_filter()                               │
  │                  pairing_rules table ──► valid candidates        │
  │                │                                                │
  │         Phase C  score_all_candidates()                         │
  │                  ① style_match        +50 pts                   │
  │                  ② color_harmony      ±30 pts  (PRIMARY)        │
  │                  ③ skin_tone_synergy  + 0..30  (SECONDARY)      │
  │                  ④ aesthetic_bonus    + 0..20                   │
  │                │                                                │
  │         Phase D  rank_and_format()  ──► top-N JSON-ready dicts  │
  └─────────────────────────────────────────────────────────────────┘

  SCORE CEILING
  ─────────────
  Style 50 + Harmony 30 + Skin 30 + Aesthetic 20  =  130 pts (max)

  DATABASE TABLES CONSUMED
  ────────────────────────
  • inventory_live        EPC  →  SKU
  • product_master        SKU  →  full garment details
  • pairing_rules         anatomy filter (cart_type → valid candidate_types)
  • color_harmony         outfit color matrix
  • skin_tone_synergy     skin tone × color bonuses
  • aesthetic_bonus       cinematic combo bonuses

  DEPENDENCIES
  ────────────
  pip install mysql-connector-python flask
=============================================================================
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import mysql.connector
from mysql.connector import Error as MySQLError

# ── Module-level logger ───────────────────────────────────────────────────────
logger = logging.getLogger("styling_engine")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter(
        "%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(_h)


# =============================================================================
# SECTION 1 — TYPED DATA CONTAINERS
# =============================================================================

@dataclass
class CartItem:
    """
    Represents the product that was physically scanned from the cart.
    Populated by _resolve_epc() — wraps one product_master row.
    """
    sku:              str
    name:             str
    price:            float
    garment_category: str
    garment_type:     str
    style_profile:    str
    color_family:     str
    image_url:        str


@dataclass
class Candidate:
    """
    A product being evaluated for recommendation.
    Holds all scoring attributes fetched from product_master.
    score and match_reason are filled in by the scoring engine.
    """
    sku:              str
    name:             str
    price:            float
    garment_category: str
    garment_type:     str
    style_profile:    str
    color_family:     str
    image_url:        str
    score:            int  = 0
    match_reason:     str  = ""


@dataclass
class ScoringTables:
    """
    In-memory cache of all scoring configuration tables fetched from MySQL.
    Loaded once at engine initialisation and refreshed via reload_scoring_tables().

    Structure:
      pairing_rules     : { cart_type: [candidate_type, ...] }
      color_harmony     : { (source_color, target_color): score }
      skin_tone_synergy : { (skin_tone, color_family): score }
      aesthetic_bonus   : { (cart_color, candidate_color): score }
    """
    pairing_rules:     dict = field(default_factory=dict)
    color_harmony:     dict = field(default_factory=dict)
    skin_tone_synergy: dict = field(default_factory=dict)
    aesthetic_bonus:   dict = field(default_factory=dict)


@dataclass
class Recommendation:
    """
    Final recommendation payload — fully JSON-serialisable.
    Returned as a list by StylingEngine.recommend().
    """
    rank:            int
    recommended_sku: str
    name:            str
    price:           float
    image_url:       str
    garment_type:    str
    color_family:    str
    match_reason:    str
    score:           int     # keep for debug; strip for MCU sends in production


# =============================================================================
# SECTION 2 — CUSTOM EXCEPTIONS
# =============================================================================

class StylingEngineError(Exception):
    """Base exception for all engine faults (maps to HTTP 500)."""
    http_status = 500

class EPCNotFoundError(StylingEngineError):
    """EPC tag absent from inventory_live or linked product inactive (HTTP 404)."""
    http_status = 404

class NoCandidatesError(StylingEngineError):
    """Anatomy filter returned empty pool (HTTP 422)."""
    http_status = 422


# =============================================================================
# SECTION 3 — DATABASE POOL
# =============================================================================

class DBPool:
    """
    Thin MySQL connection wrapper.
    In production, replace with mysql.connector.pooling.MySQLConnectionPool
    or SQLAlchemy for higher concurrency and connection reuse.

    Args:
        config : Dict accepted by mysql.connector.connect().
                 Required keys: host, port, user, password, database
    """

    def __init__(self, config: dict):
        self._config = config
        self._probe()

    def _probe(self):
        """Open + close a test connection at startup so failures are immediate."""
        try:
            conn = mysql.connector.connect(**self._config)
            conn.close()
            logger.info(
                "DB probe OK  host=%s  db=%s",
                self._config.get("host"),
                self._config.get("database"),
            )
        except MySQLError as e:
            logger.error("DB probe FAILED: %s", e)
            raise

    def query(self, sql: str, params: tuple = ()) -> list:
        """
        Execute a SELECT and return results as a list of dicts.

        Args:
            sql    : Parameterised SQL string (use %s placeholders).
            params : Tuple of bind values.

        Returns:
            List of row dicts keyed by column name.
        """
        conn = cursor = None
        try:
            conn   = mysql.connector.connect(**self._config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            if cursor: cursor.close()
            if conn:   conn.close()


# =============================================================================
# SECTION 4 — AI STYLING ENGINE  (core class)
# =============================================================================

class StylingEngine:
    """
    Core AI recommendation engine for the Smart Retail Cart.

    Responsibilities
    ────────────────
    • Resolve EPC tags to CartItem records via MySQL JOIN
    • Cache scoring tables from MySQL (pairing rules, color matrix, skin tone, aesthetic)
    • Run 4-stage sequential scoring pipeline on anatomy-filtered candidates
    • Return ranked, JSON-ready Recommendation objects

    Typical usage
    ─────────────
        engine = StylingEngine(db_config)
        result = engine.recommend("E200009", "Ethnic", "Warm", top_n=3)

    To hot-reload scoring weights after a DB change (no restart needed):
        engine.reload_scoring_tables()
    """

    # ── Centralised SQL strings ───────────────────────────────────────────────
    # Keeping all queries here makes them easy to audit, mock in tests,
    # or swap for stored procedure calls.

    _SQL_RESOLVE_EPC = """
        SELECT
            pm.sku,
            pm.name,
            pm.price,
            pm.garment_category,
            pm.garment_type,
            pm.style_profile,
            pm.color_family,
            pm.image_url
        FROM  inventory_live  il
        INNER JOIN product_master pm ON il.sku = pm.sku
        WHERE il.epc_id    = %s
          AND il.is_active = 1
          AND pm.is_active = 1
        LIMIT 1
    """

    _SQL_ALL_ACTIVE_PRODUCTS = """
        SELECT
            sku, name, price,
            garment_category, garment_type,
            style_profile, color_family, image_url
        FROM  product_master
        WHERE is_active = 1
    """

    _SQL_PAIRING_RULES    = "SELECT cart_type, candidate_type FROM pairing_rules ORDER BY cart_type"
    _SQL_COLOR_HARMONY    = "SELECT source_color, target_color, harmony_score FROM color_harmony"
    _SQL_SKIN_SYNERGY     = "SELECT skin_tone, color_family, synergy_score FROM skin_tone_synergy"
    _SQL_AESTHETIC_BONUS  = "SELECT cart_color, candidate_color, bonus_score FROM aesthetic_bonus"

    # ─────────────────────────────────────────────────────────────────────────

    def __init__(self, db_config: dict):
        """
        Initialise the engine: open DB pool, load scoring tables.

        Args:
            db_config : mysql.connector config dict.
                        { host, port, user, password, database }
        """
        self._db     = DBPool(db_config)
        self._tables = ScoringTables()
        self.reload_scoring_tables()
        logger.info("StylingEngine ready.")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def recommend(
        self,
        epc_id:         str,
        user_style:     str,
        user_skin_tone: str,
        top_n:          int = 3,
    ) -> dict:
        """
        Full recommendation pipeline entry point.

        Args:
            epc_id         : Raw UHF RFID EPC string from the Arduino Mega.
            user_style     : "Streetwear" | "Ethnic" | "Minimalist"
            user_skin_tone : "Warm" | "Cool" | "Neutral"
            top_n          : Number of ranked suggestions to return.

        Returns:
            {
              "cart_item"   : { sku, name, price, ... },
              "suggestions" : [ { rank, recommended_sku, name, price,
                                  image_url, garment_type, color_family,
                                  match_reason, _score }, ... ],
              "meta"        : { pipeline stats }
            }

        Raises:
            EPCNotFoundError  : EPC unknown or inactive.
            NoCandidatesError : No valid pairings for this garment type.
            StylingEngineError: DB or general fault.
        """
        logger.info(
            "recommend() ► epc=%s  style=%s  skin=%s  top_n=%d",
            epc_id, user_style, user_skin_tone, top_n,
        )

        # ── Phase A: EPC → CartItem ──────────────────────────────────────
        cart_item = self._resolve_epc(epc_id)

        # ── Phase B: Anatomy filter ──────────────────────────────────────
        candidates = self._anatomy_filter(cart_item)
        if not candidates:
            raise NoCandidatesError(
                f"No valid anatomical pairings found for garment type "
                f"'{cart_item.garment_type}'. "
                f"Add products or pairing rules to the database."
            )

        # ── Phase C: Score all candidates ────────────────────────────────
        scored = self._score_all(candidates, cart_item, user_style, user_skin_tone)

        # ── Phase D: Rank + format ───────────────────────────────────────
        top = self._rank_and_format(scored, top_n)

        return {
            "cart_item":  self._cart_item_to_dict(cart_item),
            "suggestions":[self._rec_to_dict(r) for r in top],
            "meta": {
                "total_candidates_filtered": len(candidates),
                "total_candidates_scored":   len(scored),
                "top_n_returned":            len(top),
                "max_possible_score":        130,
            },
        }

    def reload_scoring_tables(self) -> None:
        """
        Re-fetches all four scoring tables from MySQL into memory.
        Call after any DB update to scoring weights — no server restart needed.
        """
        logger.info("Loading scoring tables from MySQL …")
        self._tables = self._load_scoring_tables()
        logger.info(
            "Scoring tables loaded — rules=%d  harmony=%d  skin=%d  aesthetic=%d",
            sum(len(v) for v in self._tables.pairing_rules.values()),
            len(self._tables.color_harmony),
            len(self._tables.skin_tone_synergy),
            len(self._tables.aesthetic_bonus),
        )

    # =========================================================================
    # PHASE A — EPC RESOLUTION
    # =========================================================================

    def _resolve_epc(self, epc_id: str) -> CartItem:
        """
        Translates raw EPC tag → full CartItem via a two-table JOIN.

        SQL:  inventory_live.epc_id
               → inventory_live.sku
               → product_master.*

        Raises:
            EPCNotFoundError : EPC absent or inactive.
        """
        try:
            rows = self._db.query(self._SQL_RESOLVE_EPC, (epc_id,))
        except MySQLError as e:
            raise StylingEngineError(f"DB error during EPC resolution: {e}") from e

        if not rows:
            raise EPCNotFoundError(
                f"EPC '{epc_id}' is not registered in inventory_live, "
                f"or its linked product is marked inactive."
            )

        r = rows[0]
        return CartItem(
            sku=r["sku"],
            name=r["name"],
            price=float(r["price"]),
            garment_category=r["garment_category"],
            garment_type=r["garment_type"],
            style_profile=r["style_profile"],
            color_family=r["color_family"],
            image_url=r["image_url"],
        )

    # =========================================================================
    # PHASE B — ANATOMY FILTER
    # =========================================================================

    def _anatomy_filter(self, cart_item: CartItem) -> list:
        """
        Filters the full active product catalogue to anatomically valid
        recommendation candidates.

        Logic:
          • Look up cart_item.garment_type in the in-memory pairing_rules cache.
          • Keep only products whose garment_type appears in the allowed list.
          • If no rule is defined for this cart type, pass ALL products through
            (open-filter fallback).
          • Always exclude the cart item itself (same SKU).

        Returns:
            List of Candidate objects.
        """
        try:
            rows = self._db.query(self._SQL_ALL_ACTIVE_PRODUCTS)
        except MySQLError as e:
            raise StylingEngineError(f"DB error fetching product catalogue: {e}") from e

        allowed = self._tables.pairing_rules.get(cart_item.garment_type)

        candidates = []
        for r in rows:
            if r["sku"] == cart_item.sku:
                continue  # never recommend the scanned item back to the user
            if allowed is not None and r["garment_type"] not in allowed:
                continue  # anatomy rule violated — skip
            candidates.append(Candidate(
                sku=r["sku"],
                name=r["name"],
                price=float(r["price"]),
                garment_category=r["garment_category"],
                garment_type=r["garment_type"],
                style_profile=r["style_profile"],
                color_family=r["color_family"],
                image_url=r["image_url"],
            ))

        logger.debug(
            "anatomy_filter: cart_type='%s'  allowed=%s  candidates=%d",
            cart_item.garment_type, allowed, len(candidates),
        )
        return candidates

    # =========================================================================
    # PHASE C — 4-STAGE SCORING ENGINE
    # =========================================================================

    def _score_all(
        self,
        candidates:    list,
        cart_item:     CartItem,
        user_style:    str,
        user_skin_tone: str,
    ) -> list:
        """
        Applies the 4-stage scoring pipeline to every candidate.
        Mutates each Candidate's .score and .match_reason in place.

        Scoring sequence (order is intentional and load-bearing):
          ① Style Match          +50 pts
          ② Outfit Color Harmony ±30 pts  ← PRIMARY color check
          ③ Skin Tone Synergy    +0..30   ← SECONDARY color check (runs AFTER ②)
          ④ Aesthetic Bonus      +0..20
        """
        for candidate in candidates:
            score, reason = self._score_one(
                candidate, cart_item, user_style, user_skin_tone
            )
            candidate.score        = score
            candidate.match_reason = reason
        return candidates

    def _score_one(
        self,
        candidate:      Candidate,
        cart_item:      CartItem,
        user_style:     str,
        user_skin_tone: str,
    ) -> tuple:
        """
        Scores a single candidate against the cart item and user profile.

        All score values are sourced from the MySQL-backed ScoringTables cache.

        Returns:
            (total_score: int, match_reason: str)
        """
        score        = 0
        reason_parts = []   # natural-language sentence fragments

        cart_color  = cart_item.color_family
        cand_color  = candidate.color_family
        cart_type   = cart_item.garment_type.lower()

        # ─────────────────────────────────────────────────────────────────
        # ① STYLE MATCH  (+50 pts)
        #    Hard identity check — does this candidate share the user's style?
        #    Source: candidate.style_profile vs user_style string
        # ─────────────────────────────────────────────────────────────────
        if candidate.style_profile == user_style:
            score += 50
            reason_parts.append(f"fits your {user_style} aesthetic")

        # ─────────────────────────────────────────────────────────────────
        # ② OUTFIT COLOR HARMONY  (±30 pts)  ← PRIMARY COLOR CHECK
        #    Evaluates the candidate's color against the CART item's color.
        #    Source: color_harmony table  { (source_color, target_color): score }
        #    Positive = good complement / monochromatic
        #    Negative = visual clash (penalises score)
        # ─────────────────────────────────────────────────────────────────
        harmony = self._tables.color_harmony.get((cart_color, cand_color), 0)
        harmony = max(-30, min(30, harmony))   # hard clamp to [-30, +30]
        score  += harmony

        if harmony >= 25:
            reason_parts.append(
                f"the {cand_color.lower()} makes a striking complement "
                f"to your {cart_color.lower()} {cart_type}"
            )
        elif harmony >= 15:
            reason_parts.append(
                f"the {cand_color.lower()} pairs cleanly with {cart_color.lower()}"
            )
        elif harmony > 0:
            reason_parts.append(
                f"the {cand_color.lower()} is a workable match "
                f"for {cart_color.lower()}"
            )
        elif harmony < 0:
            reason_parts.append(
                f"note: {cand_color.lower()} creates a slight clash "
                f"with {cart_color.lower()}"
            )

        # ─────────────────────────────────────────────────────────────────
        # ③ SKIN TONE SYNERGY  (+0..30 pts)  ← SECONDARY COLOR CHECK
        #    Evaluated AFTER outfit harmony — layered on top of step ②.
        #    Evaluates the candidate's color against the USER'S complexion.
        #    Source: skin_tone_synergy table  { (skin_tone, color_family): score }
        #    No negative values — skin tone never penalises.
        #
        #    Warm skin  → earth/autumn tones (Olive, Maroon, Mustard, Beige)
        #    Cool skin  → jewel/arctic tones (Navy, Charcoal, White)
        #    Neutral    → flat baseline across all colors
        # ─────────────────────────────────────────────────────────────────
        skin_bonus = self._tables.skin_tone_synergy.get(
            (user_skin_tone, cand_color), 0
        )
        skin_bonus = max(0, min(30, skin_bonus))   # clamp to [0, +30]
        score     += skin_bonus

        if skin_bonus >= 25:
            reason_parts.append(
                f"and {cand_color.lower()} is exceptionally "
                f"flattering on {user_skin_tone.lower()} skin"
            )
        elif skin_bonus >= 15:
            reason_parts.append(
                f"and it complements your {user_skin_tone.lower()} complexion"
            )

        # ─────────────────────────────────────────────────────────────────
        # ④ AESTHETIC BONUS  (+0..20 pts)
        #    Cinematic editorial bonus for specific premium combos.
        #    Source: aesthetic_bonus table  { (cart_color, candidate_color): score }
        # ─────────────────────────────────────────────────────────────────
        aesthetic = self._tables.aesthetic_bonus.get((cart_color, cand_color), 0)
        score    += aesthetic

        if aesthetic > 0:
            reason_parts.append("this combination has a premium, editorial quality")

        # ── Build natural-language match_reason ───────────────────────────
        if reason_parts:
            match_reason  = reason_parts[0].capitalize()
            if len(reason_parts) > 1:
                match_reason += " — " + ", ".join(reason_parts[1:]) + "."
            else:
                match_reason += "."
        else:
            match_reason = (
                f"A functional pairing option for your {user_style} wardrobe."
            )

        logger.debug(
            "  score_one: %-28s  score=%3d",
            candidate.name[:28], score,
        )
        return score, match_reason

    # =========================================================================
    # PHASE D — RANK & FORMAT
    # =========================================================================

    def _rank_and_format(self, candidates: list, top_n: int) -> list:
        """
        Sorts candidates descending by score (alphabetical name breaks ties),
        wraps top_n results as Recommendation objects.

        Args:
            candidates : Fully scored Candidate list.
            top_n      : Max items to return.

        Returns:
            List of Recommendation dataclass instances, best first.
        """
        candidates.sort(key=lambda c: (-c.score, c.name))

        results = []
        for rank, c in enumerate(candidates[:top_n], start=1):
            results.append(Recommendation(
                rank=rank,
                recommended_sku=c.sku,
                name=c.name,
                price=c.price,
                image_url=c.image_url,
                garment_type=c.garment_type,
                color_family=c.color_family,
                match_reason=c.match_reason,
                score=c.score,
            ))
        return results

    # =========================================================================
    # SCORING TABLE LOADER  (MySQL → ScoringTables in-memory cache)
    # =========================================================================

    def _load_scoring_tables(self) -> ScoringTables:
        """
        Fetches all four scoring/config tables from MySQL and builds the
        ScoringTables cache.  Called once at startup and whenever
        reload_scoring_tables() is invoked.

        Returns:
            A fully populated ScoringTables instance.
        """
        try:
            t = ScoringTables()

            # pairing_rules → { cart_type: [candidate_type, ...] }
            for row in self._db.query(self._SQL_PAIRING_RULES):
                t.pairing_rules.setdefault(
                    row["cart_type"], []
                ).append(row["candidate_type"])

            # color_harmony → { (source_color, target_color): score }
            for row in self._db.query(self._SQL_COLOR_HARMONY):
                t.color_harmony[
                    (row["source_color"], row["target_color"])
                ] = int(row["harmony_score"])

            # skin_tone_synergy → { (skin_tone, color_family): score }
            for row in self._db.query(self._SQL_SKIN_SYNERGY):
                t.skin_tone_synergy[
                    (row["skin_tone"], row["color_family"])
                ] = int(row["synergy_score"])

            # aesthetic_bonus → { (cart_color, candidate_color): score }
            for row in self._db.query(self._SQL_AESTHETIC_BONUS):
                t.aesthetic_bonus[
                    (row["cart_color"], row["candidate_color"])
                ] = int(row["bonus_score"])

            return t

        except MySQLError as e:
            raise StylingEngineError(
                f"Failed to load scoring tables from MySQL: {e}"
            ) from e

    # =========================================================================
    # SERIALISATION HELPERS
    # =========================================================================

    @staticmethod
    def _cart_item_to_dict(c: CartItem) -> dict:
        return {
            "sku":              c.sku,
            "name":             c.name,
            "price":            c.price,
            "garment_category": c.garment_category,
            "garment_type":     c.garment_type,
            "style_profile":    c.style_profile,
            "color_family":     c.color_family,
            "image_url":        c.image_url,
        }

    @staticmethod
    def _rec_to_dict(r: Recommendation) -> dict:
        return {
            "rank":            r.rank,
            "recommended_sku": r.recommended_sku,
            "name":            r.name,
            "price":           r.price,
            "image_url":       r.image_url,
            "garment_type":    r.garment_type,
            "color_family":    r.color_family,
            "match_reason":    r.match_reason,
            "_score":          r.score,   # strip for MCU sends in production
        }


# =============================================================================
# SECTION 5 — FLASK APPLICATION
# =============================================================================

from flask import Flask, request, jsonify

from flask_cors import CORS
flask_app = Flask(__name__)
CORS(flask_app)   # ← add this line

# ── DB Configuration ──────────────────────────────────────────────────────────
# PRODUCTION: load from environment variables, never hardcode credentials.
#
#   import os
#   DB_CONFIG = {
#       "host":     os.environ["DB_HOST"],
#       "port":     int(os.environ.get("DB_PORT", 3306)),
#       "user":     os.environ["DB_USER"],
#       "password": os.environ["DB_PASSWORD"],
#       "database": os.environ["DB_NAME"],
#   }
#
# DEV / LOCAL (replace with your MySQL credentials):
DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "root",
    "password": "7463",
    "database": "smart_cart",
}

# Single engine instance shared across all Flask requests.
# Initialised lazily on first request to allow the server to start
# even if the DB is momentarily unavailable.
_engine: Optional[StylingEngine] = None


def get_engine() -> StylingEngine:
    """Returns the shared StylingEngine singleton, creating it if necessary."""
    global _engine
    if _engine is None:
        _engine = StylingEngine(DB_CONFIG)
    return _engine


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 1: GET /health
# Liveness probe — ESP32 polls this at boot to confirm connectivity.
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/health", methods=["GET"])
def health():
    """Lightweight health check with scoring table stats."""
    try:
        eng = get_engine()
        return jsonify({
            "status":           "ok",
            "pairing_rules":    sum(len(v) for v in eng._tables.pairing_rules.values()),
            "color_pairs":      len(eng._tables.color_harmony),
            "skin_tone_pairs":  len(eng._tables.skin_tone_synergy),
            "aesthetic_combos": len(eng._tables.aesthetic_bonus),
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 503


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 2: POST /api/get_product
# EPC → product details.  Populates the cart item card on the ESP32 display.
#
# Request : { "epc_id": "E200009" }
# Response: { "sku", "name", "price", "image_url" }
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/api/get_product", methods=["POST"])
def get_product():
    """Resolves a single EPC tag to its core product details."""
    data = request.get_json(force=True, silent=True)

    if not data or "epc_id" not in data:
        return jsonify({
            "error":   "Bad Request",
            "message": "JSON body must contain 'epc_id'.",
        }), 400

    try:
        item = get_engine()._resolve_epc(str(data["epc_id"]).strip())
        return jsonify({
            "sku":       item.sku,
            "name":      item.name,
            "price":     item.price,
            "image_url": item.image_url,
        }), 200

    except EPCNotFoundError  as e:
        return jsonify({"error": "Not Found",    "message": str(e)}), 404
    except StylingEngineError as e:
        return jsonify({"error": "Server Error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 3: POST /api/get_style
# Full AI pipeline → TOP 3 ranked style recommendations.
#
# Request:
#   { "epc_id": "E200009", "user_style": "Ethnic", "user_skin_tone": "Warm" }
#
# Response:
#   {
#     "cart_item":   { sku, name, price, garment_type, color_family, ... },
#     "suggestions": [
#       { rank, recommended_sku, name, price, image_url,
#         garment_type, color_family, match_reason, _score },
#       ...
#     ],
#     "meta": { total_candidates_filtered, total_candidates_scored,
#               top_n_returned, max_possible_score }
#   }
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/api/get_style", methods=["POST"])
def get_style():
    """Full AI styling pipeline — anatomy filter + 4-stage scoring → top 3."""
    data = request.get_json(force=True, silent=True)

    if not data:
        return jsonify({
            "error":   "Bad Request",
            "message": "Request body must be valid JSON.",
        }), 400

    required = ["epc_id", "user_style", "user_skin_tone"]
    missing  = [f for f in required if f not in data]
    if missing:
        return jsonify({
            "error":   "Bad Request",
            "message": f"Missing required fields: {missing}",
        }), 400

    try:
        result = get_engine().recommend(
            epc_id         = str(data["epc_id"]).strip(),
            user_style     = str(data["user_style"]).strip(),
            user_skin_tone = str(data["user_skin_tone"]).strip(),
            top_n          = 3,
        )
        return jsonify(result), 200

    except EPCNotFoundError  as e:
        return jsonify({"error": "Not Found",            "message": str(e)}), 404
    except NoCandidatesError as e:
        return jsonify({"error": "Unprocessable Entity", "message": str(e)}), 422
    except StylingEngineError as e:
        return jsonify({"error": "Server Error",         "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE 4: POST /api/reload_scoring
# Hot-reload scoring tables from MySQL — no server restart needed.
# Secure with an API key header in production.
# ─────────────────────────────────────────────────────────────────────────────
@flask_app.route("/api/reload_scoring", methods=["POST"])
def reload_scoring():
    """
    Admin: reloads scoring tables (color_harmony, pairing_rules, etc.)
    from MySQL into the in-memory cache.
    Call after any UPDATE to scoring weights in the database.
    """
    try:
        eng = get_engine()
        eng.reload_scoring_tables()
        return jsonify({
            "status":           "reloaded",
            "pairing_rules":    sum(len(v) for v in eng._tables.pairing_rules.values()),
            "color_pairs":      len(eng._tables.color_harmony),
            "skin_tone_pairs":  len(eng._tables.skin_tone_synergy),
            "aesthetic_combos": len(eng._tables.aesthetic_bonus),
        }), 200
    except StylingEngineError as e:
        return jsonify({"error": "Reload failed", "message": str(e)}), 500


# =============================================================================
# SECTION 6 — ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    print("=" * 65)
    print("  Smart Retail Cart — AI Styling Engine  v3.0.0")
    print("  Database-driven · All weights sourced from MySQL")
    print()
    print("  POST /api/get_product    → EPC → product details")
    print("  POST /api/get_style      → EPC → top 3 recommendations")
    print("  POST /api/reload_scoring → hot-reload scoring tables")
    print("  GET  /health             → liveness probe")
    print("=" * 65)

    flask_app.run(host="0.0.0.0", port=5000, debug=True)