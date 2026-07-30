"""
=============================================================================
  AI STYLING ENGINE  —  Smart Retail Cart
  File    : styling_engine.py
  Version : 4.0.0  (Facial-Hex Edition)

  WHAT'S NEW IN v4.0.0
  ────────────────────
  • facial_hex  parameter (e.g. "#C8A882") — extracted by the mobile app
    from a live face crop via K-means dominant colour detection.
  • Scoring stage ⑤: Facial Color Harmony  +0..40 pts  (HIGHEST weight)
    — converts hex → HSL → range-scan against hex_skin_zones table
    → undertone label → looks up facial_color_harmony table for score.
  • suggest_mode parameter:
      "outfit"   → recommend only Topwear OR Bottomwear (opposite of cart item)
      "footwear" → recommend only Footwear
  • New Flask routes:
      POST /api/get_cart_wearable  — returns Topwear+Bottomwear for picker
      POST /api/get_style          — outfit suggestions (top↔bottom)
      POST /api/suggest_footwear   — footwear suggestions
      POST /api/classify_hex       — debug: hex → undertone label

  SCORE CEILING (v4)
  ──────────────────
  ① Style Match          +50 pts
  ② Outfit Color Harmony ±30 pts
  ③ Skin Tone Synergy    + 0..30  (3-category fallback, kept for compat)
  ④ Aesthetic Bonus      + 0..20
  ⑤ Facial Color Harmony + 0..40  ← NEW, highest single-stage weight
                         ─────────
  MAX                    170 pts

  DATABASE TABLES CONSUMED
  ────────────────────────
  • inventory_live          EPC → SKU
  • product_master          SKU → garment details
  • pairing_rules           anatomy filter
  • color_harmony           outfit color matrix (stage ②)
  • skin_tone_synergy       3-cat skin map (stage ③)
  • aesthetic_bonus         cinematic combos (stage ④)
  • hex_skin_zones          hex → undertone label (stage ⑤)
  • facial_color_harmony    undertone × garment color → score (stage ⑤)

  DEPENDENCIES
  ────────────
  pip install mysql-connector-python flask flask-cors
  (colorsys is Python stdlib — no extra install needed)
=============================================================================
"""

import colorsys
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
    sku:              str
    name:             str
    price:            float
    garment_category: str   # Topwear | Bottomwear | Footwear | Accessory
    garment_type:     str
    style_profile:    str
    color_family:     str
    image_url:        str


@dataclass
class Candidate:
    sku:              str
    name:             str
    price:            float
    garment_category: str
    garment_type:     str
    style_profile:    str
    color_family:     str
    image_url:        str
    score:            int = 0
    match_reason:     str = ""


@dataclass
class ScoringTables:
    pairing_rules:        dict = field(default_factory=dict)
    color_harmony:        dict = field(default_factory=dict)
    skin_tone_synergy:    dict = field(default_factory=dict)
    aesthetic_bonus:      dict = field(default_factory=dict)
    hex_skin_zones:       list = field(default_factory=list)   # ordered list
    facial_color_harmony: dict = field(default_factory=dict)


@dataclass
class Recommendation:
    rank:             int
    recommended_sku:  str
    name:             str
    price:            float
    image_url:        str
    garment_category: str
    garment_type:     str
    color_family:     str
    match_reason:     str
    score:            int
    facial_score:     int


# =============================================================================
# SECTION 2 — CUSTOM EXCEPTIONS
# =============================================================================

class StylingEngineError(Exception):
    http_status = 500

class EPCNotFoundError(StylingEngineError):
    http_status = 404

class NoCandidatesError(StylingEngineError):
    http_status = 422


# =============================================================================
# SECTION 3 — DATABASE POOL
# =============================================================================

class DBPool:
    def __init__(self, config: dict):
        self._config = config
        self._probe()

    def _probe(self):
        try:
            conn = mysql.connector.connect(**self._config)
            conn.close()
            logger.info("DB probe OK  host=%s  db=%s",
                        self._config.get("host"), self._config.get("database"))
        except MySQLError as e:
            logger.error("DB probe FAILED: %s", e)
            raise

    def query(self, sql: str, params: tuple = ()) -> list:
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
# SECTION 4 — FACIAL HEX UTILITIES
# =============================================================================

