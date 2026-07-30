-- =============================================================================
-- INNOCART V2 — Production MySQL 8.0 Master Database Schema
-- File    : migrations/schema.sql
-- Engine  : MySQL 8.0+ (InnoDB)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS smart_cart
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE smart_cart;

SET FOREIGN_KEY_CHECKS = 0;

-- -----------------------------------------------------------------------------
-- 1. STORES & RETAILER TENANCY
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stores (
    store_id    VARCHAR(40)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    location    VARCHAR(150) NOT NULL,
    city        VARCHAR(50)  NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (store_id)
) ENGINE=InnoDB COMMENT='Retail store locations';

-- -----------------------------------------------------------------------------
-- 2. LOOKUP / TAXONOMY TABLES
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS style_profiles (
    style_id    TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    style_name  VARCHAR(40)      NOT NULL,
    description VARCHAR(160)     NULL,
    created_at  TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (style_id),
    UNIQUE KEY uq_style_name (style_name)
) ENGINE=InnoDB COMMENT='Valid style profiles';

CREATE TABLE IF NOT EXISTS color_families (
    color_id    TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    color_name  VARCHAR(30)      NOT NULL,
    hex_code    CHAR(7)          NULL,
    created_at  TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (color_id),
    UNIQUE KEY uq_color_name (color_name)
) ENGINE=InnoDB COMMENT='Canonical color families';

CREATE TABLE IF NOT EXISTS garment_types (
    type_id     SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    type_name   VARCHAR(50)       NOT NULL,
    category    ENUM('Topwear','Bottomwear','Footwear','Accessory') NOT NULL,
    created_at  TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (type_id),
    UNIQUE KEY uq_garment_type (type_name)
) ENGINE=InnoDB COMMENT='Garment types and categories';

