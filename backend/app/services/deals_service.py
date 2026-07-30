import logging
from typing import List, Dict, Optional
from app.core.db import db
from app.services.cart_service import cart_service, CartSession

logger = logging.getLogger("innocart.deals_service")

class DealsService:
    def get_active_deals(self) -> List[dict]:
        rows = db.query(
            "SELECT deal_code, title, description, discount_type, discount_value, min_cart_value, category_restriction, badge_text "
            "FROM deals WHERE is_active = 1"
        )
        return [
            {
                "deal_code": r["deal_code"],
                "title": r["title"],
                "description": r["description"],
                "discount_type": r["discount_type"],
                "discount_value": float(r["discount_value"]),
                "min_cart_value": float(r["min_cart_value"]),
                "category_restriction": r["category_restriction"],
                "badge_text": r["badge_text"]
            }
            for r in rows
        ]

    def get_eligible_deals(self, session_id: str) -> List[dict]:
        sess = cart_service.get_or_create_session(session_id)
        all_deals = self.get_active_deals()
        eligible = []

        cart_raw_total = sess.raw_total
        categories_in_cart = {line.name for line in sess.lines.values()} # SKU/Category check

        for d in all_deals:
            is_eligible = True
            reason = None

            if cart_raw_total < d["min_cart_value"]:
                is_eligible = False
                shortfall = d["min_cart_value"] - cart_raw_total
                reason = f"Add ₹{shortfall:.0f} more to unlock"

            # Compute potential discount amount
            potential_discount = 0.0
            if is_eligible:
                if d["discount_type"] == "FIXED":
                    potential_discount = d["discount_value"]
                elif d["discount_type"] == "PERCENTAGE":
                    potential_discount = round((cart_raw_total * d["discount_value"]) / 100.0, 2)

            is_applied = (sess.applied_deal_code == d["deal_code"])

            eligible.append({
                **d,
                "is_eligible": is_eligible,
                "is_applied": is_applied,
                "ineligibility_reason": reason,
                "potential_discount": potential_discount
            })

        return eligible

    def apply_deal(self, session_id: str, deal_code: str) -> dict:
        sess = cart_service.get_or_create_session(session_id)
        deals = self.get_active_deals()
        deal = next((d for d in deals if d["deal_code"] == deal_code), None)

        if not deal:
            return {"status": "error", "message": f"Deal code '{deal_code}' not found", "code": 404}

        if sess.raw_total < deal["min_cart_value"]:
            return {
                "status": "error",
                "message": f"Cart total ₹{sess.raw_total} does not meet minimum requirement of ₹{deal['min_cart_value']}",
                "code": 400
            }

        discount = 0.0
        if deal["discount_type"] == "FIXED":
            discount = deal["discount_value"]
        elif deal["discount_type"] == "PERCENTAGE":
            discount = round((sess.raw_total * deal["discount_value"]) / 100.0, 2)

        sess.applied_deal_code = deal_code
        sess.discount_amount = discount
        cart_service.save_session(sess)

        return {
            "status": "success",
            "message": f"Deal '{deal['title']}' applied successfully",
            "deal_code": deal_code,
            "discount_amount": discount,
            "cart_total": sess.cart_total
        }

    def remove_deal(self, session_id: str) -> dict:
        sess = cart_service.get_or_create_session(session_id)
        sess.applied_deal_code = None
        sess.discount_amount = 0.0
        cart_service.save_session(sess)
        return {"status": "success", "message": "Deal removed", "cart_total": sess.cart_total}

deals_service = DealsService()