def hex_to_hsl(hex_color: str) -> tuple:
    """
    Convert CSS hex (#RRGGBB) → (hue 0-360, saturation 0-100, luminance 0-255).
    Luminance is 0-255 to match the DB lum_min / lum_max columns.
    """
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0, 0, 128)
    try:
        r, g, b     = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        h_f, l_f, s_f = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        return (round(h_f * 360), round(s_f * 100), round(l_f * 255))
    except (ValueError, ZeroDivisionError):
        return (0, 0, 128)


def classify_facial_hex(hex_color: str, zones: list) -> str:
    """
    Classify a facial hex colour → undertone label by range-scanning
    hex_skin_zones rows (sorted by priority ASC). First match wins.
    Falls back to "Neutral".
    """
    if not hex_color:
        return "Neutral"
    hue, sat, lum = hex_to_hsl(hex_color)
    logger.debug("Facial hex %s → H=%d  S=%d  L=%d", hex_color, hue, sat, lum)

    for zone in zones:
        lum_ok = zone["lum_min"] <= lum <= zone["lum_max"]
        h_min, h_max = zone["hue_min"], zone["hue_max"]
        hue_ok = (hue >= h_min or hue <= h_max) if h_min > h_max else (h_min <= hue <= h_max)
        sat_ok = zone["sat_min"] <= sat <= zone["sat_max"]
        if lum_ok and hue_ok and sat_ok:
            logger.debug("→ matched zone: %s (priority %d)",
                         zone["undertone_label"], zone["priority"])
            return zone["undertone_label"]
    return "Neutral"


# =============================================================================
# SECTION 5 — AI STYLING ENGINE
# =============================================================================

