from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.services.styling_service import styling_service

router = APIRouter(prefix="/api", tags=["AI Styling Engine"])

class WearableRequest(BaseModel):
    epc_ids: List[str]

class StyleRequest(BaseModel):
    epc_id: Optional[str] = None
    sku: Optional[str] = None
    user_style: str = "Streetwear"
    facial_hex: str = "#C8A882"
    suggest_mode: str = "outfit"
    top_n: int = 3
    user_skin_tone: str = "Neutral"

class ClassifyHexRequest(BaseModel):
    hex: str

@router.post("/get_cart_wearable")
async def get_cart_wearable(req: WearableRequest):
    topwear = []
    bottomwear = []
    for epc in req.epc_ids:
        item = styling_service.resolve_epc(epc)
        if item:
            item_dict = {
                "sku": item.sku,
                "name": item.name,
                "price": item.price,
                "garment_category": item.garment_category,
                "garment_type": item.garment_type,
                "style_profile": item.style_profile,
                "color_family": item.color_family,
                "image_url": item.image_url,
                "aisle_location": item.aisle_location,
                "epc": epc
            }
            if item.garment_category == "Topwear":
                topwear.append(item_dict)
            elif item.garment_category == "Bottomwear":
                bottomwear.append(item_dict)

    return {
        "topwear": topwear,
        "bottomwear": bottomwear,
        "total_wearable": len(topwear) + len(bottomwear)
    }

@router.post("/get_style")
async def get_style_suggestions(req: StyleRequest):
    res = styling_service.recommend(
        epc_id=req.epc_id,
        sku=req.sku,
        user_style=req.user_style,
        facial_hex=req.facial_hex,
        suggest_mode="outfit",
        top_n=req.top_n,
        user_skin_tone=req.user_skin_tone
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    return res

@router.post("/suggest_footwear")
async def suggest_footwear(req: StyleRequest):
    res = styling_service.recommend(
        epc_id=req.epc_id,
        sku=req.sku,
        user_style=req.user_style,
        facial_hex=req.facial_hex,
        suggest_mode="footwear",
        top_n=req.top_n,
        user_skin_tone=req.user_skin_tone
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    return res

@router.post("/suggest_accessories")
async def suggest_accessories(req: StyleRequest):
    res = styling_service.recommend(
        epc_id=req.epc_id,
        sku=req.sku,
        user_style=req.user_style,
        facial_hex=req.facial_hex,
        suggest_mode="accessories",
        top_n=req.top_n,
        user_skin_tone=req.user_skin_tone
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    return res

@router.post("/classify_hex")
async def classify_hex(req: ClassifyHexRequest):
    undertone = styling_service.classify_hex(req.hex)
    from app.services.styling_service import hex_to_hsl
    h, s, l = hex_to_hsl(req.hex)
    return {
        "hex": req.hex,
        "undertone_label": undertone,
        "hsl": {"h": h, "s": s, "l": l}
    }

@router.post("/reload_scoring")
async def reload_scoring():
    styling_service.reload_scoring_tables()
    return {"status": "success", "message": "5-stage AI scoring tables reloaded from database"}
