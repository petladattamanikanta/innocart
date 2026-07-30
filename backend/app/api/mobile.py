from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.services.mobile_service import mobile_service
from app.services.cart_service import cart_service
from app.services.cv_service import cv_service

router = APIRouter(prefix="/api/mobile", tags=["Mobile Companion App API"])

# Request Schemas
class FaceScanBase64Request(BaseModel):
    image_base64: str

class MobileRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    mobile: Optional[str] = "+91 98765 43210"
    facial_hex: Optional[str] = "#D4A373"
    undertone_label: Optional[str] = "Warm-Golden"
    skin_texture: Optional[str] = "Smooth & Uniform"
    skin_texture_score: Optional[float] = 0.85

class MobileLoginRequest(BaseModel):
    email: str
    password: str

class MobileProfileUpdateRequest(BaseModel):
    facial_hex: str = "#D4A373"
    undertone_label: str = "Warm-Golden"
    skin_texture: Optional[str] = "Smooth & Uniform"
    skin_texture_score: Optional[float] = 0.85

class MobileSessionInitiateRequest(BaseModel):
    session_id: str = "IC-042"
    user_id: Optional[str] = None
    name: str = "Alex"
    mobile: Optional[str] = "+91 98765 43210"
    facial_hex: str = "#D4A373"
    undertone_label: str = "Warm-Golden"
    skin_texture: str = "Smooth & Uniform"

# 0. AI Facial & Skin Analysis Endpoint (Gemini 1.5 Vision + OpenCV Fallback)
@router.post("/cv/scan-face")
async def scan_face_telemetry(
    file: Optional[UploadFile] = File(None),
    payload: Optional[FaceScanBase64Request] = None
):
    """
    AI Face & Skin Analysis Pipeline:
    Uses Gemini 1.5 Vision AI (with OpenCV fallback) to extract:
    - Fitzpatrick Skin Type & Complexion Description
    - Suitable Wardrobe Colors & Colors to Avoid
    - Skin Care Considerations & Routine
    - Facial Hex, Undertone Label, and Texture Smoothness
    """
    image_bytes = None
    if file and file.filename:
        image_bytes = await file.read()
    elif payload and payload.image_base64:
        image_bytes = cv_service.parse_base64_image(payload.image_base64)
    else:
        raise HTTPException(status_code=400, detail="Please upload a selfie photo or base64 image payload.")

    # 1. Algorithmic OpenCV Extraction
    cv_telemetry = cv_service.analyze_skin_telemetry(image_bytes)

    # 2. Multimodal Gemini 1.5 Vision Analysis
    gemini_telemetry = await gemini_service.analyze_face_and_skin(image_bytes, cv_telemetry)

    # Merge results
    merged = {**cv_telemetry, **gemini_telemetry}
    return merged

# 1. Register Mobile User
@router.post("/auth/register")
def register_mobile_user(req: MobileRegisterRequest):
    res = mobile_service.register_user(
        name=req.name,
        email=req.email,
        password=req.password,
        mobile=req.mobile,
        facial_hex=req.facial_hex or "#D4A373",
        undertone_label=req.undertone_label or "Warm-Golden",
        skin_texture=req.skin_texture or "Smooth & Uniform",
        skin_texture_score=req.skin_texture_score or 0.85
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    return res

# 2. Login Mobile User
@router.post("/auth/login")
def login_mobile_user(req: MobileLoginRequest):
    res = mobile_service.login_user(email=req.email, password=req.password)
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 401), detail=res.get("message"))
    return res

# 3. Get Mobile User Profile
@router.get("/profile/{user_id}")
def get_mobile_profile(user_id: str):
    res = mobile_service.get_user_profile(user_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 404), detail=res.get("message"))
    return res["profile"]

# 4. Update Mobile User Profile
@router.put("/profile/{user_id}")
def update_mobile_profile(user_id: str, req: MobileProfileUpdateRequest):
    res = mobile_service.update_user_profile(
        user_id=user_id,
        facial_hex=req.facial_hex,
        undertone_label=req.undertone_label,
        skin_texture=req.skin_texture or "Smooth & Uniform",
        skin_texture_score=req.skin_texture_score or 0.85
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    return res["profile"]

# 5. Initiate Cart Kiosk Session
@router.post("/session/initiate")
async def initiate_mobile_cart_session(req: MobileSessionInitiateRequest):
    res = await mobile_service.initiate_session(
        session_id=req.session_id,
        user_id=req.user_id,
        name=req.name,
        facial_hex=req.facial_hex,
        undertone_label=req.undertone_label,
        skin_texture=req.skin_texture,
        mobile=req.mobile
    )
    return res

# 6. Fetch Live Mobile Cart Contents
@router.get("/session/{session_id}/cart")
def get_mobile_cart(session_id: str):
    return cart_service.get_summary(session_id)

# 7. Get Skin-Matched Styling Recommendations
@router.get("/recommendations")
def get_mobile_recommendations(facial_hex: str = "#D4A373"):
    recs = mobile_service.get_recommendations_for_user(facial_hex=facial_hex)
    return {"status": "success", "facial_hex": facial_hex, "recommendations": recs}
