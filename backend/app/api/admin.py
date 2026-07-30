from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.security import verify_password, create_access_token, decode_access_token
from app.core.db import db
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/admin", tags=["Retailer Admin API"])

class LoginRequest(BaseModel):
    username: str
    password: str

class ProductCreateRequest(BaseModel):
    sku: str
    name: str
    price: float
    garment_category: str
    garment_type: str
    style_profile: str
    color_family: str
    image_url: str
    aisle_location: Optional[str] = "Aisle A-01"

@router.post("/login")
async def login(req: LoginRequest):
    rows = db.query("SELECT username, password_hash, role, store_id FROM admin_users WHERE username = %s", (req.username,))
    if not rows:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user = rows[0]
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user["username"], "role": user["role"], "store_id": user["store_id"]})
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "role": user["role"],
            "store_id": user["store_id"]
        }
    }

@router.get("/analytics/lost-sales")
async def get_lost_sales(store_id: str = "STORE-001"):
    return analytics_service.get_lost_sales_summary(store_id)

@router.get("/stores")
async def get_stores():
    return db.query("SELECT store_id, name, location, city FROM stores")

@router.get("/carts")
async def get_active_carts(store_id: str = "STORE-001"):
    sql = """
        SELECT cs.session_id, cs.store_id, cs.created_at, cs.updated_at, cs.applied_deal_code, cs.discount_amount,
               COUNT(ci.id) as item_count, SUM(ci.price * ci.quantity) as raw_total
        FROM cart_sessions cs
        LEFT JOIN cart_items ci ON cs.session_id = ci.session_id
        WHERE cs.store_id = %s AND cs.is_active = 1
        GROUP BY cs.session_id
    """
    return db.query(sql, (store_id,))

@router.get("/products")
async def get_products():
    return db.query("SELECT sku, name, price, garment_category, garment_type, style_profile, color_family, image_url, aisle_location FROM product_master WHERE is_active = 1")

@router.post("/products")
async def create_product(req: ProductCreateRequest):
    db.execute(
        "INSERT INTO product_master (sku, name, price, garment_category, garment_type, style_profile, color_family, image_url, aisle_location) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE name=VALUES(name), price=VALUES(price), aisle_location=VALUES(aisle_location)",
        (req.sku, req.name, req.price, req.garment_category, req.garment_type, req.style_profile, req.color_family, req.image_url, req.aisle_location)
    )
    return {"status": "success", "message": f"Product '{req.sku}' created/updated"}
