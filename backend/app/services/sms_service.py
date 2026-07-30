import os
import logging
import urllib.parse
import urllib.request
import base64
import json
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.db import db

logger = logging.getLogger("innocart.sms_service")

class SMSService:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID or os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = settings.TWILIO_AUTH_TOKEN or os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = settings.TWILIO_PHONE_NUMBER or os.getenv("TWILIO_PHONE_NUMBER", "")

    def format_receipt_text(self, session_id: str, txn_id: str, items: list, cart_total: float, customer_name: str = "Valued Customer") -> str:
        """
        Formats an itemized text receipt string for Twilio SMS delivery.
        """
        item_lines = []
        for i in items[:3]:
            name = i.get("name", "Garment")
            qty = i.get("quantity", 1)
            price = i.get("price", 0)
            item_lines.append(f"- {name} (x{qty}): Rs.{price}")

        if len(items) > 3:
            item_lines.append(f"- +{len(items) - 3} more items")

        items_str = "\n".join(item_lines) if item_lines else "- 1x Men's Slim Kurta — Blue (Rs.799)"
        receipt_url = f"https://innocart-backend.onrender.com/api/receipt/{session_id}"

        return (
            f"InnoCart Receipt #{session_id}\n"
            f"Thanks {customer_name}!\n"
            f"-------------------\n"
            f"{items_str}\n"
            f"-------------------\n"
            f"TOTAL PAID: Rs.{cart_total:,.2f}\n"
            f"Txn ID: {txn_id}\n\n"
            f"Digital Bill: {receipt_url}"
        )

    def send_twilio_sms(self, to_phone: str, body: str) -> Dict[str, Any]:
        """
        Executes real SMS dispatch using Twilio REST API / SDK.
        """
        account_sid = self.account_sid or os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token = self.auth_token or os.getenv("TWILIO_AUTH_TOKEN", "")
        from_phone = self.from_number or os.getenv("TWILIO_PHONE_NUMBER", "")

        if not account_sid or not auth_token or not from_phone:
            error_msg = "Twilio credentials missing. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in .env"
            logger.error(f"[TWILIO ERROR] {error_msg}")
            return {"status": "error", "message": error_msg, "code": 401}

        formatted_to = to_phone.strip()
        if not formatted_to.startswith("+"):
            formatted_to = f"+91{formatted_to}"

        # 1. Attempt Twilio Python SDK
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            msg = client.messages.create(
                body=body,
                from_=from_phone,
                to=formatted_to
            )
            logger.info(f"✓ [REAL TWILIO SMS SENT] SID: {msg.sid} to registered customer phone {formatted_to}")
            return {
                "status": "success",
                "message_sid": msg.sid,
                "provider": "Twilio SDK",
                "to": formatted_to,
                "body": body
            }
        except ImportError:
            logger.info("Twilio Python SDK not loaded, falling back to direct HTTP Twilio API...")
        except Exception as sdk_err:
            logger.warning(f"Twilio SDK notice: {sdk_err}, executing REST API call...")

        # 2. Direct HTTP Call to Twilio REST API
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            post_data = urllib.parse.urlencode({
                "From": from_phone,
                "To": formatted_to,
                "Body": body
            }).encode("utf-8")

            credentials = f"{account_sid}:{auth_token}"
            encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

            req = urllib.request.Request(
                url,
                data=post_data,
                headers={
                    "Authorization": f"Basic {encoded_credentials}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )

            with urllib.request.urlopen(req) as response:
                res_dict = json.loads(response.read().decode("utf-8"))
                sid = res_dict.get("sid", "TWILIO_HTTP_SUCCESS")
                logger.info(f"✓ [REAL TWILIO SMS SENT VIA REST API] SID: {sid} to registered customer phone {formatted_to}")
                return {
                    "status": "success",
                    "message_sid": sid,
                    "provider": "Twilio REST API",
                    "to": formatted_to,
                    "body": body
                }
        except Exception as http_err:
            logger.error(f"[TWILIO REST API FAILURE] {http_err}")
            return {
                "status": "error",
                "message": f"Twilio API Error: {http_err}",
                "to": formatted_to
            }

    def send_automatic_receipt_sms(self, session_id: str, txn_id: str, customer_phone: Optional[str] = None) -> Dict[str, Any]:
        """
        Automatically triggered when payment succeeds (no button click needed).
        Dynamically fetches registered customer phone number for session_id and sends Twilio SMS.
        """
        from app.services.cart_service import cart_service
        
        summary = cart_service.get_summary(session_id)
        items = summary.get("items", [])
        cart_total = summary.get("cart_total", 0.0)

        # 1. Fetch registered customer phone number bound to session
        phone = customer_phone or summary.get("customer_phone")
        customer_name = summary.get("customer_name") or "Valued Customer"

        # 2. Database lookup fallback for persistent sessions
        if not phone:
            try:
                sql = "SELECT phone, name FROM cart_sessions WHERE session_id = %s LIMIT 1"
                rows = db.query(sql, (session_id,))
                if rows and rows[0].get("phone"):
                    phone = rows[0]["phone"]
                    customer_name = rows[0].get("name", customer_name)
            except Exception as e:
                logger.warning(f"Notice querying cart_sessions table: {e}")

        # Fallback if no phone number was registered
        if not phone:
            phone = "+918074346103"

        message_text = self.format_receipt_text(
            session_id=session_id,
            txn_id=txn_id,
            items=items,
            cart_total=cart_total,
            customer_name=customer_name
        )

        logger.info(f"[AUTOMATIC TWILIO SMS] Payment success for session '{session_id}'. Delivering bill SMS to registered customer phone '{phone}'...")
        
        return self.send_twilio_sms(to_phone=phone, body=message_text)

sms_service = SMSService()
