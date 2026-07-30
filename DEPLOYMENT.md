# InnoCart V2 — Master Production Deployment Guide

This guide gives the **single, exact step-by-step procedure** to deploy the complete InnoCart V2 system to production using **Supabase** (or Cloud MySQL), **Render**, and **Vercel**. Follow these steps in order.

---

## Production Stack Architecture

- **Frontend**: Vercel (`https://innocart-v2.vercel.app`)
- **Backend**: Render Docker Service (`https://innocart-backend.onrender.com`)
- **Database**: Supabase PostgreSQL / Cloud MySQL 8.0
- **Hardware Bridge**: ESP32-S3 WSS Client

---

## STEP 1: Provision & Seed the Cloud Database (Supabase)

### Option A: Using Supabase (Hosted PostgreSQL — Recommended)

1. Log in to [Supabase.com](https://supabase.com) and create a free project named `innocart-db`.
2. Save your database connection credentials from **Project Settings** → **Database**:
   - Host: `db.xxxxxx.supabase.co`
   - Port: `5432` (or `6543` for connection pooling)
   - User: `postgres`
   - Password: `YOUR_SUPABASE_PASSWORD`
   - Database: `postgres`

3. In your Supabase Dashboard, open the **SQL Editor**:
   - Copy and execute the contents of [migrations/supabase_schema.sql](file:///d:/project_innocart/migrations/supabase_schema.sql) to create all tables.
   - Copy and execute the contents of [migrations/supabase_seed.sql](file:///d:/project_innocart/migrations/supabase_seed.sql) to populate initial product catalog and test RFID tags.

---

### Option B: Using Managed Cloud MySQL (Aiven / Railway / PlanetScale)

If you prefer Cloud MySQL:
1. Provision a MySQL 8.0 instance on Aiven, Railway, or GCP Cloud SQL.
2. Run database setup scripts:
   ```bash
   mysql -h YOUR_CLOUD_DB_HOST -P 3306 -u YOUR_DB_USER -p smart_cart < migrations/schema.sql
   mysql -h YOUR_CLOUD_DB_HOST -P 3306 -u YOUR_DB_USER -p smart_cart < migrations/seed.sql
   ```

---

## STEP 2: Deploy the Backend Service to Render

1. Push this repository to **GitHub** (or GitLab).
2. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** → **Web Service**.
3. Select **Build and deploy from a Git repository** and pick your `project_innocart` repository.
4. Configure Web Service settings:
   - **Name**: `innocart-backend`
   - **Region**: Singapore (or nearest to store)
   - **Environment**: `Docker`
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `Dockerfile`

5. Scroll to **Environment Variables** and add your Supabase / Cloud DB details:
   | Key | Value |
   | :--- | :--- |
   | `MYSQL_HOST` | `db.xxxxxx.supabase.co` (or your Cloud DB host) |
   | `MYSQL_PORT` | `5432` (Supabase) or `3306` (MySQL) |
   | `MYSQL_USER` | `postgres` (or your DB user) |
   | `MYSQL_PASSWORD` | `YOUR_SUPABASE_PASSWORD` |
   | `MYSQL_DB` | `postgres` (or `smart_cart`) |
   | `REDIS_HOST` | `127.0.0.1` |
   | `JWT_SECRET` | `innocart_prod_jwt_secret_2026` |
   | `USE_MOCK_PAYMENTS` | `true` |

6. Click **Create Web Service**. Render will build the Docker container and deploy it.
7. Save your live backend URL (e.g. `https://innocart-backend.onrender.com`).

---

## STEP 3: Deploy the Frontend to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/new).
2. Import your `project_innocart` GitHub repository.
3. Configure project settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

4. Expand **Environment Variables** and add:
   - `VITE_BACKEND_URL`: `https://innocart-backend.onrender.com`
   - `VITE_WS_URL`: `wss://innocart-backend.onrender.com`

5. Click **Deploy**. Vercel will build and launch your 7" Touchscreen Kiosk App (e.g. `https://innocart-v2.vercel.app`).

---

## STEP 4: Deploy the Mobile Companion App to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/new) → Click **Add New +** → **Project**.
2. Select your `project_innocart` repository.
3. Configure project settings:
   - **Project Name**: `innocart-mobile`
   - **Framework Preset**: `Vite`
   - **Root Directory**: `mobile`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

4. Expand **Environment Variables** and add:
   - `VITE_BACKEND_URL`: `https://innocart-backend.onrender.com`

5. Click **Deploy**. Vercel will launch your live Mobile Companion Web App (e.g. `https://innocart-mobile.vercel.app`).
   - Open this URL on your Android device in Chrome or Edge.
   - Tap **"Add to Home Screen"** to install it as a standalone Android app icon!

---

## STEP 5: Configure ESP32-S3 Hardware Firmware

Update the ESP32-S3 C++ firmware header to connect to your live Render backend over Secure WebSocket (WSS):

```cpp
// ESP32-S3 Network & WebSocket Settings
const char* WIFI_SSID       = "Store_WiFi_5G";
const char* WIFI_PASSWORD   = "StorePassword123";

const char* WS_SERVER_HOST  = "innocart-backend.onrender.com";
const int   WS_SERVER_PORT  = 443;
const char* WS_SERVER_PATH  = "/ws/cart/IC-042";
```

---

## STEP 5: Verify End-to-End System Health

1. **Verify Backend Health**:
   Open `https://innocart-backend.onrender.com/health` in your browser. Expected output:
   ```json
   { "status": "healthy", "service": "InnoCart V2 Backend", "version": "2.0.0" }
   ```

2. **Verify OpenAPI Swagger Docs**:
   Open `https://innocart-backend.onrender.com/docs`.

3. **Verify Touchscreen Kiosk Display**:
   Open `https://innocart-v2.vercel.app` on the 7" touchscreen panel or kiosk browser.
   - Confirm status indicator displays **Online** with green Wi-Fi badge.
   - Scan an RFID tag (`E100001` or `E200001`) via the ESP32 hardware or simulator.
   - Confirm live shopping bill updates in under 1 second.
