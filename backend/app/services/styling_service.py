import colorsys
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from app.core.db import db, redis_client

logger = logging.getLogger("innocart.styling_service")

@dataclass
class CartItem:
    sku: str
    name: str
    price: float
    garment_category: str
    garment_type: str
    style_profile: str
    color_family: str
    image_url: str
    aisle_location: str = "Aisle A-01"

@dataclass
class Candidate:
    sku: str
    name: str
    price: float
    garment_category: str
    garment_type: str
    style_profile: str
    color_family: str
    image_url: str
    aisle_location: str = "Aisle A-01"
    score: int = 0
    match_reason: str = ""
    facial_score: int = 0

@dataclass
class ScoringTables:
    pairing_rules: Dict[str, List[str]] = field(default_factory=dict)
    color_harmony: Dict[Tuple[str, str], int] = field(default_factory=dict)
    skin_tone_synergy: Dict[Tuple[str, str], int] = field(default_factory=dict)
    aesthetic_bonus: Dict[Tuple[str, str], int] = field(default_factory=dict)
    hex_skin_zones: List[dict] = field(default_factory=list)
    facial_color_harmony: Dict[Tuple[str, str], int] = field(default_factory=dict)

def hex_to_hsl(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0, 0, 128)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        h_f, l_f, s_f = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        return (round(h_f * 360), round(s_f * 100), round(l_f * 255))
    except Exception:
        return (0, 0, 128)

def classify_facial_hex(hex_color: str, zones: List[dict]) -> str:
    if not hex_color:
        return "Neutral-Beige"
    hue, sat, lum = hex_to_hsl(hex_color)
    for zone in zones:
        lum_ok = zone["lum_min"] <= lum <= zone["lum_max"]
        h_min, h_max = zone["hue_min"], zone["hue_max"]
        hue_ok = (hue >= h_min or hue <= h_max) if h_min > h_max else (h_min <= hue <= h_max)
        sat_ok = zone["sat_min"] <= sat <= zone["sat_max"]
        if lum_ok and hue_ok and sat_ok:
            return zone["undertone_label"]
    return "Neutral-Beige"

