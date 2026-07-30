# InnoCart V2 — REST API & WebSocket Reference

Base URL: `http://localhost:8000` (Production: `https://innocart-backend.onrender.com`)

---

## 1. Cart Operations

### `POST /cart/scan`
Scans an RFID EPC tag and adds/increments it in the active session.

**Request**:
```json
{
  "session_id": "IC-042",
  "epc_id": "E100001",
  "store_id": "STORE-001"
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "duplicate_scan": false,
  "sku": "HD-BLK-OVR",
  "name": "Void Black Oversized Hoodie",
  "price": 2499.0,
  "quantity": 1,
  "cart_total": 2499.0,
  "item_count": 1
}
```

### `POST /cart/remove`
Removes an item by EPC tag ID or SKU.

**Request**:
```json
{
  "session_id": "IC-042",
  "epc_id": "E100001"
}
```

### `GET /cart/{session_id}`
Returns current itemized cart summary.

### `DELETE /cart/{session_id}`
Clears and resets the session.

---

## 2. AI Styling Engine

### `POST /api/get_style`
Returns AI outfit recommendations scored across all 5 stages.

**Request**:
```json
{
  "epc_id": "E100001",
  "user_style": "Streetwear",
  "facial_hex": "#C8A882"
}
```

### `POST /api/suggest_footwear`
Returns footwear recommendations.

### `POST /api/classify_hex`
Classifies a CSS hex skin tone into undertone label.

---

## 3. Rush Deals Engine

### `GET /cart/{session_id}/deals`
Lists eligible deals and discount amounts for the cart.

### `POST /cart/{session_id}/deals/apply`
Applies a deal code (`{"deal_code": "RUSH200"}`).

---

## 4. Payments

### `POST /cart/{session_id}/checkout/qr`
Generates a dynamic UPI QR code for the cart total.

### `POST /payments/webhook`
Razorpay webhook receiver verifying `X-Razorpay-Signature`.

### `POST /payments/mock_pay`
Simulates instant UPI payment for testing (`{"session_id": "IC-042"}`).
