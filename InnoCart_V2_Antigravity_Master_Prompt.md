# MASTER PROMPT — InnoCart V2 Production Build
### For: Antigravity (agentic build)
### Project: SWIPE Technologies · InnoCart V2 / InnoBasket V2
### Tagline: **"Drop. Scan. Pay. Leave."**

---

## 0. READ THIS FIRST — HOW TO USE THIS PROMPT

You are building the **production version** of an existing, fully-designed hardware +
software prototype. Reference files are attached in the project. Do not redesign the
concept — implement it. Where this prompt says "port," it means: take the working logic
from the attached prototype file, keep its behavior and contracts, and rebuild it as a
real, deployable service (real DB, real auth, real WebSockets, real payment webhook,
error handling, logging, tests).

**Attached reference files (treat as source of truth for logic/contracts):**
- `Cart_handler.py` — cart session logic, EPC→SKU resolution, scan/remove/qty/checkout API contracts
- `Styling_engine.py` — 5-stage AI scoring engine (style match, color harmony, skin synergy, aesthetic bonus, facial-hex harmony), `/api/get_style`, `/api/suggest_footwear`, `/api/classify_hex`
- `innocart_display_2.html` — the 6-screen on-cart UI (Welcome/QR → Live Shopping → AI Styling → Rush Deals → UPI Payment → Success), brand palette, layout, copy
- `Innocart · Hardware Simulator.html` (+ `1.html`) — product catalogue (`PRODUCTS[]`), EPC mapping, cart/AI interaction flow, console/log semantics
- `InnoCart_V2_Circuit_Design.docx` — full electrical schematic, pin maps, power rails, antenna config, firmware signal flow (this defines what the ESP32-S3 firmware sends/expects — your backend and WebSocket contract must match it)
- `InnoCart_Research_Document.docx` — business context, market, financial model, glossary
- `E710_Demo_User_Manual.docx` / `Serial_Protocol_Users_Guide_V2_38_en_.pdf` — UHF reader protocol reference (already abstracted away by the Arduino Mega firmware; you do not talk to the E710 directly, you talk to the ESP32-S3's JSON bridge)

---

## 1. WHAT INNOCART V2 IS (ELEVATOR PITCH)

InnoCart V2 (internally "InnoBasket V2") is an **autonomous UHF RFID checkout cart**
for Indian fast-fashion retail (Zudio, Pantaloons, Decathlon, H&M — chains that
**already RFID-tag every garment for security**, so InnoCart repurposes infrastructure
retailers have already paid for).

The customer experience:
1. Shopper drops garments into a **Faraday-shielded cavity** in the cart.
2. Four inward-facing UHF antennas fast-switch-scan the cavity; every tag's EPC is
   read, deduplicated, and resolved to a product in under a second.
3. A **7-inch on-cart touchscreen** shows a live, itemized bill in real time — no
   staff, no queue.
4. An **AI styling engine** can suggest a matching top/bottom or footwear, scored
   against the shopper's facial-hex undertone (captured once via the companion app).
5. **Rush Deals** apply time-limited, cart-value-based discounts at checkout.
6. Payment happens **on the cart itself** via a UPI QR code, confirmed over
   WebSocket — no app hand-off required to pay.
7. Lost-sale analytics track items added-then-removed before checkout, giving
   retailers rejection-reason data e-commerce competitors have but physical
   retail traditionally lacks.

This is a **B2B SaaS hardware product**: sold per-cart to retail chains, not
a consumer app.

---

## 2. SYSTEM ARCHITECTURE (WHAT YOU ARE BUILDING)

```
┌────────────────────┐     UART/JSON      ┌──────────────────┐
│  Arduino Mega 2560  │◄──────────────────►│  ESP32-S3-WROOM  │
│  (E710 RFID driver, │   EPC events,      │  (Wi-Fi bridge,  │
│   4-ant fast-switch,│   dedup, wake ctrl │   sensor fusion, │
│   300ms EN delay)   │                    │   WebSocket clt) │
└────────────────────┘                    └────────┬─────────┘
                                                     │ WSS (persistent)
                                                     ▼
                                        ┌─────────────────────────┐
                                        │   BACKEND (this build)  │
                                        │  - Cart Session Service │
                                        │  - AI Styling Service   │
                                        │  - Rush Deals Engine    │
                                        │  - Payment Gateway svc  │
                                        │  - Lost-Sale Analytics  │
                                        │  - Retailer Admin API   │
                                        │  MySQL/Postgres + Redis │
                                        └──────────┬──────────────┘
                                                    │ WSS + REST
                                                    ▼
                                   ┌─────────────────────────────────┐
                                   │  7" ON-CART DISPLAY (this build)│
                                   │  Browser/kiosk client, rendering│
                                   │  the 6 screens, live via WS     │
                                   └─────────────────────────────────┘
```

**Hardware/software boundary (do not re-implement below this line):**
The Arduino Mega + E710 stack is fixed hardware/firmware (see Circuit Design doc).
Your backend's only contract with hardware is the **JSON event stream the ESP32-S3
pushes over WebSocket** (see §3) and the **300ms EN-enable / 2-second EPC dedup
window** already implemented in firmware — assume EPCs arriving at your backend are
already deduplicated singles, not raw radio noise.

**Key pivot from the prototype:** the 7" display was originally going to be
rendered directly by the ESP32-S3 over SPI/I2C to the ST7701S+GT911 panel. For
this build, **the display is a browser-based kiosk web app** served by your
backend (assume it runs on a small companion compute unit — Pi/Android board —
wired to the same 7" panel, in Chromium kiosk mode, `800x480`, touch-enabled).
The ESP32-S3 remains the sensor/RFID bridge and talks to the backend independently
over its own WebSocket connection. If this assumption is wrong for your hardware
revision, flag it back to me before building around it.

---

## 3. HARDWARE→BACKEND CONTRACT (ESP32-S3 WebSocket events)

Design this explicitly (it doesn't fully exist in the prototype — the prototype
simulates it via HTTP POST from the browser). Build a WebSocket namespace
`/ws/cart/<cart_id>` with these inbound event types from the ESP32-S3:

```jsonc
// New tag detected (post-dedup, post-300ms-delay, from Mega→ESP32 bridge)
{ "type": "epc_scan", "cart_id": "IC-042", "epc_id": "E280110C", "ts": "..." }

// Tag no longer read for N consecutive rounds (debounced removal)
{ "type": "epc_lost", "cart_id": "IC-042", "epc_id": "E280110C", "ts": "..." }

// PIR/IR sensor + battery telemetry (low priority, batched)
{ "type": "telemetry", "cart_id": "IC-042", "battery_pct": 78, "pir_active": true }
```

Outbound (backend → ESP32-S3 and → display client, fan-out):
```jsonc
{ "type": "cart_update", "cart_id": "IC-042", "items": [...], "cart_total": 3546, "item_count": 4 }
{ "type": "payment_confirmed", "cart_id": "IC-042", "txn_id": "RZP8821049" }
{ "type": "unlock_cart", "cart_id": "IC-042" }
```

Port the **EPC→SKU resolution, session model, and scan/remove/qty logic byte-for-byte
in behavior** from `Cart_handler.py` — just move the trigger from HTTP POST (used only
by your dev/QA simulator) to the WebSocket event above, keep the REST endpoints too
(cart view, checkout summary, clear) for the display client and admin dashboard to poll.

---

## 4. BACKEND — WHAT TO BUILD

Extend `Cart_handler.py` and `Styling_engine.py` into one production service
(or two services behind an API gateway — your call, but keep the existing
route names/payloads as the contract):

### 4.1 Cart Session Service (from `Cart_handler.py`)
- Keep: `CartSession`, `CartLine`, `CartManager` logic, session TTL eviction,
  `POST /cart/scan`, `POST /cart/remove`, `POST /cart/qty`, `GET /cart/<id>`,
  `GET /cart/<id>/summary`, `DELETE /cart/<id>`, `GET /health`.
- Add: persistent session store surviving process restarts (Redis for hot
  session state + MySQL for durability — the prototype already assumes both
  `cart_sessions`/`cart_items` tables; build the migrations).
- Add: multi-cart, multi-store isolation — `cart_id` must be scoped under a
  `store_id`; no cross-store data bleed.
- Add: idempotency — duplicate `epc_scan` events (e.g. reconnect replay) must
  not double-add.

### 4.2 AI Styling Service (from `Styling_engine.py`)
- Port all 5 scoring stages exactly: Style Match (+50), Outfit Color Harmony (±30),
  Skin Tone Synergy (+0..30, legacy fallback), Aesthetic Bonus (+0..20),
  **Facial Color Harmony (+0..40, highest weight)** via `hex_to_hsl` →
  `hex_skin_zones` → `facial_color_harmony`.
- Keep routes: `POST /api/get_cart_wearable`, `POST /api/get_style`,
  `POST /api/suggest_footwear`, `POST /api/classify_hex`, `POST /api/reload_scoring`.
- Add: cache `ScoringTables` in Redis, invalidate on `/api/reload_scoring`, so
  every scoring call isn't a fresh 6-table MySQL load.
- Add: rate/size guard — cap `top_n`, validate `facial_hex` regex before hitting
  `colorsys`.

### 4.3 Rush Deals Engine (new — implied by research doc + display mockup, not
    yet built in the prototype)
- Rules-based (not ML) discount engine: threshold discounts (`₹200 off > ₹2,500`),
  category discounts (`15% off footwear`), loyalty (`2nd visit this week`),
  bundled-free-accessory rules.
- `GET /cart/<id>/deals` → eligible deals for current cart state.
- `POST /cart/<id>/deals/apply` → `{ deal_code }`.
- Must recompute live as cart contents change (a deal can become eligible or
  ineligible mid-shop).

### 4.4 Payment Service (new — the prototype only simulates this)
- Real UPI integration via a payment gateway (Razorpay is what the research doc
  already assumes for the mobile app; reuse it here for the on-cart flow).
- `POST /cart/<id>/checkout/qr` → generates a dynamic UPI QR for `cart_total`
  minus applied deals.
- Webhook receiver `POST /payments/webhook` → verifies signature, matches
  `order_id`→`cart_id`, then:
  - persists transaction,
  - emits `payment_confirmed` + `unlock_cart` over the cart's WebSocket,
  - triggers `clear_session` (existing `Cart_handler.py` logic).
- Handle timeout: if unpaid after N minutes, expire the QR and return the
  display to the Rush Deals screen.

### 4.5 Lost-Sale Analytics (new)
- Every `epc_scan` followed by `epc_lost` (or explicit `/cart/remove`) before
  checkout is a "considered then rejected" event.
- Store: `product_id`, `store_id`, `cart_id`, `time_in_cart_seconds`,
  `removed_before_checkout: true`.
- Expose an aggregation endpoint for the retailer dashboard (top-rejected SKUs,
  average dwell time before rejection, rejection rate by category).

### 4.6 Retailer/Admin API (new, minimal for v1)
- Store-scoped auth (JWT), CRUD on `product_master`, live view of active carts
  per store, lost-sale analytics dashboard data, Rush Deals rule management.

### Data layer
- MySQL schema = union of what's already implied across both prototype files:
  `product_master`, `inventory_live`, `cart_sessions`, `cart_items`,
  `pairing_rules`, `color_harmony`, `skin_tone_synergy`, `aesthetic_bonus`,
  `hex_skin_zones`, `facial_color_harmony`, plus new `stores`, `deals`,
  `deal_redemptions`, `lost_sale_events`, `transactions`.
- Write the migrations. Seed data from the `PRODUCTS[]` array in the simulator
  HTML files (21 SKUs, 3 style profiles, EPC ranges E1/E2/E3-prefixed) so the
  seeded catalogue matches what QA already expects.

---

## 5. FRONTEND — 7" ON-CART DISPLAY (WHAT TO BUILD)

Port `innocart_display_2.html` from a static mockup into a real, WebSocket-driven
app (React + Vite recommended; Tailwind matching the existing CSS variables
below). Keep the exact 6-screen flow, layout, animations, and copy already
designed — this is a **rebuild for data-binding, not a redesign**:

1. **Welcome / QR** — cart ID, "scan to begin" QR linking the companion app to
   this `cart_id` session.
2. **Live Shopping Bill** — real-time item list bound to `cart_update` WS
   events, RFID status indicator, last-scanned item, "Go with AI Styling"
   button, checkout button.
3. **AI Styling** — calls `/api/get_cart_wearable` then `/api/get_style` /
   `/api/suggest_footwear`, renders ranked suggestion cards with aisle location.
4. **Rush Deals** — live deal cards from `/cart/<id>/deals`, apply/unapply,
   countdown timer, running savings total.
5. **UPI Payment QR** — dynamic QR from `/cart/<id>/checkout/qr`, WebSocket
   listener for `payment_confirmed`.
6. **Success** — transaction summary, "tap NFC at exit," auto-return to
   Welcome screen after a timeout (triggered by `unlock_cart`).

**Brand tokens (already fixed — reuse exactly):**
```
--brand:  #1A1AFF   (Deep Electric Blue)
--cyan:   #00F5FF   (Neon Cyan)
--violet: #7C4DFF   (AI features)
--amber:  #FFB300   (Rush Deals)
--green:  #00E676   (payment success)
--bg:     #0D0D0D   (Jet Black)
Fonts: Rajdhani (headers), Space Mono (technical/mono), Exo 2 (body)
```

- Target viewport: `800×480`, touch-first, kiosk mode (no browser chrome,
  no scroll bounce, disable text selection/long-press menus).
- Must reconnect gracefully on WebSocket drop (cart Wi-Fi can hiccup near
  the Faraday-shielded cavity) and show a clear "reconnecting" state rather
  than a blank screen.
- Keep the existing hardware simulator (`Innocart · Hardware Simulator.html`)
  working against the real backend, unmodified in intent — it's your ESP32
  stand-in for QA before real hardware is wired. Point its `CFG.cart` /
  `CFG.style` at the deployed service URLs.

---

## 6. NON-FUNCTIONAL REQUIREMENTS

- **Latency**: EPC scan → display update end-to-end under 1 second (excludes
  the 300ms E710 startup delay, which happens before the EPC ever reaches you).
- **Resilience**: backend must survive an ESP32 reconnect storm (Wi-Fi drop
  near the metal-lined cavity is expected, not exceptional) without duplicating
  cart items.
- **Multi-tenancy**: everything scoped by `store_id` → `cart_id`; no data
  leakage across stores (the financial model targets 150 stores × 30 carts).
- **Security**: WSS/HTTPS everywhere, payment webhook signature verification,
  admin API behind JWT auth, no plaintext DB credentials (env vars / secrets
  manager — the current prototype hardcodes `yourpassword`, do not ship that).
- **Observability**: structured logs per the existing `logging` setup in both
  Python files; add request tracing across the cart-scan → styling → payment
  chain so a support engineer can follow one cart's session end-to-end.

---

## 7. DELIVERABLES

1. Monorepo (or two services + shared lib) with clear `backend/`, `frontend/`,
   `simulator/` (existing HTML files, wired to real endpoints), `migrations/`.
2. `docker-compose.yml` for local dev: backend, MySQL, Redis, frontend dev
   server.
3. DB migrations + seed script (product catalogue from the simulator's
   `PRODUCTS[]`).
4. `.env.example` covering DB, Redis, Razorpay keys, JWT secret.
5. README: architecture diagram, how to run locally, how the ESP32 WebSocket
   contract works, how to point real hardware at it later.
6. Basic test coverage: cart scan/remove/qty flow, styling engine scoring
   (at least the facial-hex stage since it's the highest-weighted and most
   novel), payment webhook signature verification, deal eligibility rules.

---

## 8. OPEN DECISIONS TO CONFIRM BEFORE/DURING BUILD

- Confirm the kiosk-display hardware assumption in §2 (Pi/Android board vs.
  ESP32 driving a browser directly — the latter is unusual and may not be
  feasible on-chip).
- Confirm backend language/framework preference if you have one beyond
  "extend the existing Python/Flask files" (FastAPI + native WebSockets is a
  reasonable modernization if you're open to migrating off Flask).
- Confirm MySQL vs. Postgres for production (prototype assumes MySQL).
- Confirm Razorpay vs. another PSP for the on-cart UPI flow.
