import logging
from app.core.db import db

logger = logging.getLogger("innocart.analytics_service")

class AnalyticsService:
    def record_lost_sale(self, session_id: str, epc_id: str, sku: str, product_name: str, dwell_seconds: int = 0, store_id: str = "STORE-001"):
        try:
            db.execute(
                "INSERT INTO lost_sale_events (session_id, store_id, sku, product_name, epc_id, time_in_cart_seconds) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (session_id, store_id, sku, product_name, epc_id, dwell_seconds)
            )
            logger.info(f"Recorded lost sale event for SKU {sku} in session {session_id}")
        except Exception as e:
            logger.error(f"Failed to record lost sale: {e}")

    def get_lost_sales_summary(self, store_id: str = "STORE-001") -> dict:
        sql_top_rejected = """
            SELECT sku, product_name, COUNT(*) as rejection_count, AVG(time_in_cart_seconds) as avg_dwell_seconds
            FROM lost_sale_events
            WHERE store_id = %s
            GROUP BY sku, product_name
            ORDER BY rejection_count DESC
            LIMIT 10
        """
        top_rejected = db.query(sql_top_rejected, (store_id,))

        sql_total_lost = "SELECT COUNT(*) as total_events FROM lost_sale_events WHERE store_id = %s"
        total_rows = db.query(sql_total_lost, (store_id,))
        total_events = total_rows[0]["total_events"] if total_rows else 0

        return {
            "store_id": store_id,
            "total_rejection_events": total_events,
            "top_rejected_products": [
                {
                    "sku": r["sku"],
                    "product_name": r["product_name"],
                    "rejection_count": r["rejection_count"],
                    "avg_dwell_seconds": round(float(r["avg_dwell_seconds"] or 0), 1)
                } for r in top_rejected
            ]
        }

analytics_service = AnalyticsService()
