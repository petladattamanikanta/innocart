import logging
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from app.core.db import db, redis_client
from app.core.config import settings

logger = logging.getLogger("innocart.cart_service")

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

@dataclass
class CartLine:
    sku: str
    name: str
    price: float
    image_url: str
    quantity: int = 1
    epcs: List[str] = field(default_factory=list)
    added_at: str = field(default_factory=_utc_now)
    garment_category: str = "Topwear"
    style_profile: str = "Casual"
    major_color_hex: str = "#00F5FF"
    pattern: str = "Solid"

    @property
    def line_total(self) -> float:
        return round(self.price * self.quantity, 2)

@dataclass
class CartSession:
    session_id: str
    store_id: str = "STORE-001"
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    lines: Dict[str, CartLine] = field(default_factory=dict)
    applied_deal_code: Optional[str] = None
    discount_amount: float = 0.0
    customer_name: Optional[str] = "Valued Customer"
    customer_phone: Optional[str] = "+918074346103"

    @property
    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines.values())

    @property
    def raw_total(self) -> float:
        return round(sum(line.line_total for line in self.lines.values()), 2)

    @property
    def cart_total(self) -> float:
        return max(0.0, round(self.raw_total - self.discount_amount, 2))

    def touch(self):
        self.updated_at = _utc_now()