-- -----------------------------------------------------------------------------
-- 3. PRODUCT CATALOGUE & LIVE INVENTORY
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_master (
    sku              VARCHAR(20)   NOT NULL,
    name             VARCHAR(120)  NOT NULL,
    price            DECIMAL(8,2)  NOT NULL,
    garment_category ENUM('Topwear','Bottomwear','Footwear','Accessory') NOT NULL,
    garment_type     VARCHAR(50)   NOT NULL,
    style_profile    VARCHAR(40)   NOT NULL,
    color_family     VARCHAR(30)   NOT NULL,
    image_url        VARCHAR(255)  NOT NULL,
    aisle_location   VARCHAR(50)   NOT NULL DEFAULT 'Aisle A-01',
    is_active        TINYINT(1)    NOT NULL DEFAULT 1,
    created_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (sku),
    FOREIGN KEY (garment_type) REFERENCES garment_types (type_name) ON UPDATE CASCADE,
    FOREIGN KEY (style_profile) REFERENCES style_profiles (style_name) ON UPDATE CASCADE,
    FOREIGN KEY (color_family) REFERENCES color_families (color_name) ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Master product catalogue';

CREATE TABLE IF NOT EXISTS inventory_live (
    epc_id       VARCHAR(40)  NOT NULL,
    sku          VARCHAR(20)  NOT NULL,
    store_id     VARCHAR(40)  NOT NULL DEFAULT 'STORE-001',
    is_active    TINYINT(1)   NOT NULL DEFAULT 1,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (epc_id),
    FOREIGN KEY (sku) REFERENCES product_master (sku) ON UPDATE CASCADE,
    FOREIGN KEY (store_id) REFERENCES stores (store_id) ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Live UHF RFID tag to SKU mapping';

-- -----------------------------------------------------------------------------
-- 4. SCORING TABLES (5-Stage AI Styling Engine)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pairing_rules (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cart_type      VARCHAR(50) NOT NULL,
    candidate_type VARCHAR(50) NOT NULL,
    INDEX idx_pr_cart (cart_type)
) ENGINE=InnoDB COMMENT='Stage 1: Anatomy filter pairing rules';

CREATE TABLE IF NOT EXISTS color_harmony (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_color  VARCHAR(30) NOT NULL,
    target_color  VARCHAR(30) NOT NULL,
    harmony_score INT         NOT NULL,
    UNIQUE KEY uq_ch_pair (source_color, target_color)
) ENGINE=InnoDB COMMENT='Stage 2: Color harmony scores (-30 to +30)';

CREATE TABLE IF NOT EXISTS skin_tone_synergy (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    skin_tone     VARCHAR(30) NOT NULL,
    color_family  VARCHAR(30) NOT NULL,
    synergy_score INT         NOT NULL,
    UNIQUE KEY uq_sts_pair (skin_tone, color_family)
) ENGINE=InnoDB COMMENT='Stage 3: Legacy skin tone synergy (0 to 30)';

CREATE TABLE IF NOT EXISTS aesthetic_bonus (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cart_color      VARCHAR(30) NOT NULL,
    candidate_color VARCHAR(30) NOT NULL,
    bonus_score     INT         NOT NULL,
    UNIQUE KEY uq_ab_pair (cart_color, candidate_color)
) ENGINE=InnoDB COMMENT='Stage 4: Aesthetic combo bonuses (0 to 20)';

CREATE TABLE IF NOT EXISTS hex_skin_zones (
    zone_id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    undertone_label VARCHAR(40) NOT NULL,
    lum_min         INT NOT NULL,
    lum_max         INT NOT NULL,
    hue_min         INT NOT NULL,
    hue_max         INT NOT NULL,
    sat_min         INT NOT NULL,
    sat_max         INT NOT NULL,
    priority        INT NOT NULL DEFAULT 1,
    INDEX idx_hsz_priority (priority)
) ENGINE=InnoDB COMMENT='Stage 5a: HSL ranges for facial hex classification';

CREATE TABLE IF NOT EXISTS facial_color_harmony (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    undertone_label VARCHAR(40) NOT NULL,
    color_family    VARCHAR(30) NOT NULL,
    harmony_score   INT         NOT NULL,
    UNIQUE KEY uq_fch_pair (undertone_label, color_family)
) ENGINE=InnoDB COMMENT='Stage 5b: Facial color harmony scores (0 to 40)';

-- -----------------------------------------------------------------------------
-- 5. CART SESSIONS & ITEMS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cart_sessions (
    session_id      VARCHAR(40) NOT NULL,
    store_id        VARCHAR(40) NOT NULL DEFAULT 'STORE-001',
    created_at      DATETIME    NOT NULL,
    updated_at      DATETIME    NOT NULL,
    is_active       TINYINT(1)  NOT NULL DEFAULT 1,
    applied_deal_code VARCHAR(40) NULL,
    discount_amount DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    PRIMARY KEY (session_id),
    FOREIGN KEY (store_id) REFERENCES stores (store_id) ON UPDATE CASCADE,
    INDEX idx_cs_active (is_active)
) ENGINE=InnoDB COMMENT='Active shopping cart trips';

CREATE TABLE IF NOT EXISTS cart_items (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    session_id   VARCHAR(40)  NOT NULL,
    sku          VARCHAR(20)  NOT NULL,
    name         VARCHAR(120) NOT NULL,
    price        DECIMAL(8,2) NOT NULL,
    image_url    VARCHAR(255) NOT NULL,
    quantity     TINYINT UNSIGNED NOT NULL DEFAULT 1,
    added_at     DATETIME     NOT NULL,
    updated_at   DATETIME     NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_session_sku (session_id, sku),
    FOREIGN KEY (session_id) REFERENCES cart_sessions (session_id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Line items per cart session';

-- -----------------------------------------------------------------------------
-- 6. RUSH DEALS & DISCOUNT RULES
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS deals (
    deal_code        VARCHAR(40)  NOT NULL,
    title            VARCHAR(100) NOT NULL,
    description      VARCHAR(255) NOT NULL,
    discount_type    ENUM('PERCENTAGE', 'FIXED') NOT NULL,
    discount_value   DECIMAL(8,2) NOT NULL,
    min_cart_value   DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    category_restriction VARCHAR(50) NULL,
    badge_text       VARCHAR(30)  NOT NULL DEFAULT 'RUSH DEAL',
    is_active        TINYINT(1)   NOT NULL DEFAULT 1,
    PRIMARY KEY (deal_code)
) ENGINE=InnoDB COMMENT='Rush deals and discount rules';

-- -----------------------------------------------------------------------------
-- 7. LOST-SALE ANALYTICS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lost_sale_events (
    id                   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id           VARCHAR(40)  NOT NULL,
    store_id             VARCHAR(40)  NOT NULL DEFAULT 'STORE-001',
    sku                  VARCHAR(20)  NOT NULL,
    product_name         VARCHAR(120) NOT NULL,
    epc_id               VARCHAR(40)  NOT NULL,
    time_in_cart_seconds INT          NOT NULL DEFAULT 0,
    removed_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku) REFERENCES product_master (sku) ON UPDATE CASCADE,
    INDEX idx_ls_store (store_id),
    INDEX idx_ls_sku (sku)
) ENGINE=InnoDB COMMENT='Analytics for items added and removed before checkout';

-- -----------------------------------------------------------------------------
-- 8. TRANSACTIONS & PAYMENT LOGS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    txn_id           VARCHAR(64)  NOT NULL,
    session_id       VARCHAR(40)  NOT NULL,
    store_id         VARCHAR(40)  NOT NULL DEFAULT 'STORE-001',
    amount           DECIMAL(8,2) NOT NULL,
    payment_method   VARCHAR(30)  NOT NULL DEFAULT 'UPI',
    payment_gateway  VARCHAR(30)  NOT NULL DEFAULT 'Razorpay',
    status           ENUM('PENDING', 'SUCCESS', 'FAILED') NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at     TIMESTAMP    NULL,
    PRIMARY KEY (txn_id),
    INDEX idx_txn_session (session_id)
) ENGINE=InnoDB COMMENT='Completed customer payment transactions';

-- -----------------------------------------------------------------------------
-- 9. ADMIN USERS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'STORE_MANAGER',
    store_id      VARCHAR(40)  NOT NULL DEFAULT 'STORE-001',
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='Retailer admin users';

-- -----------------------------------------------------------------------------
-- 10. APP USERS (Mobile Companion Personalization Profile)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id            VARCHAR(40)  NOT NULL,
    name               VARCHAR(100) NOT NULL,
    email              VARCHAR(100) NOT NULL,
    password_hash      VARCHAR(255) NOT NULL,
    facial_hex         VARCHAR(7)   NOT NULL DEFAULT '#D4A373',
    undertone_label    VARCHAR(40)  NOT NULL DEFAULT 'Warm-Golden',
    skin_texture       VARCHAR(50)  NOT NULL DEFAULT 'Smooth & Uniform',
    skin_texture_score FLOAT        NOT NULL DEFAULT 0.85,
    created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at      TIMESTAMP    NULL DEFAULT NULL,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_user_email (email)
) ENGINE=InnoDB COMMENT='Registered mobile companion users';

SET FOREIGN_KEY_CHECKS = 1;
