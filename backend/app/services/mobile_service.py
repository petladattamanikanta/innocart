import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.core.db import db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.services.cart_service import cart_service
from app.services.styling_service import styling_service
from app.api.websocket import manager

logger = logging.getLogger("innocart.mobile_service")

class MobileService:
    def __init__(self):
        self.in_memory_users: Dict[str, Dict[str, Any]] = {}
        self._ensure_table_columns()

    def _ensure_table_columns(self):
        try:
            db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ DEFAULT NULL")
            db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS skin_texture VARCHAR(50) NOT NULL DEFAULT 'Smooth & Uniform'")
            db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS skin_texture_score FLOAT NOT NULL DEFAULT 0.85")
            db.execute("ALTER TABLE users DROP COLUMN IF EXISTS preferred_style")
        except Exception as e:
            logger.warning(f"Supabase column check notice: {e}")

    def register_user(
        self,
        name: str,
        email: str,
        password: str,
        mobile: Optional[str] = None,
        facial_hex: str = "#D4A373",
        undertone_label: str = "Warm-Golden",
        skin_texture: str = "Smooth & Uniform",
        skin_texture_score: float = 0.85
    ) -> Dict[str, Any]:
        user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
        hashed_pwd = get_password_hash(password)
        user_mobile = mobile or "+91 8074346103"
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        user_obj = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "mobile": user_mobile,
            "password_hash": hashed_pwd,
            "facial_hex": facial_hex,
            "undertone_label": undertone_label,
            "skin_texture": skin_texture,
            "skin_texture_score": skin_texture_score,
            "last_login_at": now_ts
        }

        try:
            db.execute(
                """
                INSERT INTO users (user_id, name, email, password_hash, facial_hex, undertone_label, skin_texture, skin_texture_score, last_login_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, name, email, hashed_pwd, facial_hex, undertone_label, skin_texture, skin_texture_score, now_ts)
            )
        except Exception as e:
            # Fallback if table doesn't have newer columns yet
            try:
                db.execute(
                    """
                    INSERT INTO users (user_id, name, email, password_hash, facial_hex, undertone_label)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, name, email, hashed_pwd, facial_hex, undertone_label)
                )
            except Exception as ex:
                logger.warning(f"MySQL insert user notice: {ex}")

        self.in_memory_users[email.lower()] = user_obj

        token = create_access_token({"sub": user_id, "email": email, "name": name})

        return {
            "status": "success",
            "message": "Mobile user registered successfully",
            "access_token": token,
            "user": {
                "user_id": user_id,
                "name": name,
                "email": email,
                "mobile": user_mobile,
                "facial_hex": facial_hex,
                "undertone_label": undertone_label,
                "skin_texture": skin_texture,
                "skin_texture_score": skin_texture_score,
                "last_login_at": now_ts
            }
        }

    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        email_clean = email.lower()
        user_obj = None

        try:
            users = db.query("SELECT * FROM users WHERE email = %s", (email_clean,))
            if users:
                user_obj = users[0]
        except Exception as e:
            logger.warning(f"MySQL query user notice: {e}")

        if not user_obj and email_clean in self.in_memory_users:
            user_obj = self.in_memory_users[email_clean]

        if not user_obj:
            return {"status": "error", "code": 401, "message": "Invalid email or password."}

        pwd_hash = user_obj.get("password_hash") or user_obj.get("password")
        if pwd_hash and not verify_password(password, pwd_hash):
            return {"status": "error", "code": 401, "message": "Invalid email or password."}

        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Update last_login_at timestamp in DB
        try:
            db.execute(
                "UPDATE users SET last_login_at = %s WHERE user_id = %s",
                (now_ts, user_obj["user_id"])
            )
        except Exception as e:
            logger.warning(f"Failed to update last_login_at timestamp: {e}")

        user_obj["last_login_at"] = now_ts
        if email_clean in self.in_memory_users:
            self.in_memory_users[email_clean]["last_login_at"] = now_ts

        token = create_access_token({"sub": user_obj["user_id"], "email": user_obj["email"], "name": user_obj["name"]})

        return {
            "status": "success",
            "access_token": token,
            "user": {
                "user_id": user_obj["user_id"],
                "name": user_obj["name"],
                "email": user_obj["email"],
                "mobile": user_obj.get("mobile", "+91 8074346103"),
                "facial_hex": user_obj.get("facial_hex", "#D4A373"),
                "undertone_label": user_obj.get("undertone_label", "Warm-Golden"),
                "skin_texture": user_obj.get("skin_texture", "Smooth & Uniform"),
                "skin_texture_score": user_obj.get("skin_texture_score", 0.85),
                "last_login_at": now_ts
            }
        }

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            users = db.query(
                "SELECT user_id, name, email, facial_hex, undertone_label, skin_texture, skin_texture_score, created_at, last_login_at FROM users WHERE user_id = %s",
                (user_id,)
            )
            if users:
                return {"status": "success", "profile": users[0]}
        except Exception as e:
            logger.warning(f"DB profile lookup notice: {e}")

        for u in self.in_memory_users.values():
            if u["user_id"] == user_id:
                return {"status": "success", "profile": u}

        return {"status": "error", "code": 404, "message": "User profile not found."}

    def update_user_profile(
        self,
        user_id: str,
        facial_hex: str,
        undertone_label: str,
        skin_texture: str = "Smooth & Uniform",
        skin_texture_score: float = 0.85
    ) -> Dict[str, Any]:
        try:
            db.execute(
                """
                UPDATE users SET facial_hex = %s, undertone_label = %s, skin_texture = %s, skin_texture_score = %s
                WHERE user_id = %s
                """,
                (facial_hex, undertone_label, skin_texture, skin_texture_score, user_id)
            )
        except Exception as e:
            logger.warning(f"DB update notice: {e}")

        for u in self.in_memory_users.values():
            if u["user_id"] == user_id:
                u["facial_hex"] = facial_hex
                u["undertone_label"] = undertone_label
                u["skin_texture"] = skin_texture
                u["skin_texture_score"] = skin_texture_score
                return {"status": "success", "profile": u}

        return self.get_user_profile(user_id)

    async def initiate_session(
        self,
        session_id: str,
        user_id: Optional[str],
        name: str,
        facial_hex: str,
        undertone_label: str,
        skin_texture: str = "Smooth & Uniform",
        mobile: Optional[str] = None
    ) -> Dict[str, Any]:
        target_mobile = mobile or "+918074346103"
        logger.info(f"Mobile Companion initiating session '{session_id}' for user '{name}' with mobile '{target_mobile}'")

        # BIND CUSTOMER REGISTERED MOBILE TO CART SESSION
        cart_service.bind_user_to_session(session_id=session_id, name=name, mobile=target_mobile, facial_hex=facial_hex)

        payload = {
            "type": "user_profile_synced",
            "session_id": session_id,
            "user": {
                "user_id": user_id or f"USR-{uuid.uuid4().hex[:8].upper()}",
                "name": name,
                "mobile": target_mobile,
                "facial_hex": facial_hex,
                "undertone_label": undertone_label,
                "skin_texture": skin_texture
            }
        }

        await manager.broadcast_to_cart(session_id, payload)
        cart_summary = cart_service.get_summary(session_id)

        return {
            "status": "success",
            "message": f"Session {session_id} initiated and registered mobile number '{target_mobile}' bound successfully.",
            "session_id": session_id,
            "registered_mobile": target_mobile,
            "telemetry": payload,
            "cart": cart_summary
        }

    def get_recommendations_for_user(self, facial_hex: str) -> List[Dict[str, Any]]:
        return styling_service.get_cart_wearable_recommendations(
            cart_items=[],
            top_n=4,
            facial_hex=facial_hex
        )

mobile_service = MobileService()