class StylingEngine:
    """
    Core AI recommendation engine for the Smart Retail Cart.

    v4.0 additions
    ───────────────
    • facial_hex + suggest_mode parameters in recommend()
    • Stage ⑤: Facial Color Harmony (+0..40 pts — highest weight)
    • resolve_cart_wearable() — returns top+bottom items for the picker
    • hex_to_undertone()      — public debug utility
    • New routes: /api/get_cart_wearable, /api/get_style,
                  /api/suggest_footwear, /api/classify_hex
    """

    _SQL_RESOLVE_EPC = """
        SELECT pm.sku, pm.name, pm.price,
               pm.garment_category, pm.garment_type,
               pm.style_profile, pm.color_family, pm.image_url
        FROM   inventory_live il
        INNER  JOIN product_master pm ON il.sku = pm.sku
        WHERE  il.epc_id    = %s
          AND  il.is_active = 1
          AND  pm.is_active = 1
        LIMIT  1
    """

    _SQL_ALL_ACTIVE = """
        SELECT sku, name, price, garment_category, garment_type,
               style_profile, color_family, image_url
        FROM   product_master
        WHERE  is_active = 1
    """

    _SQL_BATCH_EPCS = """
        SELECT DISTINCT pm.sku, pm.name, pm.price,
               pm.garment_category, pm.garment_type,
               pm.style_profile, pm.color_family, pm.image_url
        FROM   inventory_live il
        INNER  JOIN product_master pm ON il.sku = pm.sku
        WHERE  il.epc_id IN ({ph})
          AND  il.is_active = 1
          AND  pm.is_active = 1
    """

    _SQL_PAIRING     = "SELECT cart_type, candidate_type FROM pairing_rules ORDER BY cart_type"
    _SQL_HARMONY     = "SELECT source_color, target_color, harmony_score FROM color_harmony"
    _SQL_SKIN        = "SELECT skin_tone, color_family, synergy_score FROM skin_tone_synergy"
    _SQL_AESTHETIC   = "SELECT cart_color, candidate_color, bonus_score FROM aesthetic_bonus"
    _SQL_HEX_ZONES   = """
        SELECT undertone_label, lum_min, lum_max,
               hue_min, hue_max, sat_min, sat_max, priority
        FROM   hex_skin_zones
        ORDER  BY priority ASC
    """
    _SQL_FACIAL      = "SELECT undertone_label, color_family, harmony_score FROM facial_color_harmony"

    # ─────────────────────────────────────────────────────────────────────────

    def __init__(self, db_config: dict):
        self._db     = DBPool(db_config)
        self._tables = ScoringTables()
        self.reload_scoring_tables()
        logger.info("StylingEngine v4.0.0 ready.")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def recommend(
        self,
        epc_id:         str,
        user_style:     str,
        facial_hex:     str = "",
        suggest_mode:   str = "outfit",   # "outfit" | "footwear"
        top_n:          int = 3,
        user_skin_tone: str = "Neutral",  # legacy fallback
    ) -> dict:
        """
        Full recommendation pipeline.

        facial_hex drives stage ⑤ (highest weight).
        suggest_mode controls whether we recommend outfit pairs or footwear.
        """
        logger.info("recommend() epc=%s style=%s hex=%s mode=%s top_n=%d",
                    epc_id, user_style, facial_hex, suggest_mode, top_n)

        cart_item = self._resolve_epc(epc_id)

        undertone = (
            classify_facial_hex(facial_hex, self._tables.hex_skin_zones)
            if facial_hex else self._legacy_undertone(user_skin_tone)
        )
        logger.info("Undertone: '%s'  (hex='%s')", undertone, facial_hex)

        candidates = self._anatomy_filter(cart_item, suggest_mode)
        if not candidates:
            raise NoCandidatesError(
                f"No valid pairings for '{cart_item.garment_type}' "
                f"in mode '{suggest_mode}'."
            )

        scored = self._score_all(candidates, cart_item, user_style, user_skin_tone, undertone)
        top    = self._rank_and_format(scored, top_n)

        return {
            "cart_item":       self._cart_item_to_dict(cart_item),
            "undertone_label": undertone,
            "facial_hex":      facial_hex,
            "suggest_mode":    suggest_mode,
            "suggestions":     [self._rec_to_dict(r) for r in top],
            "meta": {
                "total_candidates_filtered": len(candidates),
                "total_candidates_scored":   len(scored),
                "top_n_returned":            len(top),
                "max_possible_score":        170,
                "scoring_stages": {
                    "style_match":          50,
                    "outfit_color_harmony": 30,
                    "skin_tone_synergy":    30,
                    "aesthetic_bonus":      20,
                    "facial_color_harmony": 40,
                },
            },
        }

    def resolve_cart_wearable(self, epc_ids: list) -> dict:
        """
        Returns only Topwear + Bottomwear products from a list of cart EPCs.
        Used to populate the Style Me picker in the simulator / mobile app.
        """
        if not epc_ids:
            return {"topwear": [], "bottomwear": [], "total_wearable": 0}

        ph  = ", ".join(["%s"] * len(epc_ids))
        sql = self._SQL_BATCH_EPCS.format(ph=ph)
        try:
            rows = self._db.query(sql, tuple(epc_ids))
        except MySQLError as e:
            raise StylingEngineError(f"DB error in batch EPC resolve: {e}") from e

        topwear, bottomwear = [], []
        for r in rows:
            item = {
                "sku": r["sku"], "name": r["name"], "price": float(r["price"]),
                "garment_category": r["garment_category"],
                "garment_type": r["garment_type"],
                "style_profile": r["style_profile"],
                "color_family": r["color_family"],
                "image_url": r["image_url"],
            }
            if r["garment_category"] == "Topwear":
                topwear.append(item)
            elif r["garment_category"] == "Bottomwear":
                bottomwear.append(item)

        return {
            "topwear":       topwear,
            "bottomwear":    bottomwear,
            "total_wearable": len(topwear) + len(bottomwear),
        }

    def hex_to_undertone(self, hex_color: str) -> str:
        return classify_facial_hex(hex_color, self._tables.hex_skin_zones)

    def reload_scoring_tables(self) -> None:
        logger.info("Loading scoring tables from MySQL …")
        self._tables = self._load_scoring_tables()
        logger.info(
            "Tables loaded — rules=%d harmony=%d skin=%d "
            "aesthetic=%d hex_zones=%d facial=%d",
            sum(len(v) for v in self._tables.pairing_rules.values()),
            len(self._tables.color_harmony),
            len(self._tables.skin_tone_synergy),
            len(self._tables.aesthetic_bonus),
            len(self._tables.hex_skin_zones),
            len(self._tables.facial_color_harmony),
        )

    # =========================================================================
    # PHASE A — EPC RESOLUTION
    # =========================================================================

    def _resolve_epc(self, epc_id: str) -> CartItem:
        try:
            rows = self._db.query(self._SQL_RESOLVE_EPC, (epc_id,))
        except MySQLError as e:
            raise StylingEngineError(f"DB error in EPC resolution: {e}") from e
        if not rows:
            raise EPCNotFoundError(f"EPC '{epc_id}' not found or inactive.")
        r = rows[0]
        return CartItem(
            sku=r["sku"], name=r["name"], price=float(r["price"]),
            garment_category=r["garment_category"], garment_type=r["garment_type"],
            style_profile=r["style_profile"], color_family=r["color_family"],
            image_url=r["image_url"],
        )

    # =========================================================================
    # PHASE B — ANATOMY FILTER
    # =========================================================================

    def _anatomy_filter(self, cart_item: CartItem, suggest_mode: str) -> list:
        """
        suggest_mode="outfit"   → candidates must be the OPPOSITE category
            cart is Topwear    → suggest Bottomwear
            cart is Bottomwear → suggest Topwear
        suggest_mode="footwear" → candidates must be Footwear only
        """
        try:
            rows = self._db.query(self._SQL_ALL_ACTIVE)
        except MySQLError as e:
            raise StylingEngineError(f"DB error fetching catalogue: {e}") from e

        allowed_types = self._tables.pairing_rules.get(cart_item.garment_type)

        if suggest_mode == "footwear":
            cat_gate = {"Footwear"}
        elif cart_item.garment_category == "Topwear":
            cat_gate = {"Bottomwear"}
        elif cart_item.garment_category == "Bottomwear":
            cat_gate = {"Topwear"}
        else:
            cat_gate = {"Topwear", "Bottomwear"}

        candidates = []
        for r in rows:
            if r["sku"] == cart_item.sku:
                continue
            if r["garment_category"] not in cat_gate:
                continue
            if allowed_types is not None and r["garment_type"] not in allowed_types:
                continue
            candidates.append(Candidate(
                sku=r["sku"], name=r["name"], price=float(r["price"]),
                garment_category=r["garment_category"], garment_type=r["garment_type"],
                style_profile=r["style_profile"], color_family=r["color_family"],
                image_url=r["image_url"],
            ))

        logger.debug("anatomy_filter: mode='%s' gate=%s candidates=%d",
                     suggest_mode, cat_gate, len(candidates))
        return candidates

    # =========================================================================
    # PHASE C — 5-STAGE SCORING
    # =========================================================================

    def _score_all(self, candidates, cart_item, user_style, user_skin_tone, undertone):
        for c in candidates:
            c.score, c.match_reason = self._score_one(
                c, cart_item, user_style, user_skin_tone, undertone
            )
        return candidates

    def _score_one(self, candidate, cart_item, user_style, user_skin_tone, undertone):
        score        = 0
        reason_parts = []
        facial_pts   = 0

        cart_color = cart_item.color_family
        cand_color = candidate.color_family
        cart_type  = cart_item.garment_type.lower()

        # ① Style Match +50
        if candidate.style_profile == user_style:
            score += 50
            reason_parts.append(f"fits your {user_style} aesthetic")

        # ② Outfit Color Harmony ±30
        harmony = max(-30, min(30, self._tables.color_harmony.get((cart_color, cand_color), 0)))
        score  += harmony
        if harmony >= 25:
            reason_parts.append(f"{cand_color.lower()} makes a striking complement to your {cart_color.lower()} {cart_type}")
        elif harmony >= 15:
            reason_parts.append(f"{cand_color.lower()} pairs cleanly with {cart_color.lower()}")
        elif harmony > 0:
            reason_parts.append(f"{cand_color.lower()} is a workable match for {cart_color.lower()}")
        elif harmony < 0:
            reason_parts.append(f"note: {cand_color.lower()} creates a slight clash with {cart_color.lower()}")

        # ③ Skin Tone Synergy +0..30 (legacy)
        skin_bonus = max(0, min(30, self._tables.skin_tone_synergy.get((user_skin_tone, cand_color), 0)))
        score     += skin_bonus
        if skin_bonus >= 25:
            reason_parts.append(f"{cand_color.lower()} is exceptionally flattering on {user_skin_tone.lower()} skin")
        elif skin_bonus >= 15:
            reason_parts.append(f"complements your {user_skin_tone.lower()} complexion")

        # ④ Aesthetic Bonus +0..20
        aesthetic = self._tables.aesthetic_bonus.get((cart_color, cand_color), 0)
        score    += aesthetic
        if aesthetic > 0:
            reason_parts.append("premium editorial combination")

        # ⑤ Facial Color Harmony +0..40  ← HIGHEST WEIGHT
        facial_pts = max(0, min(40, self._tables.facial_color_harmony.get((undertone, cand_color), 0)))
        score     += facial_pts
        undertone_readable = undertone.replace("-", " ").lower()
        if facial_pts >= 35:
            reason_parts.insert(0, f"{cand_color.lower()} is an exceptional match for your {undertone_readable} complexion")
        elif facial_pts >= 25:
            reason_parts.append(f"very flattering against your {undertone_readable} skin")
        elif facial_pts >= 15:
            reason_parts.append(f"good harmony with your complexion")

        # Build reason string
        if reason_parts:
            match_reason = reason_parts[0].capitalize()
            if len(reason_parts) > 1:
                match_reason += " — " + ", ".join(reason_parts[1:]) + "."
            else:
                match_reason += "."
        else:
            match_reason = f"A functional {user_style.lower()} pairing option."

        logger.debug("  score %-28s  total=%3d  facial=%2d", candidate.name[:28], score, facial_pts)
        candidate._facial_score = facial_pts
        return score, match_reason

    # =========================================================================
    # PHASE D — RANK & FORMAT
    # =========================================================================

    def _rank_and_format(self, candidates: list, top_n: int) -> list:
        candidates.sort(key=lambda c: (-c.score, c.name))
        results = []
        for rank, c in enumerate(candidates[:top_n], start=1):
            results.append(Recommendation(
                rank=rank, recommended_sku=c.sku, name=c.name, price=c.price,
                image_url=c.image_url, garment_category=c.garment_category,
                garment_type=c.garment_type, color_family=c.color_family,
                match_reason=c.match_reason, score=c.score,
                facial_score=getattr(c, "_facial_score", 0),
            ))
        return results

    # =========================================================================
    # TABLE LOADER
    # =========================================================================

    def _load_scoring_tables(self) -> ScoringTables:
        try:
            t = ScoringTables()
            for row in self._db.query(self._SQL_PAIRING):
                t.pairing_rules.setdefault(row["cart_type"], []).append(row["candidate_type"])
            for row in self._db.query(self._SQL_HARMONY):
                t.color_harmony[(row["source_color"], row["target_color"])] = int(row["harmony_score"])
            for row in self._db.query(self._SQL_SKIN):
                t.skin_tone_synergy[(row["skin_tone"], row["color_family"])] = int(row["synergy_score"])
            for row in self._db.query(self._SQL_AESTHETIC):
                t.aesthetic_bonus[(row["cart_color"], row["candidate_color"])] = int(row["bonus_score"])
            t.hex_skin_zones = self._db.query(self._SQL_HEX_ZONES)   # already ordered by priority
            for row in self._db.query(self._SQL_FACIAL):
                t.facial_color_harmony[(row["undertone_label"], row["color_family"])] = int(row["harmony_score"])
            return t
        except MySQLError as e:
            raise StylingEngineError(f"Failed to load scoring tables: {e}") from e

    # =========================================================================
    # SERIALISATION
    # =========================================================================

    @staticmethod
    def _cart_item_to_dict(c: CartItem) -> dict:
        return {
            "sku": c.sku, "name": c.name, "price": c.price,
            "garment_category": c.garment_category, "garment_type": c.garment_type,
            "style_profile": c.style_profile, "color_family": c.color_family,
            "image_url": c.image_url,
        }

    @staticmethod
    def _rec_to_dict(r: Recommendation) -> dict:
        return {
            "rank": r.rank, "recommended_sku": r.recommended_sku,
            "name": r.name, "price": r.price, "image_url": r.image_url,
            "garment_category": r.garment_category, "garment_type": r.garment_type,
            "color_family": r.color_family, "match_reason": r.match_reason,
            "facial_score": r.facial_score, "_score": r.score,
        }

    @staticmethod
    def _legacy_undertone(skin_tone: str) -> str:
        return {"Warm": "Medium-Warm", "Cool": "Medium-Cool", "Neutral": "Neutral"}.get(skin_tone, "Neutral")


