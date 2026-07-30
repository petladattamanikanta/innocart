import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.cart_service import cart_service
from app.services.payment_service import payment_service
from app.services.analytics_service import analytics_service

logger = logging.getLogger("innocart.websocket")
router = APIRouter()

class ConnectionManager:
    """Manages active WebSocket connections per cart_id namespace."""
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, cart_id: str, websocket: WebSocket):
        await websocket.accept()
        if cart_id not in self.active_connections:
            self.active_connections[cart_id] = set()
        self.active_connections[cart_id].add(websocket)
        logger.info(f"WebSocket connected for cart '{cart_id}'. Active connections: {len(self.active_connections[cart_id])}")

    def disconnect(self, cart_id: str, websocket: WebSocket):
        if cart_id in self.active_connections:
            self.active_connections[cart_id].discard(websocket)
            if not self.active_connections[cart_id]:
                del self.active_connections[cart_id]
        logger.info(f"WebSocket disconnected for cart '{cart_id}'")

    async def broadcast_to_cart(self, cart_id: str, message: dict):
        if cart_id in self.active_connections:
            dead_sockets = set()
            payload = json.dumps(message)
            for ws in self.active_connections[cart_id]:
                try:
                    await ws.send_text(payload)
                except Exception as e:
                    logger.warning(f"Error broadcasting to WS: {e}")
                    dead_sockets.add(ws)
            for ws in dead_sockets:
                self.disconnect(cart_id, ws)

manager = ConnectionManager()

@router.websocket("/ws/cart/{cart_id}")
async def cart_websocket_endpoint(websocket: WebSocket, cart_id: str):
    await manager.connect(cart_id, websocket)
    
    # Send initial cart state upon connection
    summary = cart_service.get_summary(cart_id)
    await websocket.send_text(json.dumps({
        "type": "cart_update",
        "cart_id": cart_id,
        "items": summary["items"],
        "cart_total": summary["cart_total"],
        "raw_total": summary["raw_total"],
        "discount_amount": summary["discount_amount"],
        "item_count": summary["item_count"]
    }))

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
                msg_type = msg.get("type")

                if msg_type == "epc_scan":
                    epc_id = msg.get("epc_id")
                    if epc_id:
                        res = cart_service.scan_epc(session_id=cart_id, epc_id=epc_id)
                        summary = cart_service.get_summary(cart_id)
                        await manager.broadcast_to_cart(cart_id, {
                            "type": "cart_update",
                            "cart_id": cart_id,
                            "last_action": "scan",
                            "scanned_item": res,
                            "items": summary["items"],
                            "cart_total": summary["cart_total"],
                            "raw_total": summary["raw_total"],
                            "discount_amount": summary["discount_amount"],
                            "item_count": summary["item_count"]
                        })

                elif msg_type == "epc_lost":
                    epc_id = msg.get("epc_id")
                    if epc_id:
                        # Log lost sale analytics before removal
                        prod = cart_service.resolve_epc(epc_id)
                        if prod:
                            analytics_service.record_lost_sale(session_id=cart_id, epc_id=epc_id, sku=prod["sku"], product_name=prod["name"])
                        
                        res = cart_service.remove_epc_or_sku(session_id=cart_id, epc_id=epc_id)
                        summary = cart_service.get_summary(cart_id)
                        await manager.broadcast_to_cart(cart_id, {
                            "type": "cart_update",
                            "cart_id": cart_id,
                            "last_action": "remove",
                            "removed_item": res,
                            "items": summary["items"],
                            "cart_total": summary["cart_total"],
                            "raw_total": summary["raw_total"],
                            "discount_amount": summary["discount_amount"],
                            "item_count": summary["item_count"]
                        })

                elif msg_type == "telemetry":
                    logger.info(f"Telemetry from cart {cart_id}: battery={msg.get('battery_pct')}%, pir={msg.get('pir_active')}")

            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON on WebSocket from cart {cart_id}")

    except WebSocketDisconnect:
        manager.disconnect(cart_id, websocket)