class CartService:
    def __init__(self):
        self._in_memory_sessions: Dict[str, CartSession] = {}

    def get_or_create_session(self, session_id: str, store_id: str = "STORE-001") -> CartSession:
        if session_id in self._in_memory_sessions:
            sess = self._in_memory_sessions[session_id]
            sess.touch()
            return sess

        if redis_client:
            try:
                data = redis_client.get(f"cart:{session_id}")
                if data:
                    raw = json.loads(data)
                    sess = self._deserialize_session(raw)
                    self._in_memory_sessions[session_id] = sess
                    return sess
            except Exception as e:
                logger.warning(f"Redis get failed for session {session_id}: {e}")

        try:
            rows = db.query(
                "SELECT session_id, store_id, created_at, updated_at, applied_deal_code, discount_amount, phone, name "
                "FROM cart_sessions WHERE session_id = %s AND is_active = 1",
                (session_id,)
            )
            if rows:
                r = rows[0]
                sess = CartSession(
                    session_id=r["session_id"],
                    store_id=r["store_id"],
                    created_at=str(r["created_at"]),
                    updated_at=str(r["updated_at"]),
                    applied_deal_code=r.get("applied_deal_code"),
                    discount_amount=float(r.get("discount_amount") or 0.0),
                    customer_phone=r.get("phone") or "+918074346103",
                    customer_name=r.get("name") or "Valued Customer"
                )
                items_rows = db.query(
                    "SELECT sku, name, price, image_url, quantity, added_at FROM cart_items WHERE session_id = %s",
                    (session_id,)
                )
                for item in items_rows:
                    sess.lines[item["sku"]] = CartLine(
                        sku=item["sku"],
                        name=item["name"],
                        price=float(item["price"]),
                        image_url=item["image_url"],
                        quantity=int(item["quantity"]),
                        added_at=str(item["added_at"])
                    )
                self._in_memory_sessions[session_id] = sess
                return sess
        except Exception as e:
            logger.warning(f"MySQL query cart_session error: {e}")

        sess = CartSession(session_id=session_id, store_id=store_id)
        self.save_session(sess)
        return sess

    def bind_user_to_session(self, session_id: str, name: str, mobile: str, facial_hex: str = "#C8A882") -> dict:
        sess = self.get_or_create_session(session_id)
        sess.customer_name = name
        sess.customer_phone = mobile
        
        try:
            db.execute(
                "UPDATE cart_sessions SET phone = %s, name = %s, updated_at = %s WHERE session_id = %s",
                (mobile, name, _utc_now(), session_id)
            )
        except Exception as e:
            logger.warning(f"Notice updating phone in cart_sessions: {e}")

        self.save_session(sess)
        logger.info(f"✓ Bound customer '{name}' ({mobile}) to cart session '{session_id}'")
        return {"status": "success", "session_id": session_id, "name": name, "phone": mobile}

    def save_session(self, session: CartSession):
        session.touch()
        self._in_memory_sessions[session.session_id] = session

        if redis_client:
            try:
                redis_client.setex(
                    f"cart:{session.session_id}",
                    settings.SESSION_TTL_SECONDS,
                    json.dumps(self._serialize_session(session))
                )
            except Exception as e:
                logger.warning(f"Redis set failed for {session.session_id}: {e}")

        try:
            db.execute(
                "INSERT INTO cart_sessions (session_id, store_id, created_at, updated_at, is_active, applied_deal_code, discount_amount, phone, name) "
                "VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE updated_at=VALUES(updated_at), applied_deal_code=VALUES(applied_deal_code), discount_amount=VALUES(discount_amount), phone=VALUES(phone), name=VALUES(name), is_active=1",
                (session.session_id, session.store_id, session.created_at, session.updated_at, session.applied_deal_code, session.discount_amount, session.customer_phone, session.customer_name)
            )
        except Exception as e:
            logger.error(f"Failed to persist cart_session to MySQL: {e}")

    def resolve_epc(self, epc_id: str) -> Optional[dict]:
        clean_epc = epc_id.strip().upper() if epc_id else ""
        if not clean_epc:
            return None

        # 1. Try DB lookup against inventory_live & product_master
        try:
            sql = """
                SELECT il.epc_id, pm.sku, pm.name, pm.price, pm.image_url,
                       pm.garment_category, pm.garment_type, pm.style_profile, pm.color_family, pm.major_color_hex, pm.pattern, pm.aisle_location
                FROM inventory_live il
                INNER JOIN product_master pm ON il.sku = pm.sku
                WHERE il.epc_id = %s
                LIMIT 1
            """
            rows = db.query(sql, (clean_epc,))
            if rows:
                return rows[0]
        except Exception as e:
            logger.warning(f"DB resolve_epc query failed: {e}")

        # 2. Try direct product_master lookup by SKU
        try:
            sql_pm = """
                SELECT sku, name, price, image_url, garment_category, garment_type, style_profile, color_family, major_color_hex, pattern, aisle_location
                FROM product_master
                WHERE sku = %s
                LIMIT 1
            """
            rows_pm = db.query(sql_pm, (clean_epc,))
            if rows_pm:
                res = rows_pm[0]
                res["epc_id"] = clean_epc
                return res
        except Exception:
            pass

        FALLBACK_CATALOG = {
            "E288116C": {"epc_id": "E288116C", "sku": "SKU-KRT-01", "name": "Men's Slim Kurta — Blue", "price": 799.0, "image_url": "https://assets.retailcart.io/KRT-BLU.webp", "garment_category": "Topwear", "garment_type": "Kurta", "style_profile": "Ethnic Wear", "color_family": "Blue", "major_color_hex": "#1A73E8", "pattern": "Solid", "aisle_location": "Aisle 3"},
            "E280110C": {"epc_id": "E280110C", "sku": "SKU-KRT-01", "name": "Men's Slim Kurta — Blue", "price": 799.0, "image_url": "https://assets.retailcart.io/KRT-BLU.webp", "garment_category": "Topwear", "garment_type": "Kurta", "style_profile": "Ethnic Wear", "color_family": "Blue", "major_color_hex": "#1A73E8", "pattern": "Solid", "aisle_location": "Aisle 3"},
            "E288118D": {"epc_id": "E288118D", "sku": "SKU-TRS-02", "name": "Chino Trousers — Khaki", "price": 1199.0, "image_url": "https://assets.retailcart.io/TRS-KHK.webp", "garment_category": "Bottomwear", "garment_type": "Trousers", "style_profile": "Casual", "color_family": "Khaki", "major_color_hex": "#795548", "pattern": "Solid", "aisle_location": "Aisle 4"},
            "E280110D": {"epc_id": "E280110D", "sku": "SKU-TRS-02", "name": "Chino Trousers — Khaki", "price": 1199.0, "image_url": "https://assets.retailcart.io/TRS-KHK.webp", "garment_category": "Bottomwear", "garment_type": "Trousers", "style_profile": "Casual", "color_family": "Khaki", "major_color_hex": "#795548", "pattern": "Solid", "aisle_location": "Aisle 4"},
            "E288110E": {"epc_id": "E288110E", "sku": "SKU-SHT-03", "name": "Cotton Casual Shirt — White", "price": 649.0, "image_url": "https://assets.retailcart.io/SHT-WHT.webp", "garment_category": "Topwear", "garment_type": "Shirt", "style_profile": "Casual", "color_family": "White", "major_color_hex": "#F5F5F5", "pattern": "Solid", "aisle_location": "Aisle 2"},
            "E280110E": {"epc_id": "E280110E", "sku": "SKU-SHT-03", "name": "Cotton Casual Shirt — White", "price": 649.0, "image_url": "https://assets.retailcart.io/SHT-WHT.webp", "garment_category": "Topwear", "garment_type": "Shirt", "style_profile": "Casual", "color_family": "White", "major_color_hex": "#F5F5F5", "pattern": "Solid", "aisle_location": "Aisle 2"},
            "E288110F": {"epc_id": "E288110F", "sku": "SKU-SRT-04", "name": "Cargo Shorts — Olive Green", "price": 899.0, "image_url": "https://assets.retailcart.io/SRT-GRN.webp", "garment_category": "Bottomwear", "garment_type": "Shorts", "style_profile": "Streetwear", "color_family": "Green", "major_color_hex": "#388E3C", "pattern": "Camouflage", "aisle_location": "Aisle 5"},
            "E280110F": {"epc_id": "E280110F", "sku": "SKU-SRT-04", "name": "Cargo Shorts — Olive Green", "price": 899.0, "image_url": "https://assets.retailcart.io/SRT-GRN.webp", "garment_category": "Bottomwear", "garment_type": "Shorts", "style_profile": "Streetwear", "color_family": "Green", "major_color_hex": "#388E3C", "pattern": "Camouflage", "aisle_location": "Aisle 5"},
            "E288110G": {"epc_id": "E288110G", "sku": "SKU-JKT-05", "name": "Classic Denim Jacket — Indigo", "price": 1999.0, "image_url": "https://assets.retailcart.io/JKT-IND.webp", "garment_category": "Topwear", "garment_type": "Jacket", "style_profile": "Streetwear", "color_family": "Indigo", "major_color_hex": "#1A1AFF", "pattern": "Solid", "aisle_location": "Aisle 1"},
            "E280110G": {"epc_id": "E280110G", "sku": "SKU-JKT-05", "name": "Classic Denim Jacket — Indigo", "price": 1999.0, "image_url": "https://assets.retailcart.io/JKT-IND.webp", "garment_category": "Topwear", "garment_type": "Jacket", "style_profile": "Streetwear", "color_family": "Indigo", "major_color_hex": "#1A1AFF", "pattern": "Solid", "aisle_location": "Aisle 1"},
            "E288110H": {"epc_id": "E288110H", "sku": "SKU-SNK-06", "name": "White Minimal Sneakers", "price": 1499.0, "image_url": "https://assets.retailcart.io/SNK-WHT.webp", "garment_category": "Footwear", "garment_type": "Sneakers", "style_profile": "Casual", "color_family": "White", "major_color_hex": "#FFFFFF", "pattern": "Solid", "aisle_location": "Aisle 7"},
            "E280110H": {"epc_id": "E280110H", "sku": "SKU-SNK-06", "name": "White Minimal Sneakers", "price": 1499.0, "image_url": "https://assets.retailcart.io/SNK-WHT.webp", "garment_category": "Footwear", "garment_type": "Sneakers", "style_profile": "Casual", "color_family": "White", "major_color_hex": "#FFFFFF", "pattern": "Solid", "aisle_location": "Aisle 7"},
            "E288110I": {"epc_id": "E288110I", "sku": "SKU-HD-01", "name": "Void Black Oversized Hoodie", "price": 2499.0, "image_url": "https://assets.retailcart.io/HD-BLK.webp", "garment_category": "Topwear", "garment_type": "Hoodie", "style_profile": "Streetwear", "color_family": "Black", "major_color_hex": "#111116", "pattern": "Graphic Print", "aisle_location": "Aisle 1"},
            "E280110I": {"epc_id": "E280110I", "sku": "SKU-HD-01", "name": "Void Black Oversized Hoodie", "price": 2499.0, "image_url": "https://assets.retailcart.io/HD-BLK.webp", "garment_category": "Topwear", "garment_type": "Hoodie", "style_profile": "Streetwear", "color_family": "Black", "major_color_hex": "#111116", "pattern": "Graphic Print", "aisle_location": "Aisle 1"}
        }

        if clean_epc in FALLBACK_CATALOG:
            return FALLBACK_CATALOG[clean_epc]

        return {
            "epc_id": clean_epc,
            "sku": f"SKU-{clean_epc[:6]}",
            "name": f"Garment ({clean_epc})",
            "price": 999.0,
            "image_url": "https://assets.retailcart.io/GENERIC.webp",
            "garment_category": "Topwear",
            "garment_type": "Garment",
            "style_profile": "Casual",
            "color_family": "Blue",
            "major_color_hex": "#00F5FF",
            "pattern": "Solid",
            "aisle_location": "Aisle 1"
        }

        if clean_epc in FALLBACK_CATALOG:
            return FALLBACK_CATALOG[clean_epc]

        return {
            "epc_id": clean_epc,
            "sku": f"SKU-{clean_epc[:6]}",
            "name": f"Zudio Garment ({clean_epc})",
            "price": 999.0,
            "image_url": "https://assets.retailcart.io/GENERIC.webp",
            "garment_category": "Topwear",
            "garment_type": "Garment",
            "style_profile": "Casual",
            "color_family": "Blue",
            "major_color_hex": "#00F5FF",
            "pattern": "Solid",
            "aisle_location": "Aisle 1"
        }

    def scan_epc(self, session_id: str, epc_id: str, store_id: str = "STORE-001") -> dict:
        product = self.resolve_epc(epc_id)
        if not product:
            return {"status": "error", "message": f"EPC '{epc_id}' not found in catalogue", "code": 404}

        sess = self.get_or_create_session(session_id, store_id)
        sku = product["sku"]

        if sku in sess.lines and epc_id in sess.lines[sku].epcs:
            return {
                "status": "success",
                "duplicate_scan": True,
                "epc_id": epc_id,
                "sku": sku,
                "name": product["name"],
                "price": float(product["price"]),
                "quantity": sess.lines[sku].quantity,
                "cart_total": sess.cart_total,
                "raw_total": sess.raw_total,
                "discount_amount": sess.discount_amount,
                "item_count": sess.item_count,
            }

        if sku not in sess.lines:
            line = CartLine(
                sku=sku,
                name=product["name"],
                price=float(product["price"]),
                image_url=product["image_url"],
                quantity=1,
                epcs=[epc_id],
                garment_category=product.get("garment_category", "Topwear"),
                style_profile=product.get("style_profile", "Casual"),
                major_color_hex=product.get("major_color_hex", "#00F5FF"),
                pattern=product.get("pattern", "Solid")
            )
            sess.lines[sku] = line
        else:
            line = sess.lines[sku]
            line.quantity += 1
            if epc_id not in line.epcs:
                line.epcs.append(epc_id)

        try:
            db.execute(
                "INSERT INTO cart_items (session_id, sku, name, price, image_url, quantity, added_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE quantity=VALUES(quantity), updated_at=VALUES(updated_at)",
                (session_id, sku, line.name, line.price, line.image_url, line.quantity, line.added_at, _utc_now())
            )
        except Exception as e:
            logger.error(f"Failed to upsert cart item: {e}")

        self.save_session(sess)

        return {
            "status": "success",
            "duplicate_scan": False,
            "epc_id": epc_id,
            "sku": sku,
            "name": product["name"],
            "price": float(product["price"]),
            "image_url": product["image_url"],
            "garment_category": product.get("garment_category", "Topwear"),
            "garment_type": product.get("garment_type", "Garment"),
            "style_profile": product.get("style_profile", "Casual"),
            "major_color_hex": product.get("major_color_hex", "#00F5FF"),
            "pattern": product.get("pattern", "Solid"),
            "quantity": line.quantity,
            "cart_total": sess.cart_total,
            "raw_total": sess.raw_total,
            "discount_amount": sess.discount_amount,
            "item_count": sess.item_count
        }

    def remove_epc_or_sku(self, session_id: str, epc_id: Optional[str] = None, sku: Optional[str] = None) -> dict:
        sess = self.get_or_create_session(session_id)

        target_sku = sku
        if epc_id and not target_sku:
            product = self.resolve_epc(epc_id)
            if product:
                target_sku = product["sku"]

        if not target_sku or target_sku not in sess.lines:
            return {"status": "error", "message": "Item not found in cart", "code": 404}

        line = sess.lines[target_sku]
        if epc_id and epc_id in line.epcs:
            line.epcs.remove(epc_id)

        line.quantity -= 1
        remaining_qty = line.quantity

        if remaining_qty <= 0:
            del sess.lines[target_sku]
            try:
                db.execute("DELETE FROM cart_items WHERE session_id = %s AND sku = %s", (session_id, target_sku))
            except Exception:
                pass
        else:
            try:
                db.execute(
                    "UPDATE cart_items SET quantity = %s, updated_at = %s WHERE session_id = %s AND sku = %s",
                    (remaining_qty, _utc_now(), session_id, target_sku)
                )
            except Exception:
                pass

        self.save_session(sess)

        return {
            "status": "success",
            "removed_sku": target_sku,
            "remaining_qty": max(0, remaining_qty),
            "cart_total": sess.cart_total,
            "raw_total": sess.raw_total,
            "discount_amount": sess.discount_amount,
            "item_count": sess.item_count
        }

    def update_qty(self, session_id: str, sku: str, quantity: int) -> dict:
        sess = self.get_or_create_session(session_id)
        if quantity <= 0:
            return self.remove_epc_or_sku(session_id, sku=sku)

        if sku not in sess.lines:
            product_rows = []
            try:
                product_rows = db.query("SELECT name, price, image_url FROM product_master WHERE sku = %s", (sku,))
            except Exception:
                pass

            if product_rows:
                p = product_rows[0]
                sess.lines[sku] = CartLine(sku=sku, name=p["name"], price=float(p["price"]), image_url=p["image_url"], quantity=quantity)
            else:
                sess.lines[sku] = CartLine(sku=sku, name=f"Garment ({sku})", price=999.0, image_url="https://assets.retailcart.io/GENERIC.webp", quantity=quantity)
        else:
            sess.lines[sku].quantity = min(10, quantity)

        line = sess.lines[sku]
        try:
            db.execute(
                "INSERT INTO cart_items (session_id, sku, name, price, image_url, quantity, added_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE quantity=VALUES(quantity), updated_at=VALUES(updated_at)",
                (session_id, sku, line.name, line.price, line.image_url, line.quantity, line.added_at, _utc_now())
            )
        except Exception:
            pass

        self.save_session(sess)

        return {
            "status": "success",
            "sku": sku,
            "quantity": line.quantity,
            "cart_total": sess.cart_total,
            "raw_total": sess.raw_total,
            "discount_amount": sess.discount_amount,
            "item_count": sess.item_count
        }

    def clear_session(self, session_id: str) -> dict:
        if session_id in self._in_memory_sessions:
            del self._in_memory_sessions[session_id]
        if redis_client:
            try:
                redis_client.delete(f"cart:{session_id}")
            except Exception:
                pass
        try:
            db.execute("DELETE FROM cart_items WHERE session_id = %s", (session_id,))
            db.execute("UPDATE cart_sessions SET is_active = 0, updated_at = %s WHERE session_id = %s", (_utc_now(), session_id))
        except Exception:
            pass
        return {"status": "success", "message": f"Cart session '{session_id}' cleared"}

    def get_summary(self, session_id: str) -> dict:
        sess = self.get_or_create_session(session_id)
        items = []
        for line in sess.lines.values():
            items.append({
                "sku": line.sku,
                "name": line.name,
                "price": line.price,
                "quantity": line.quantity,
                "line_total": line.line_total,
                "image_url": line.image_url,
                "epcs": line.epcs,
                "garment_category": line.garment_category,
                "style_profile": line.style_profile,
                "major_color_hex": line.major_color_hex,
                "pattern": line.pattern
            })
        return {
            "session_id": sess.session_id,
            "store_id": sess.store_id,
            "item_count": sess.item_count,
            "raw_total": sess.raw_total,
            "applied_deal_code": sess.applied_deal_code,
            "discount_amount": sess.discount_amount,
            "cart_total": sess.cart_total,
            "customer_name": sess.customer_name,
            "customer_phone": sess.customer_phone,
            "items": items
        }

    def _serialize_session(self, sess: CartSession) -> dict:
        return {
            "session_id": sess.session_id,
            "store_id": sess.store_id,
            "created_at": sess.created_at,
            "updated_at": sess.updated_at,
            "applied_deal_code": sess.applied_deal_code,
            "discount_amount": sess.discount_amount,
            "customer_name": sess.customer_name,
            "customer_phone": sess.customer_phone,
            "lines": {
                sku: {
                    "sku": line.sku,
                    "name": line.name,
                    "price": line.price,
                    "image_url": line.image_url,
                    "quantity": line.quantity,
                    "epcs": line.epcs,
                    "added_at": line.added_at,
                    "garment_category": line.garment_category,
                    "style_profile": line.style_profile,
                    "major_color_hex": line.major_color_hex,
                    "pattern": line.pattern
                } for sku, line in sess.lines.items()
            }
        }

    def _deserialize_session(self, data: dict) -> CartSession:
        sess = CartSession(
            session_id=data["session_id"],
            store_id=data.get("store_id", "STORE-001"),
            created_at=data.get("created_at", _utc_now()),
            updated_at=data.get("updated_at", _utc_now()),
            applied_deal_code=data.get("applied_deal_code"),
            discount_amount=float(data.get("discount_amount", 0.0)),
            customer_name=data.get("customer_name", "Valued Customer"),
            customer_phone=data.get("customer_phone", "+918074346103")
        )
        for sku, ldata in data.get("lines", {}).items():
            sess.lines[sku] = CartLine(
                sku=ldata["sku"],
                name=ldata["name"],
                price=float(ldata["price"]),
                image_url=ldata["image_url"],
                quantity=int(ldata["quantity"]),
                epcs=ldata.get("epcs", []),
                added_at=ldata.get("added_at", _utc_now()),
                garment_category=ldata.get("garment_category", "Topwear"),
                style_profile=ldata.get("style_profile", "Casual"),
                major_color_hex=ldata.get("major_color_hex", "#00F5FF"),
                pattern=ldata.get("pattern", "Solid")
            )
        return sess

cart_service = CartService()
