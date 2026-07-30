# InnoCart V2 — System Architecture & Design Specification

## Overview

InnoCart V2 is an autonomous UHF RFID checkout cart system designed for Indian fast-fashion retail chains (Zudio, Pantaloons, Decathlon, H&M).

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

## Component Boundaries

### 1. Hardware Subsystem (Arduino Mega + ESP32-S3)
- **Arduino Mega 2560**: Controls the MagicRF E710 UHF RFID module and 4-way antenna fast-switch matrix. Performs raw radio reads and 300ms startup delay timing.
- **ESP32-S3-WROOM**: Receives deduplicated EPC tag events over UART JSON from Arduino Mega, acts as the Wi-Fi bridge, and streams JSON events to the backend over WebSocket (`/ws/cart/{cart_id}`).

### 2. Backend Subsystem (FastAPI Services)
- **Cart Session Service**: Manages session state, EPC-to-SKU product resolution, quantity increments, duplicate scan suppression, and TTL eviction.
- **5-Stage AI Styling Engine**: Evaluates garment pairings against customer style preference and facial undertone (`#RRGGBB` → HSL → range scan).
- **Rush Deals Engine**: Applies time-limited, cart-value-based discounts dynamically.
- **Payment & Webhook Service**: Generates dynamic UPI QR codes and handles signature-verified payment webhooks.
- **Lost-Sale Analytics**: Logs considered-then-rejected items (EPC scanned then lost before checkout).

### 3. Frontend Subsystem (7" On-Cart Touchscreen Kiosk)
- React + Vite application running in `800x480` kiosk mode.
- Connects to backend over WebSockets with automatic reconnection logic.
- Renders the 6-screen customer journey (Welcome, Live Bill, AI Styling, Rush Deals, Payment, Success).
