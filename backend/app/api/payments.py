from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from app.services.payment_service import payment_service
from app.services.cart_service import cart_service
from app.services.sms_service import sms_service
from app.api.websocket import manager

router = APIRouter(prefix="", tags=["Payments & Webhook"])

class MockPayRequest(BaseModel):
    session_id: str
    txn_id: Optional[str] = "TXN_MOCK_12345"

@router.post("/cart/{session_id}/checkout/qr")
async def generate_checkout_qr(session_id: str):
    res = payment_service.create_checkout_qr(session_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=res.get("code", 400), detail=res.get("message"))
    return res

@router.post("/payments/webhook")
async def razorpay_webhook(request: Request, x_razorpay_signature: Optional[str] = Header(None)):
    body_bytes = await request.body()
    
    if x_razorpay_signature and not payment_service.verify_razorpay_signature(body_bytes, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay webhook signature")

    try:
        data = await request.json()
        payload = data.get("payload", {}).get("payment", {}).get("entity", {})
        txn_id = payload.get("id", "TXN_RZP_WEBHOOK")
        session_id = payload.get("notes", {}).get("session_id") or data.get("session_id")

        if session_id:
            payment_service.process_payment_success(txn_id=txn_id, session_id=session_id)
            cart_service.clear_session(session_id)
            
            await manager.broadcast_to_cart(session_id, {
                "type": "payment_confirmed",
                "cart_id": session_id,
                "txn_id": txn_id
            })
            await manager.broadcast_to_cart(session_id, {
                "type": "unlock_cart",
                "cart_id": session_id
            })
            return {"status": "success", "message": "Payment verified, automatic SMS sent, and session completed"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {e}")

    return {"status": "ignored"}

@router.post("/payments/mock_pay")
async def mock_payment_simulator(req: MockPayRequest):
    pay_res = payment_service.process_payment_success(txn_id=req.txn_id, session_id=req.session_id)
    
    await manager.broadcast_to_cart(req.session_id, {
        "type": "payment_confirmed",
        "cart_id": req.session_id,
        "txn_id": req.txn_id
    })
    await manager.broadcast_to_cart(req.session_id, {
        "type": "unlock_cart",
        "cart_id": req.session_id
    })

    return {
        "status": "success",
        "message": f"Mock payment of transaction '{req.txn_id}' for session '{req.session_id}' completed. Automatic SMS dispatched.",
        "txn_id": req.txn_id,
        "session_id": req.session_id,
        "sms_details": pay_res.get("sms_delivery")
    }

@router.get("/api/receipt/{session_id}", response_class=HTMLResponse)
async def get_web_receipt(session_id: str):
    summary = cart_service.get_summary(session_id)
    items = summary.get("items", [])
    cart_total = summary.get("cart_total", 799.0)
    raw_total = summary.get("raw_total", 799.0)
    discount = summary.get("discount_amount", 0.0)

    item_rows_html = ""
    if not items:
        item_rows_html = """
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #333">
          <div>
            <div style="font-weight:bold;color:#fff">Men's Slim Kurta — Blue</div>
            <div style="font-size:10px;color:#888">SKU-KRT-01 · Size M</div>
          </div>
          <div style="font-weight:bold;color:#00F5FF">₹799.00</div>
        </div>"""
    else:
        for i in items:
            item_rows_html += f"""
            <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #333">
              <div>
                <div style="font-weight:bold;color:#fff">{i.get('name', 'Garment')}</div>
                <div style="font-size:10px;color:#888">{i.get('sku', 'SKU-01')} · Qty: {i.get('quantity', 1)}</div>
              </div>
              <div style="font-weight:bold;color:#00F5FF">₹{i.get('price', 0):,.2f}</div>
            </div>"""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>InnoCart — Official Digital Receipt #{session_id}</title>
      <style>
        body {{ background: #0A0D14; color: #E2E8F0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; }}
        .card {{ max-width: 420px; margin: 0 auto; background: #131A26; border: 1px solid #1E293B; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        .header {{ text-align: center; border-bottom: 1px dashed #334155; padding-bottom: 16px; margin-bottom: 16px; }}
        .logo {{ font-size: 24px; font-weight: 800; color: #00F5FF; letter-spacing: 2px; }}
        .sub {{ font-size: 11px; color: #94A3B8; margin-top: 4px; }}
        .total-box {{ background: #1E293B; border-radius: 12px; padding: 16px; text-align: center; margin-top: 16px; }}
        .total-val {{ font-size: 28px; font-weight: 800; color: #00FF88; }}
        .footer {{ text-align: center; font-size: 11px; color: #64748B; margin-top: 20px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <div class="logo">INNOCART V2</div>
          <div class="sub">Official Store Receipt · Cart #{session_id}</div>
          <div style="font-size:10px;color:#00FF88;margin-top:6px;font-weight:bold">✓ PAID VIA UPI / RAZORPAY</div>
        </div>

        <div style="margin-bottom: 12px; font-size:12px; font-weight:bold; color:#94A3B8">PURCHASED GARMENTS</div>
        {item_rows_html}

        <div class="total-box">
          <div style="font-size:11px;color:#94A3B8">TOTAL AMOUNT PAID</div>
          <div class="total-val">₹{cart_total:,.2f}</div>
          {f'<div style="font-size:11px;color:#00FF88;margin-top:4px">You saved ₹{discount:,.2f} on this bill!</div>' if discount > 0 else ''}
        </div>

        <div class="footer">
          Thank you for shopping at InnoCart!<br>
          For queries, visit innocart.app or contact support.
        </div>
      </div>
    </body>
    </html>
    """
    return html_content
