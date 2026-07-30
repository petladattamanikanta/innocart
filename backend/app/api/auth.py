import uuid
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from app.core.db import db
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.api.websocket import manager

logger = logging.getLogger("innocart.auth")
router = APIRouter(prefix="/api", tags=["App User Auth & Personalization Sync"])

# Request/Response Schemas
class UserRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    facial_hex: Optional[str] = "#D4A373"
    undertone_label: Optional[str] = "Warm-Golden"

class UserLoginRequest(BaseModel):
    email: str
    password: str

class SyncProfileRequest(BaseModel):
    session_id: str = "IC-042"
    user_id: Optional[str] = None
    name: str = "Alex"
    facial_hex: str = "#D4A373"
    undertone_label: str = "Warm-Golden"

# 1. User Registration Endpoint
@router.post("/auth/register")
def register_user(req: UserRegisterRequest):
    # Check if user with email exists
    existing = db.query("SELECT user_id FROM users WHERE email = %s", (req.email,))
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    hashed_pwd = get_password_hash(req.password)
    from datetime import datetime, timezone
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        db.execute(
            """
            INSERT INTO users (user_id, name, email, password_hash, facial_hex, undertone_label, skin_texture, skin_texture_score, last_login_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, req.name, req.email, hashed_pwd, req.facial_hex, req.undertone_label, "Smooth & Uniform", 0.85, now_ts)
        )
    except Exception:
        db.execute(
            """
            INSERT INTO users (user_id, name, email, password_hash, facial_hex, undertone_label)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, req.name, req.email, hashed_pwd, req.facial_hex, req.undertone_label)
        )

    token = create_access_token({"sub": user_id, "email": req.email, "name": req.name})

    return {
        "status": "success",
        "message": "User registered successfully",
        "access_token": token,
        "user": {
            "user_id": user_id,
            "name": req.name,
            "email": req.email,
            "facial_hex": req.facial_hex,
            "undertone_label": req.undertone_label,
            "last_login_at": now_ts
        }
    }

# 2. User Login Endpoint
@router.post("/auth/login")
def login_user(req: UserLoginRequest):
    users = db.query("SELECT * FROM users WHERE email = %s", (req.email,))
    if not users:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user = users[0]
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    from datetime import datetime, timezone
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        db.execute(
            "UPDATE users SET last_login_at = %s WHERE user_id = %s",
            (now_ts, user["user_id"])
        )
    except Exception as e:
        logger.warning(f"Failed to update last_login_at: {e}")

    token = create_access_token({"sub": user["user_id"], "email": user["email"], "name": user["name"]})

    return {
        "status": "success",
        "access_token": token,
        "user": {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "facial_hex": user["facial_hex"],
            "undertone_label": user["undertone_label"],
            "last_login_at": now_ts
        }
    }

# 3. Get Current User Profile Endpoint
@router.get("/user/profile/{user_id}")
def get_user_profile(user_id: str):
    users = db.query("SELECT user_id, name, email, facial_hex, undertone_label, created_at, last_login_at FROM users WHERE user_id = %s", (user_id,))
    if not users:
        raise HTTPException(status_code=404, detail="User profile not found.")
    return users[0]

# 4. Sync Mobile Profile to Cart Session (Called after QR Code Scan)
@router.post("/cart/sync-profile")
@router.post("/cart/sync_profile")
@router.post("/session/initiate")
async def sync_profile_to_cart(req: SyncProfileRequest):
    logger.info(f"Syncing profile for user '{req.name}' to cart session '{req.session_id}'")

    from app.services.cart_service import cart_service
    cart_service.bind_user_to_session(
        session_id=req.session_id,
        name=req.name or "Customer",
        mobile="+918074346103",
        facial_hex=req.facial_hex or "#D4A373"
    )

    payload = {
        "type": "user_profile_synced",
        "session_id": req.session_id,
        "user": {
            "user_id": req.user_id or "USR-001",
            "name": req.name,
            "facial_hex": req.facial_hex,
            "undertone_label": req.undertone_label
        }
    }

    # Broadcast directly to active touchscreen kiosk WebSocket
    await manager.broadcast_to_cart(req.session_id, payload)

    return {
        "status": "success",
        "message": f"Profile successfully synced to cart {req.session_id}",
        "synced_data": payload
    }