# =============================================================================
# SECTION 6 — FLASK APP
# =============================================================================

from flask import Flask, request, jsonify
from flask_cors import CORS

flask_app = Flask(__name__)
CORS(flask_app)

DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "cart_user",
    "password": "yourpassword",
    "database": "smart_cart",
}

_engine: Optional[StylingEngine] = None

def get_engine() -> StylingEngine:
    global _engine
    if _engine is None:
        _engine = StylingEngine(DB_CONFIG)
    return _engine


@flask_app.route("/health", methods=["GET"])
def health():
    try:
        eng = get_engine()
        return jsonify({
            "status": "ok", "version": "4.0.0",
            "pairing_rules":    sum(len(v) for v in eng._tables.pairing_rules.values()),
            "color_pairs":      len(eng._tables.color_harmony),
            "skin_tone_pairs":  len(eng._tables.skin_tone_synergy),
            "aesthetic_combos": len(eng._tables.aesthetic_bonus),
            "hex_zones":        len(eng._tables.hex_skin_zones),
            "facial_combos":    len(eng._tables.facial_color_harmony),
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 503


@flask_app.route("/api/get_product", methods=["POST"])
def get_product():
    data = request.get_json(force=True, silent=True)
    if not data or "epc_id" not in data:
        return jsonify({"error": "Bad Request", "message": "Missing 'epc_id'."}), 400
    try:
        item = get_engine()._resolve_epc(str(data["epc_id"]).strip())
        return jsonify({
            "sku": item.sku, "name": item.name, "price": item.price,
            "garment_category": item.garment_category,
            "garment_type": item.garment_type,
            "image_url": item.image_url,
        }), 200
    except EPCNotFoundError   as e:
        return jsonify({"error": "Not Found",    "message": str(e)}), 404
    except StylingEngineError as e:
        return jsonify({"error": "Server Error", "message": str(e)}), 500


@flask_app.route("/api/get_cart_wearable", methods=["POST"])
def get_cart_wearable():
    """
    Returns only Topwear + Bottomwear from a cart session.
    Used to populate the Style Me item picker.

    Request:  { "epc_ids": ["E100001", "E200007", ...] }
    Response: { "topwear": [...], "bottomwear": [...], "total_wearable": N }
    """
    data = request.get_json(force=True, silent=True)
    if not data or "epc_ids" not in data:
        return jsonify({"error": "Bad Request", "message": "Missing 'epc_ids'."}), 400
    epc_ids = [str(e).strip() for e in data["epc_ids"] if e]
    if not epc_ids:
        return jsonify({"topwear": [], "bottomwear": [], "total_wearable": 0}), 200
    try:
        return jsonify(get_engine().resolve_cart_wearable(epc_ids)), 200
    except StylingEngineError as e:
        return jsonify({"error": "Server Error", "message": str(e)}), 500


@flask_app.route("/api/get_style", methods=["POST"])
def get_style():
    """
    Outfit recommendations — Topwear ↔ Bottomwear.

    Request:
      { "epc_id": "E100001", "user_style": "Streetwear",
        "facial_hex": "#C8A882", "top_n": 3 }

    facial_hex is the dominant colour extracted from the customer's face crop
    by the mobile app. It drives the highest-weight scoring stage.
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Bad Request", "message": "Invalid JSON."}), 400
    missing = [f for f in ["epc_id", "user_style"] if f not in data]
    if missing:
        return jsonify({"error": "Bad Request", "message": f"Missing: {missing}"}), 400
    try:
        return jsonify(get_engine().recommend(
            epc_id         = str(data["epc_id"]).strip(),
            user_style     = str(data["user_style"]).strip(),
            facial_hex     = str(data.get("facial_hex", "")).strip(),
            suggest_mode   = "outfit",
            top_n          = int(data.get("top_n", 3)),
            user_skin_tone = str(data.get("user_skin_tone", "Neutral")).strip(),
        )), 200
    except EPCNotFoundError  as e:
        return jsonify({"error": "Not Found",            "message": str(e)}), 404
    except NoCandidatesError as e:
        return jsonify({"error": "Unprocessable Entity", "message": str(e)}), 422
    except StylingEngineError as e:
        return jsonify({"error": "Server Error",         "message": str(e)}), 500


@flask_app.route("/api/suggest_footwear", methods=["POST"])
def suggest_footwear():
    """
    Footwear-only recommendations.

    Request:
      { "epc_id": "E100001", "user_style": "Streetwear",
        "facial_hex": "#C8A882", "top_n": 3 }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Bad Request", "message": "Invalid JSON."}), 400
    missing = [f for f in ["epc_id", "user_style"] if f not in data]
    if missing:
        return jsonify({"error": "Bad Request", "message": f"Missing: {missing}"}), 400
    try:
        return jsonify(get_engine().recommend(
            epc_id         = str(data["epc_id"]).strip(),
            user_style     = str(data["user_style"]).strip(),
            facial_hex     = str(data.get("facial_hex", "")).strip(),
            suggest_mode   = "footwear",
            top_n          = int(data.get("top_n", 3)),
            user_skin_tone = str(data.get("user_skin_tone", "Neutral")).strip(),
        )), 200
    except EPCNotFoundError  as e:
        return jsonify({"error": "Not Found",            "message": str(e)}), 404
    except NoCandidatesError as e:
        return jsonify({"error": "Unprocessable Entity", "message": str(e)}), 422
    except StylingEngineError as e:
        return jsonify({"error": "Server Error",         "message": str(e)}), 500


@flask_app.route("/api/classify_hex", methods=["POST"])
def classify_hex_route():
    """
    Debug utility — test what undertone a hex maps to.

    Request:  { "hex": "#C8A882" }
    Response: { "hex": "#C8A882", "undertone_label": "Olive-Warm",
                "hsl": { "h": 32, "s": 28, "l": 163 } }
    """
    data = request.get_json(force=True, silent=True)
    if not data or "hex" not in data:
        return jsonify({"error": "Bad Request", "message": "Missing 'hex'."}), 400
    hex_color = str(data["hex"]).strip()
    try:
        eng = get_engine()
        undertone = classify_facial_hex(hex_color, eng._tables.hex_skin_zones)
        h, s, l   = hex_to_hsl(hex_color)
        return jsonify({
            "hex": hex_color, "undertone_label": undertone,
            "hsl": {"h": h, "s": s, "l": l},
        }), 200
    except Exception as e:
        return jsonify({"error": "Server Error", "message": str(e)}), 500


@flask_app.route("/api/reload_scoring", methods=["POST"])
def reload_scoring():
    try:
        eng = get_engine()
        eng.reload_scoring_tables()
        return jsonify({
            "status": "reloaded",
            "hex_zones":    len(eng._tables.hex_skin_zones),
            "facial_combos":len(eng._tables.facial_color_harmony),
        }), 200
    except StylingEngineError as e:
        return jsonify({"error": "Reload failed", "message": str(e)}), 500


# =============================================================================
# SECTION 7 — ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
        datefmt="%H:%M:%S", stream=sys.stdout,
    )
    print("=" * 65)
    print("  Innocart AI Styling Engine  v4.0.0  — Facial Hex Edition")
    print()
    print("  Score ceiling: 170 pts")
    print("  ① Style Match          +50 pts")
    print("  ② Outfit Color Harmony ±30 pts")
    print("  ③ Skin Tone Synergy    + 0..30 pts")
    print("  ④ Aesthetic Bonus      + 0..20 pts")
    print("  ⑤ Facial Color Harmony + 0..40 pts  ← highest weight (NEW)")
    print()
    print("  POST /api/get_cart_wearable  → picker: top+bottom from cart")
    print("  POST /api/get_style          → outfit suggestions (top↔bottom)")
    print("  POST /api/suggest_footwear   → footwear suggestions")
    print("  POST /api/classify_hex       → hex → undertone label")
    print("  POST /api/reload_scoring     → hot-reload scoring tables")
    print("  GET  /health                 → liveness probe")
    print("=" * 65)
    flask_app.run(host="0.0.0.0", port=5000, debug=True)