from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.deals_service import deals_service

router = APIRouter(prefix="/cart", tags=["Rush Deals Engine"])

class ApplyDealRequest(BaseModel):
    deal_code: str

@router.get("/{session_id}/deals")
async def get_eligible_deals(session_id: str):
    return deals_service.get_eligible_deals(session_id)

@router.post("/{session_id}/deals/apply")
async def apply_deal(session_id: str, req: ApplyDealRequest):
    res = deals_service.apply_deal(session_id, req.deal_code)
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    return res

@router.post("/{session_id}/deals/remove")
async def remove_deal(session_id: str):
    return deals_service.remove_deal(session_id)
