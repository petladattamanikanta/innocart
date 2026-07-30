from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.cart_service import cart_service
from app.services.analytics_service import analytics_service
from app.api.websocket import manager

router = APIRouter(prefix="", tags=["Cart Sessions"])

class ScanRequest(BaseModel):
    session_id: str
    epc_id: str
    store_id: Optional[str] = "STORE-001"

class RemoveRequest(BaseModel):
    session_id: str
    epc_id: Optional[str] = None
    sku: Optional[str] = None

class QtyRequest(BaseModel):
    session_id: str
    sku: str
    quantity: int

class CartStylingRequest(BaseModel):
    session_id: str
    facial_hex: Optional[str] = "#C8A882"
    user_style: Optional[str] = "Streetwear"

@router.post("/cart/scan")
async def scan_item(req: ScanRequest):
    res = cart_service.scan_epc(session_id=req.session_id, epc_id=req.epc_id, store_id=req.store_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    
    summary = cart_service.get_summary(req.session_id)
    await manager.broadcast_to_cart(req.session_id, {
        "type": "cart_update",
        "cart_id": req.session_id,
        "items": summary["items"],
        "cart_total": summary["cart_total"],
        "raw_total": summary["raw_total"],
        "discount_amount": summary["discount_amount"],
        "item_count": summary["item_count"]
    })
    return res

@router.post("/cart/remove")
async def remove_item(req: RemoveRequest):
    if req.epc_id:
        prod = cart_service.resolve_epc(req.epc_id)
        if prod:
            analytics_service.record_lost_sale(session_id=req.session_id, epc_id=req.epc_id, sku=prod["sku"], product_name=prod["name"])
            
    res = cart_service.remove_epc_or_sku(session_id=req.session_id, epc_id=req.epc_id, sku=req.sku)
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    
    summary = cart_service.get_summary(req.session_id)
    await manager.broadcast_to_cart(req.session_id, {
        "type": "cart_update",
        "cart_id": req.session_id,
        "items": summary["items"],
        "cart_total": summary["cart_total"],
        "raw_total": summary["raw_total"],
        "discount_amount": summary["discount_amount"],
        "item_count": summary["item_count"]
    })
    return res

@router.post("/cart/qty")
async def update_quantity(req: QtyRequest):
    res = cart_service.update_qty(session_id=req.session_id, sku=req.sku, quantity=req.quantity)
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    
    summary = cart_service.get_summary(req.session_id)
    await manager.broadcast_to_cart(req.session_id, {
        "type": "cart_update",
        "cart_id": req.session_id,
        "items": summary["items"],
        "cart_total": summary["cart_total"],
        "raw_total": summary["raw_total"],
        "discount_amount": summary["discount_amount"],
        "item_count": summary["item_count"]
    })
    return res

@router.get("/cart/{session_id}")
async def get_cart(session_id: str):
    return cart_service.get_summary(session_id)

@router.get("/cart/{session_id}/ai_styling")
async def get_cart_ai_styling_endpoint(session_id: str, facial_hex: str = "#C8A882", user_style: str = "Streetwear"):
    from app.services.styling_service import styling_service
    return styling_service.get_cart_ai_styling(session_id=session_id, facial_hex=facial_hex, user_style=user_style)

@router.post("/cart/ai_styling")
async def post_cart_ai_styling_endpoint(req: CartStylingRequest):
    from app.services.styling_service import styling_service
    return styling_service.get_cart_ai_styling(session_id=req.session_id, facial_hex=req.facial_hex, user_style=req.user_style)

@router.get("/cart/{session_id}/summary")
async def get_cart_summary(session_id: str):
    summary = cart_service.get_summary(session_id)
    if summary["item_count"] == 0:
        raise HTTPException(status_code=400, detail="Cart is empty")
    return summary

@router.delete("/cart/{session_id}")
async def clear_cart(session_id: str):
    res = cart_service.clear_session(session_id)
    await manager.broadcast_to_cart(session_id, {
        "type": "cart_update",
        "cart_id": session_id,
        "items": [],
        "cart_total": 0.0,
        "raw_total": 0.0,
        "discount_amount": 0.0,
        "item_count": 0
    })
    return res