class StylingService:
    def __init__(self):
        self._tables = ScoringTables()
        self.reload_scoring_tables()

    def reload_scoring_tables(self):
        logger.info("Loading 5-stage AI scoring tables from MySQL...")
        t = ScoringTables()
        
        try:
            # 1. Pairing rules
            rules = db.query("SELECT cart_type, candidate_type FROM pairing_rules")
            for r in rules:
                t.pairing_rules.setdefault(r["cart_type"], []).append(r["candidate_type"])

            # 2. Color harmony
            harmonies = db.query("SELECT source_color, target_color, harmony_score FROM color_harmony")
            for h in harmonies:
                t.color_harmony[(h["source_color"], h["target_color"])] = int(h["harmony_score"])

            # 3. Skin tone synergy
            skins = db.query("SELECT skin_tone, color_family, synergy_score FROM skin_tone_synergy")
            for s in skins:
                t.skin_tone_synergy[(s["skin_tone"], s["color_family"])] = int(s["synergy_score"])

            # 4. Aesthetic bonus
            aesthetics = db.query("SELECT cart_color, candidate_color, bonus_score FROM aesthetic_bonus")
            for a in aesthetics:
                t.aesthetic_bonus[(a["cart_color"], a["candidate_color"])] = int(a["bonus_score"])

            # 5a. Hex skin zones
            t.hex_skin_zones = db.query(
                "SELECT undertone_label, lum_min, lum_max, hue_min, hue_max, sat_min, sat_max, priority "
                "FROM hex_skin_zones ORDER BY priority ASC"
            )

            # 5b. Facial color harmony
            facials = db.query("SELECT undertone_label, color_family, harmony_score FROM facial_color_harmony")
            for f in facials:
                t.facial_color_harmony[(f["undertone_label"], f["color_family"])] = int(f["harmony_score"])
        except Exception as e:
            logger.warning(f"Database query for AI scoring tables notice: {e}")

        self._tables = t

    def resolve_epc(self, epc_id: str) -> Optional[CartItem]:
        sql = """
            SELECT pm.sku, pm.name, pm.price, pm.garment_category, pm.garment_type,
                   pm.style_profile, pm.color_family, pm.image_url, pm.aisle_location
            FROM inventory_live il
            INNER JOIN product_master pm ON il.sku = pm.sku
            WHERE il.epc_id = %s
            LIMIT 1
        """
        rows = db.query(sql, (epc_id,))
        if not rows:
            return None
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
            aisle_location=r.get("aisle_location", "Aisle A-01")
        )

    def resolve_sku(self, sku: str) -> Optional[CartItem]:
        sql = """
            SELECT sku, name, price, garment_category, garment_type,
                   style_profile, color_family, image_url, aisle_location
            FROM product_master
            WHERE sku = %s
            LIMIT 1
        """
        rows = db.query(sql, (sku,))
        if not rows:
            return None
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
            aisle_location=r.get("aisle_location", "Aisle A-01")
        )

    def classify_hex(self, hex_color: str) -> str:
        return classify_facial_hex(hex_color, self._tables.hex_skin_zones)

    def recommend(
        self,
        epc_id: Optional[str] = None,
        sku: Optional[str] = None,
        user_style: str = "Streetwear",
        facial_hex: str = "#C8A882",
        suggest_mode: str = "outfit",  # "outfit" | "footwear" | "accessories"
        top_n: int = 3,
        user_skin_tone: str = "Neutral"
    ) -> dict:
        cart_item = None
        if epc_id:
            cart_item = self.resolve_epc(epc_id)
        elif sku:
            cart_item = self.resolve_sku(sku)

        if not cart_item:
            rows = db.query("SELECT sku FROM product_master WHERE garment_category = 'Topwear' LIMIT 1")
            if rows:
                cart_item = self.resolve_sku(rows[0]["sku"])

        if not cart_item:
            return {"status": "error", "message": "Item not found for styling", "code": 404}

        undertone = (
            self.classify_hex(facial_hex)
            if facial_hex else user_skin_tone
        )

        candidates = self._anatomy_filter(cart_item, suggest_mode)
        scored = self._score_all(candidates, cart_item, user_style, user_skin_tone, undertone)
        scored.sort(key=lambda c: (-c.score, c.name))
        top_candidates = scored[:top_n]

        suggestions = []
        for rank, c in enumerate(top_candidates, start=1):
            suggestions.append({
                "rank": rank,
                "recommended_sku": c.sku,
                "name": c.name,
                "price": c.price,
                "image_url": c.image_url,
                "garment_category": c.garment_category,
                "garment_type": c.garment_type,
                "color_family": c.color_family,
                "aisle_location": c.aisle_location,
                "match_reason": c.match_reason,
                "_score": c.score,
                "facial_score": c.facial_score
            })

        return {
            "cart_item": {
                "sku": cart_item.sku,
                "name": cart_item.name,
                "price": cart_item.price,
                "garment_category": cart_item.garment_category,
                "garment_type": cart_item.garment_type,
                "style_profile": cart_item.style_profile,
                "color_family": cart_item.color_family,
                "image_url": cart_item.image_url,
                "aisle_location": cart_item.aisle_location
            },
            "undertone_label": undertone,
            "facial_hex": facial_hex,
            "suggest_mode": suggest_mode,
            "suggestions": suggestions,
            "meta": {
                "total_candidates": len(candidates),
                "max_possible_score": 170
            }
        }

    def get_cart_ai_styling(self, session_id: str, facial_hex: str = "#C8A882", user_style: str = "Streetwear") -> dict:
        from app.services.cart_service import cart_service
        summary = cart_service.get_summary(session_id)
        items = summary.get("items", [])

        undertone = self.classify_hex(facial_hex)

        topwear_item = None
        bottomwear_item = None
        footwear_item = None

        for item in items:
            cat = item.get("garment_category")
            if not cat:
                res = self.resolve_sku(item.get("sku"))
                if res:
                    cat = res.garment_category
            
            if cat == "Topwear" and not topwear_item:
                topwear_item = item
            elif cat == "Bottomwear" and not bottomwear_item:
                bottomwear_item = item
            elif cat == "Footwear" and not footwear_item:
                footwear_item = item

        recommended_bottomwear = []
        recommended_topwear = []
        recommended_footwear = []
        recommended_accessories = []

        ref_sku = topwear_item.get("sku") if topwear_item else (bottomwear_item.get("sku") if bottomwear_item else "SKU-HD-01")

        # 1. Bottomwear Recommendations (when Topwear is present or requested)
        rec_bot = self.recommend(sku=ref_sku, user_style=user_style, facial_hex=facial_hex, suggest_mode="outfit", top_n=4)
        if rec_bot and rec_bot.get("suggestions"):
            for s in rec_bot["suggestions"]:
                if s.get("garment_category") == "Bottomwear":
                    recommended_bottomwear.append(s)

        # 2. Topwear Recommendations (when Bottomwear is present or requested)
        if bottomwear_item:
            rec_top = self.recommend(sku=bottomwear_item.get("sku"), user_style=user_style, facial_hex=facial_hex, suggest_mode="outfit", top_n=4)
            if rec_top and rec_top.get("suggestions"):
                for s in rec_top["suggestions"]:
                    if s.get("garment_category") == "Topwear":
                        recommended_topwear.append(s)

        # 3. Footwear Recommendations (Separate Category)
        rec_foot = self.recommend(sku=ref_sku, user_style=user_style, facial_hex=facial_hex, suggest_mode="footwear", top_n=3)
        if rec_foot and rec_foot.get("suggestions"):
            recommended_footwear = rec_foot["suggestions"]

        # 4. Accessories Recommendations (Separate Category)
        rec_acc = self.recommend(sku=ref_sku, user_style=user_style, facial_hex=facial_hex, suggest_mode="accessories", top_n=3)
        if rec_acc and rec_acc.get("suggestions"):
            recommended_accessories = rec_acc["suggestions"]

        outfit_match_score = 85
        if topwear_item and bottomwear_item:
            outfit_match_score = 94
        elif topwear_item or bottomwear_item:
            outfit_match_score = 88

        return {
            "session_id": session_id,
            "undertone_label": undertone,
            "facial_hex": facial_hex,
            "user_style": user_style,
            "active_topwear": topwear_item,
            "active_bottomwear": bottomwear_item,
            "active_footwear": footwear_item,
            "outfit_match_score": outfit_match_score,
            "recommended_bottomwear": recommended_bottomwear,
            "recommended_topwear": recommended_topwear,
            "recommended_footwear": recommended_footwear,
            "recommended_accessories": recommended_accessories
        }

    def _anatomy_filter(self, cart_item: CartItem, suggest_mode: str) -> List[Candidate]:
        sql = "SELECT sku, name, price, garment_category, garment_type, style_profile, color_family, image_url, aisle_location FROM product_master"
        rows = db.query(sql)

        allowed_types = self._tables.pairing_rules.get(cart_item.garment_type)

        if suggest_mode == "footwear":
            cat_gate = {"Footwear"}
        elif suggest_mode == "accessories":
            cat_gate = {"Accessories"}
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
                sku=r["sku"],
                name=r["name"],
                price=float(r["price"]),
                garment_category=r["garment_category"],
                garment_type=r["garment_type"],
                style_profile=r["style_profile"],
                color_family=r["color_family"],
                image_url=r["image_url"],
                aisle_location=r.get("aisle_location", "Aisle A-01")
            ))
        return candidates

    def _score_all(self, candidates: List[Candidate], cart_item: CartItem, user_style: str, user_skin_tone: str, undertone: str) -> List[Candidate]:
        for c in candidates:
            score = 0
            reason_parts = []
            cart_color = cart_item.color_family
            cand_color = c.color_family
            cart_type = cart_item.garment_type.lower()

            if c.style_profile == user_style:
                score += 50
                reason_parts.append(f"fits your {user_style} aesthetic")

            harmony = max(-30, min(30, self._tables.color_harmony.get((cart_color, cand_color), 0)))
            score += harmony
            if harmony >= 25:
                reason_parts.append(f"{cand_color.lower()} makes a striking complement to your {cart_color.lower()} {cart_type}")
            elif harmony >= 15:
                reason_parts.append(f"{cand_color.lower()} pairs cleanly with {cart_color.lower()}")
            elif harmony > 0:
                reason_parts.append(f"{cand_color.lower()} is a workable match for {cart_color.lower()}")

            skin_bonus = max(0, min(30, self._tables.skin_tone_synergy.get((user_skin_tone, cand_color), 0)))
            score += skin_bonus
            if skin_bonus >= 25:
                reason_parts.append(f"complements {user_skin_tone.lower()} skin tone")

            aesthetic = self._tables.aesthetic_bonus.get((cart_color, cand_color), 0)
            score += aesthetic
            if aesthetic > 0:
                reason_parts.append("premium editorial combination")

            facial_pts = max(0, min(40, self._tables.facial_color_harmony.get((undertone, cand_color), 0)))
            score += facial_pts
            c.facial_score = facial_pts

            if facial_pts >= 35:
                reason_parts.insert(0, f"exceptional match for your {undertone.replace('-', ' ').lower()} complexion")
            elif facial_pts >= 25:
                reason_parts.append(f"flattering against your {undertone.replace('-', ' ').lower()} skin")

            if reason_parts:
                c.match_reason = reason_parts[0].capitalize() + (" — " + ", ".join(reason_parts[1:]) + "." if len(reason_parts) > 1 else ".")
            else:
                c.match_reason = f"A functional {user_style.lower()} pairing option."

            c.score = score
        return candidates

styling_service = StylingService()
