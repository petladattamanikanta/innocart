-- =============================================================================
-- INNOCART V2 — Supabase (PostgreSQL) Master Database Schema
-- File    : migrations/supabase_schema.sql
-- Engine  : PostgreSQL 14+ (Supabase)
-- =============================================================================

-- 1. STORES & RETAILER TENANCY
CREATE TABLE IF NOT EXISTS stores (
    store_id    VARCHAR(40)  PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    location    VARCHAR(150) NOT NULL,
    city        VARCHAR(50)  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. LOOKUP / TAXONOMY TABLES
CREATE TABLE IF NOT EXISTS style_profiles (
    style_id    SERIAL PRIMARY KEY,
    style_name  VARCHAR(40) UNIQUE NOT NULL,
    description VARCHAR(160),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS color_families (
    color_id    SERIAL PRIMARY KEY,
    color_name  VARCHAR(30) UNIQUE NOT NULL,
    hex_code    CHAR(7),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS garment_types (
    type_id     SERIAL PRIMARY KEY,
    type_name   VARCHAR(50) UNIQUE NOT NULL,
    category    VARCHAR(30) CHECK (category IN ('Topwear','Bottomwear','Footwear','Accessory')) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. PRODUCT CATALOGUE & LIVE INVENTORY
CREATE TABLE IF NOT EXISTS product_master (
    sku              VARCHAR(20) PRIMARY KEY,
    name             VARCHAR(120) NOT NULL,
    price            NUMERIC(8,2) NOT NULL,
    garment_category VARCHAR(30) CHECK (garment_category IN ('Topwear','Bottomwear','Footwear','Accessory')) NOT NULL,
    garment_type     VARCHAR(50) REFERENCES garment_types(type_name) ON UPDATE CASCADE,
    style_profile    VARCHAR(40) REFERENCES style_profiles(style_name) ON UPDATE CASCADE,
    color_family     VARCHAR(30) REFERENCES color_families(color_name) ON UPDATE CASCADE,
    image_url        VARCHAR(255) NOT NULL,
    aisle_location   VARCHAR(50) DEFAULT 'Aisle A-01',
    is_active        BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_live (
    epc_id       VARCHAR(40) PRIMARY KEY,
    sku          VARCHAR(20) REFERENCES product_master(sku) ON UPDATE CASCADE,
    store_id     VARCHAR(40) DEFAULT 'STORE-001' REFERENCES stores(store_id) ON UPDATE CASCADE,
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. SCORING TABLES (5-Stage AI Styling Engine)
CREATE TABLE IF NOT EXISTS pairing_rules (
    id             SERIAL PRIMARY KEY,
    cart_type      VARCHAR(50) NOT NULL,
    candidate_type VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS color_harmony (
    id            SERIAL PRIMARY KEY,
    source_color  VARCHAR(30) NOT NULL,
    target_color  VARCHAR(30) NOT NULL,
    harmony_score INT NOT NULL,
    UNIQUE (source_color, target_color)
);

CREATE TABLE IF NOT EXISTS skin_tone_synergy (
    id            SERIAL PRIMARY KEY,
    skin_tone     VARCHAR(30) NOT NULL,
    color_family  VARCHAR(30) NOT NULL,
    synergy_score INT NOT NULL,
    UNIQUE (skin_tone, color_family)
);

CREATE TABLE IF NOT EXISTS aesthetic_bonus (
    id              SERIAL PRIMARY KEY,
    cart_color      VARCHAR(30) NOT NULL,
    candidate_color VARCHAR(30) NOT NULL,
    bonus_score     INT NOT NULL,
    UNIQUE (cart_color, candidate_color)
);

CREATE TABLE IF NOT EXISTS hex_skin_zones (
    zone_id         SERIAL PRIMARY KEY,
    undertone_label VARCHAR(40) NOT NULL,
    lum_min         INT NOT NULL,
    lum_max         INT NOT NULL,
    hue_min         INT NOT NULL,
    hue_max         INT NOT NULL,
    sat_min         INT NOT NULL,
    sat_max         INT NOT NULL,
    priority        INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS facial_color_harmony (
    id              SERIAL PRIMARY KEY,
    undertone_label VARCHAR(40) NOT NULL,
    color_family    VARCHAR(30) NOT NULL,
    harmony_score   INT NOT NULL,
    UNIQUE (undertone_label, color_family)
);

-- 5. CART SESSIONS & ITEMS
CREATE TABLE IF NOT EXISTS cart_sessions (
    session_id        VARCHAR(40) PRIMARY KEY,
    store_id          VARCHAR(40) DEFAULT 'STORE-001' REFERENCES stores(store_id) ON UPDATE CASCADE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active         BOOLEAN DEFAULT TRUE,
    applied_deal_code VARCHAR(40),
    discount_amount   NUMERIC(8,2) DEFAULT 0.00
);

CREATE TABLE IF NOT EXISTS cart_items (
    id           BIGSERIAL PRIMARY KEY,
    session_id   VARCHAR(40) REFERENCES cart_sessions(session_id) ON DELETE CASCADE,
    sku          VARCHAR(20) NOT NULL,
    name         VARCHAR(120) NOT NULL,
    price        NUMERIC(8,2) NOT NULL,
    image_url    VARCHAR(255) NOT NULL,
    quantity     SMALLINT DEFAULT 1,
    added_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, sku)
);

-- 6. RUSH DEALS & DISCOUNT RULES
CREATE TABLE IF NOT EXISTS deals (
    deal_code            VARCHAR(40) PRIMARY KEY,
    title                VARCHAR(100) NOT NULL,
    description          VARCHAR(255) NOT NULL,
    discount_type        VARCHAR(20) CHECK (discount_type IN ('PERCENTAGE', 'FIXED')) NOT NULL,
    discount_value       NUMERIC(8,2) NOT NULL,
    min_cart_value       NUMERIC(8,2) DEFAULT 0.00,
    category_restriction VARCHAR(50),
    badge_text           VARCHAR(30) DEFAULT 'RUSH DEAL',
    is_active            BOOLEAN DEFAULT TRUE
);

-- 7. LOST-SALE ANALYTICS
CREATE TABLE IF NOT EXISTS lost_sale_events (
    id                   BIGSERIAL PRIMARY KEY,
    session_id           VARCHAR(40) NOT NULL,
    store_id             VARCHAR(40) DEFAULT 'STORE-001',
    sku                  VARCHAR(20) REFERENCES product_master(sku) ON UPDATE CASCADE,
    product_name         VARCHAR(120) NOT NULL,
    epc_id               VARCHAR(40) NOT NULL,
    time_in_cart_seconds INT DEFAULT 0,
    removed_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. TRANSACTIONS & PAYMENT LOGS
CREATE TABLE IF NOT EXISTS transactions (
    txn_id           VARCHAR(64) PRIMARY KEY,
    session_id       VARCHAR(40) NOT NULL,
    store_id         VARCHAR(40) DEFAULT 'STORE-001',
    amount           NUMERIC(8,2) NOT NULL,
    payment_method   VARCHAR(30) DEFAULT 'UPI',
    payment_gateway  VARCHAR(30) DEFAULT 'Razorpay',
    status           VARCHAR(20) CHECK (status IN ('PENDING', 'SUCCESS', 'FAILED')) DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at     TIMESTAMPTZ
);

-- 9. ADMIN USERS
CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) DEFAULT 'STORE_MANAGER',
    store_id      VARCHAR(40) DEFAULT 'STORE-001',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. APP USERS (Mobile Companion Personalization Profile)
CREATE TABLE IF NOT EXISTS users (
    user_id            VARCHAR(40) PRIMARY KEY,
    name               VARCHAR(100) NOT NULL,
    email              VARCHAR(100) UNIQUE NOT NULL,
    password_hash      VARCHAR(255) NOT NULL,
    facial_hex         VARCHAR(7) NOT NULL DEFAULT '#D4A373',
    undertone_label    VARCHAR(40) NOT NULL DEFAULT 'Warm-Golden',
    skin_texture       VARCHAR(50) NOT NULL DEFAULT 'Smooth & Uniform',
    skin_texture_score FLOAT NOT NULL DEFAULT 0.85,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at      TIMESTAMPTZ DEFAULT NULL
);

