# InnoCart V2 / InnoBasket V2 — Production Build

> **"Drop. Scan. Pay. Leave."** — Autonomous UHF RFID Checkout Cart for Indian Fast-Fashion Retail.

---

## 1. System Architecture Overview

```
┌─────────────────────────┐         UART / JSON       ┌────────────────────────┐
│  Arduino Mega 2560      │ ────────────────────────► │  ESP32-S3-WROOM        │
│  (E710 RFID driver,     │   EPC events, dedup,      │  (Wi-Fi bridge,        │
│   4-ant fast-switch)    │   wake control            │   HTTP / WS client)    │
└─────────────────────────┘                           └───────────┬────────────┘
                                                                  │ WSS / REST
                                                                  ▼
                                                   ┌───────────────────────────────┐
                                                   │  INNOCART BACKEND             │
                                                   │  (FastAPI + WebSockets)       │
                                                   │  - Cart Session Service       │
                                                   │  - AI Styling Engine (5-stage) │
                                                   │  - Rush Deals Engine          │
                                                   │  - Payment & Webhook Svc      │
                                                   │  - Lost-Sale Analytics Svc    │
                                                   │  - Retailer Admin REST API    │
                                                   │  - MySQL + Redis Session Store│
                                                   └──────────────┬────────────────┘
                                                                  │ WSS + REST
                                                                  ▼
                                                   ┌───────────────────────────────┐
                                                   │  7" ON-CART DISPLAY WEB APP   │
                                                   │  (React + Vite Kiosk App)     │
                                                   │  800x480, 6-Screen Flow       │
                                                   └───────────────────────────────┘
```

---

## 2. Key Features Implemented

1. **Cart Session Service**: Real-time EPC tag resolution, quantity increments, duplicate scan rejection, TTL eviction, and dual persistence (Redis hot session + MySQL durability).
2. **5-Stage AI Styling Engine**:
   - Stage 1: Anatomy filter pairing rules (`Topwear` ↔ `Bottomwear` ↔ `Footwear`)
   - Stage 2: Outfit Color Harmony (±30 pts)
   - Stage 3: Skin Tone Synergy (0 to +30 pts)
   - Stage 4: Aesthetic Combo Bonus (0 to +20 pts)
   - Stage 5: **Facial Color Harmony (+0 to +40 pts - HIGHEST weight)** via CSS hex → HSL → range scan against `hex_skin_zones` → `facial_color_harmony`.
3. **Rush Deals Engine**: Rules-based dynamic discount calculation (e.g. ₹200 off > ₹2,500, 15% off footwear, VIP loyalty offers).
4. **Payment Gateway & Mock Simulator**: Razorpay UPI QR generation, signature-verified webhook receiver (`/payments/webhook`), and instant Mock Payment Simulator (`/payments/mock_pay`).
5. **Lost-Sale Analytics**: Logs items added then removed prior to checkout to provide rejection data to retailers.
6. **7" On-Cart Display (React + Vite)**: 6-screen kiosk flow (`800x480` viewport, touch-first, brand tokens: `#1A1AFF`, `#00F5FF`, `#7C4DFF`, `#FFB300`, `#00E676`).
7. **WebSocket Auto-Sync**: Persistent connection over `/ws/cart/{cart_id}` with auto-reconnect handling.

---

## 3. Quick Start (Local Setup)

### Option A: Docker Compose (Recommended)
```bash
docker-compose up --build
```
- Backend: `http://localhost:8000` (Docs: `http://localhost:8000/docs`)
- Frontend Touchscreen Kiosk: `http://localhost:3000`
- MySQL: `localhost:3306` (User: `root`, Password: `root`, DB: `smart_cart`)
- Redis: `localhost:6379`

### Option B: Manual Local Setup

1. **Import Database Schema & Seed Data**:
```bash
mysql -u root -p < migrations/schema.sql
mysql -u root -p < migrations/seed.sql
```

2. **Start Backend**:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

3. **Start Frontend Kiosk App**:
```bash
cd frontend
npm install
npm run dev
```

---

## 4. Hardware Bridge (ESP32-S3 Protocol)

The ESP32-S3 pushes WebSocket events to `/ws/cart/{cart_id}` or HTTP REST endpoints:

### Inbound Events (ESP32 -> Backend)
```jsonc
// EPC Tag Scan
{ "type": "epc_scan", "cart_id": "IC-042", "epc_id": "E100001" }

// Tag Removed
{ "type": "epc_lost", "cart_id": "IC-042", "epc_id": "E100001" }

// Telemetry
{ "type": "telemetry", "cart_id": "IC-042", "battery_pct": 85, "pir_active": true }
```

### Outbound Events (Backend -> Display & ESP32)
```jsonc
// Real-time Cart Update
{ "type": "cart_update", "cart_id": "IC-042", "items": [...], "cart_total": 2499.0, "item_count": 1 }

// Payment Confirmed & Unlock Cart
{ "type": "payment_confirmed", "cart_id": "IC-042", "txn_id": "TXN_MOCK_123" }
{ "type": "unlock_cart", "cart_id": "IC-042" }
```

---

## 5. Automated Tests

Run unit tests via `pytest`:
```bash
cd backend
pytest -v
```
