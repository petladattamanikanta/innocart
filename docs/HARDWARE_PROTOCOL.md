# InnoCart V2 — Hardware Bridge & Communication Protocol

This document defines the communication contract between the physical hardware (Arduino Mega 2560 + ESP32-S3) and the backend service.

---

## 1. Arduino Mega 2560 ➔ ESP32-S3 (UART @ 115200 Baud)

The Arduino Mega reads tags from the E710 reader, deduplicates them within a 2-second sliding window, and emits clean line-delimited JSON strings over UART:

```json
{"event":"NEW_TAG", "epc":"E100001", "rssi":-48, "ant":1}
{"event":"TAG_LOST", "epc":"E100001", "ant":1}
```

---

## 2. ESP32-S3 ➔ Backend WebSocket (`/ws/cart/{cart_id}`)

The ESP32-S3 maintains a persistent WSS connection to the backend and pushes hardware events:

### Inbound Events (ESP32-S3 ➔ Backend)

#### Tag Scan Event
```json
{
  "type": "epc_scan",
  "cart_id": "IC-042",
  "epc_id": "E100001",
  "ts": "2026-07-26T20:00:00Z"
}
```

#### Tag Removed / Debounced Loss Event
```json
{
  "type": "epc_lost",
  "cart_id": "IC-042",
  "epc_id": "E100001",
  "ts": "2026-07-26T20:00:05Z"
}
```

#### Telemetry Event
```json
{
  "type": "telemetry",
  "cart_id": "IC-042",
  "battery_pct": 88,
  "pir_active": true
}
```

---

## 3. Backend ➔ ESP32-S3 & Display (Fan-Out)

#### Real-Time Cart Update
```json
{
  "type": "cart_update",
  "cart_id": "IC-042",
  "items": [
    {
      "sku": "HD-BLK-OVR",
      "name": "Void Black Oversized Hoodie",
      "price": 2499.0,
      "quantity": 1,
      "line_total": 2499.0
    }
  ],
  "cart_total": 2499.0,
  "item_count": 1
}
```

#### Unlock Cart Hardware Signal
```json
{
  "type": "unlock_cart",
  "cart_id": "IC-042",
  "txn_id": "TXN_RZP_99812"
}
```
