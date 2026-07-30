import hmac
import hashlib
import uuid
import logging
from datetime import datetime, timezone
from app.core.config import settings
from app.core.db import db
from app.services.cart_service import cart_service
from app.services.sms_service import sms_service

logger = logging.getLogger("innocart.payment_service")

class PaymentService:
    def create_checkout_qr(self, session_id: str) -> dict:
        sess = cart_service.get_or_create_session(session_id)
        if sess.item_count == 0 or sess.cart_total <= 0:
            return {"status": "error", "message": "Cart is empty", "code": 400}

        txn_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        amount = sess.cart_total

        # Save pending transaction
        try:
            db.execute(
                "INSERT INTO transactions (txn_id, session_id, store_id, amount, status) "
                "VALUES (%s, %s, %s, %s, 'PENDING')",
                (txn_id, session_id, sess.store_id, amount)
            )
        except Exception as e:
            logger.error(f"Failed to record transaction in DB: {e}")

        # UPI payload spec: upi://pay?pa=innocart@razorpay&pn=InnoCart%20Store&am=123.45&tn=CART-001&tr=TXN_123
        upi_string = f"upi://pay?pa=innocart@razorpay&pn=InnoCart%20V2%20Store&am={amount:.2f}&tn={session_id}&tr={txn_id}"
        
        # QR image API URL via quickchart/google charts format or SVG
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_string}"

        return {
            "status": "success",
            "txn_id": txn_id,
            "session_id": session_id,
            "amount": amount,
            "raw_total": sess.raw_total,
            "discount_amount": sess.discount_amount,
            "item_count": sess.item_count,
            "upi_string": upi_string,
            "qr_code_url": qr_code_url,
            "expires_in_seconds": 600
        }

    def verify_razorpay_signature(self, body_bytes: bytes, signature: str) -> bool:
        expected_sig = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature)

    def process_payment_success(self, txn_id: str, session_id: str) -> dict:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            db.execute(
                "UPDATE transactions SET status = 'SUCCESS', completed_at = %s WHERE txn_id = %s OR session_id = %s",
                (now_str, txn_id, session_id)
            )
        except Exception as e:
            logger.warning(f"Notice updating transaction status: {e}")

        # AUTOMATIC SMS RECEIPT DISPATCH UPON PAYMENT SUCCESS (NO BUTTON CLICK NEEDED)
        sms_res = sms_service.send_automatic_receipt_sms(session_id=session_id, txn_id=txn_id)

        return {
            "status": "success",
            "txn_id": txn_id,
            "session_id": session_id,
            "sms_delivery": sms_res
        }

payment_service = PaymentService()
