-- =============================================================================
--  SMART RETAIL CART — Master Database
--  File    : smart_cart_db.sql
--  Engine  : MySQL 8.0+ (InnoDB)
--  Purpose : Defines and seeds all core tables used by the Flask API.
--            Replace the in-memory mock dicts in smart_cart_api.py by
--            pointing SQLAlchemy / mysql-connector to this schema.
--
--  TABLE OVERVIEW
--  ┌──────────────────┬──────────────────────────────────────────────────┐
--  │ Table            │ Role                                             │
--  ├──────────────────┼──────────────────────────────────────────────────┤
--  │ style_profiles   │ Lookup: valid style names (FK target)            │
--  │ color_families   │ Lookup: valid color names (FK target)            │
--  │ garment_types    │ Lookup: valid garment types (FK target)          │
--  │ product_master   │ Core catalogue — SKU, details, AI scoring attrs  │
--  │ inventory_live   │ EPC tag → SKU mapping (physical ↔ digital)      │
--  │ pairing_rules    │ Anatomy filter table (replaces Python dict)      │
--  │ color_harmony    │ Outfit color score matrix (replaces Python dict) │
--  │ skin_tone_synergy│ Skin tone color score table                      │
--  │ aesthetic_bonus  │ Cinematic combo bonus table                      │
--  └──────────────────┴──────────────────────────────────────────────────┘
-- =============================================================================


-- -----------------------------------------------------------------------------
-- BOOTSTRAP
-- -----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS smart_cart
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE smart_cart;

-- Disable FK checks during bulk insert, re-enable at end
SET FOREIGN_KEY_CHECKS = 0;


-- =============================================================================
-- SECTION 1 — LOOKUP / REFERENCE TABLES
-- Keeps the main tables normalised; easy to extend without schema changes.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1a. style_profiles
-- Valid style identity values used in product_master.style_profile
-- and referenced by the scoring engine.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS style_profiles (
    style_id    TINYINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    style_name  VARCHAR(40)         NOT NULL,
    description VARCHAR(160)        NULL,
    created_at  TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_style_profiles   PRIMARY KEY (style_id),
    CONSTRAINT uq_style_name       UNIQUE      (style_name)
) ENGINE=InnoDB COMMENT='Lookup table for garment style identities';

INSERT INTO style_profiles (style_name, description) VALUES
    ('Streetwear', 'Urban, oversized silhouettes, graphic elements, monochrome palettes'),
    ('Ethnic',     'Traditional South-Asian garments — Kurta, Pajama, Kolhapuri'),
    ('Minimalist', 'Clean cuts, neutral tones, no embellishment');


-- -----------------------------------------------------------------------------
-- 1b. color_families
-- Canonical color names used across all scoring tables and product_master.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS color_families (
    color_id    TINYINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    color_name  VARCHAR(30)         NOT NULL,
    hex_code    CHAR(7)             NULL     COMMENT 'Optional display hex',
    created_at  TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_color_families   PRIMARY KEY (color_id),
    CONSTRAINT uq_color_name       UNIQUE      (color_name)
) ENGINE=InnoDB COMMENT='Canonical color family names used for AI scoring';

INSERT INTO color_families (color_name, hex_code) VALUES
    ('Black',    '#1A1A1A'),
    ('White',    '#F5F5F5'),
    ('Navy',     '#1B2A4A'),
    ('Maroon',   '#6B1C2A'),
    ('Olive',    '#5A5E35'),
    ('Beige',    '#decfb3'),
    ('Charcoal', '#3D3D3D'),
    ('Mustard',  '#C8962A'),
    ('Red',      '#C0392B'),
    ('Green',    '#27AE60');


-- -----------------------------------------------------------------------------
-- 1c. garment_types
-- Canonical garment type names — FK target for product_master and
-- pairing_rules tables.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS garment_types (
    type_id         SMALLINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    type_name       VARCHAR(50)         NOT NULL,
    category        ENUM(
                        'Topwear',
                        'Bottomwear',
                        'Footwear',
                        'Accessory'
                    )                   NOT NULL,
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_garment_types    PRIMARY KEY (type_id),
    CONSTRAINT uq_garment_type     UNIQUE      (type_name)
) ENGINE=InnoDB COMMENT='Canonical garment type taxonomy';

INSERT INTO garment_types (type_name, category) VALUES
    ('Hoodie',              'Topwear'),
    ('Graphic Hoodie',      'Topwear'),
    ('Oversized T-Shirt',   'Topwear'),
    ('T-Shirt',             'Topwear'),
    ('Oversized Shirt',     'Topwear'),
    ('Kurta',               'Topwear'),
    ('Joggers',             'Bottomwear'),
    ('Cargo Pants',         'Bottomwear'),
    ('Jeans',               'Bottomwear'),
    ('Chinos',              'Bottomwear'),
    ('Shorts',              'Bottomwear'),
    ('Pajama',              'Bottomwear'),
    ('Sneakers',            'Footwear'),
    ('Ethnic Sandals',      'Footwear');


-- =============================================================================
-- SECTION 2 — CORE CATALOGUE: product_master
-- =============================================================================

CREATE TABLE IF NOT EXISTS product_master (
    -- Identity
    sku                 VARCHAR(20)         NOT NULL,
    name                VARCHAR(120)        NOT NULL,
    price               DECIMAL(8,2)        NOT NULL,

    -- Garment classification (denormalised for query speed on the edge device)
    garment_category    ENUM(
                            'Topwear',
                            'Bottomwear',
                            'Footwear',
                            'Accessory'
                        )                   NOT NULL,
    garment_type        VARCHAR(50)         NOT NULL,

    -- AI scoring attributes
    style_profile       VARCHAR(40)         NOT NULL,
    color_family        VARCHAR(30)         NOT NULL,

    -- Display
    image_url           VARCHAR(255)        NOT NULL,

    -- Metadata
    is_active           TINYINT(1)          NOT NULL DEFAULT 1
                            COMMENT '0 = soft-deleted / out of stock',
    created_at          TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_product_master    PRIMARY KEY  (sku),
    CONSTRAINT fk_pm_garment_type   FOREIGN KEY  (garment_type)
                                    REFERENCES   garment_types (type_name)
                                    ON UPDATE CASCADE,
    CONSTRAINT fk_pm_style_profile  FOREIGN KEY  (style_profile)
                                    REFERENCES   style_profiles (style_name)
                                    ON UPDATE CASCADE,
    CONSTRAINT fk_pm_color_family   FOREIGN KEY  (color_family)
                                    REFERENCES   color_families (color_name)
                                    ON UPDATE CASCADE,

    INDEX idx_pm_style              (style_profile),
    INDEX idx_pm_garment_type       (garment_type),
    INDEX idx_pm_color              (color_family),
    INDEX idx_pm_active             (is_active)

) ENGINE=InnoDB COMMENT='Master product catalogue — source of truth for all SKUs';


-- ── Seed: Streetwear ─────────────────────────────────────────────────────────
INSERT INTO product_master
    (sku, name, price, garment_category, garment_type, style_profile, color_family, image_url)
VALUES
    ('HD-BLK-OVR',  'Void Black Oversized Hoodie',    2499.00, 'Topwear',    'Hoodie',            'Streetwear', 'Black',    'https://assets.retailcart.io/HD-BLK-OVR.webp'),
    ('JGR-BLK-SLM', 'Matte Black Slim Joggers',       1599.00, 'Bottomwear', 'Joggers',           'Streetwear', 'Black',    'https://assets.retailcart.io/JGR-BLK-SLM.webp'),
    ('JGR-CHR-SLM', 'Charcoal Tech Joggers',          1699.00, 'Bottomwear', 'Joggers',           'Streetwear', 'Charcoal', 'https://assets.retailcart.io/JGR-CHR-SLM.webp'),
    ('CGO-OLV-TCT', 'Tactical Olive Cargo Pants',     1999.00, 'Bottomwear', 'Cargo Pants',       'Streetwear', 'Olive',    'https://assets.retailcart.io/CGO-OLV-TCT.webp'),
    ('TS-WHT-OVR',  'Clean Canvas Oversized Tee',      899.00, 'Topwear',    'Oversized T-Shirt', 'Streetwear', 'White',    'https://assets.retailcart.io/TS-WHT-OVR.webp'),
    ('HD-GRY-GFX',  'Ash Graphic Hoodie',             2199.00, 'Topwear',    'Graphic Hoodie',    'Streetwear', 'Charcoal', 'https://assets.retailcart.io/HD-GRY-GFX.webp'),
    ('SNK-WHT-CRT', 'Triple White Court Sneakers',    3499.00, 'Footwear',   'Sneakers',          'Streetwear', 'White',    'https://assets.retailcart.io/SNK-WHT-CRT.webp'),
    ('SNK-BLK-RNR', 'Stealth Black Runner Sneakers',  3299.00, 'Footwear',   'Sneakers',          'Streetwear', 'Black',    'https://assets.retailcart.io/SNK-BLK-RNR.webp');

-- ── Seed: Ethnic ─────────────────────────────────────────────────────────────
INSERT INTO product_master
    (sku, name, price, garment_category, garment_type, style_profile, color_family, image_url)
VALUES
    ('KRT-MRN-LNN', 'Ember Maroon Linen Kurta',       1799.00, 'Topwear',    'Kurta',          'Ethnic', 'Maroon', 'https://assets.retailcart.io/KRT-MRN-LNN.webp'),
    ('KRT-IVR-CTN', 'Ivory Cotton Kurta',             1599.00, 'Topwear',    'Kurta',          'Ethnic', 'Beige',  'https://assets.retailcart.io/KRT-IVR-CTN.webp'),
    ('CHN-BGE-SLM', 'Sand Beige Slim Chinos',         1499.00, 'Bottomwear', 'Chinos',         'Ethnic', 'Beige',  'https://assets.retailcart.io/CHN-BGE-SLM.webp'),
    ('PJM-WHT-ETH', 'Crisp White Ethnic Pajama',       799.00, 'Bottomwear', 'Pajama',         'Ethnic', 'White',  'https://assets.retailcart.io/PJM-WHT-ETH.webp'),
    ('SND-TAN-KLP', 'Artisan Tan Kolhapuri Sandals',  1299.00, 'Footwear',   'Ethnic Sandals', 'Ethnic', 'Beige',  'https://assets.retailcart.io/SND-TAN-KLP.webp');

-- ── Seed: Minimalist ─────────────────────────────────────────────────────────
INSERT INTO product_master
    (sku, name, price, garment_category, garment_type, style_profile, color_family, image_url)
VALUES
    ('TS-NVY-CRW',  'Essential Navy Crew Tee',         799.00, 'Topwear',    'T-Shirt',        'Minimalist', 'Navy',  'https://assets.retailcart.io/TS-NVY-CRW.webp'),
    ('TS-WHT-PMA',  'Classic White Pima Tee',           699.00, 'Topwear',    'T-Shirt',        'Minimalist', 'White', 'https://assets.retailcart.io/TS-WHT-PMA.webp'),
    ('SHT-BLK-DRP', 'Drop-Shoulder Black Shirt',      1399.00, 'Topwear',    'Oversized Shirt','Minimalist', 'Black', 'https://assets.retailcart.io/SHT-BLK-DRP.webp'),
    ('JNS-BLK-SLM', 'Washed Black Slim Jeans',        1999.00, 'Bottomwear', 'Jeans',          'Minimalist', 'Black', 'https://assets.retailcart.io/JNS-BLK-SLM.webp'),
    ('JNS-NVY-RAW', 'Raw Indigo Slim Jeans',           1999.00, 'Bottomwear', 'Jeans',          'Minimalist', 'Navy',  'https://assets.retailcart.io/JNS-NVY-RAW.webp'),
    ('SHT-WHT-LNN', 'Minimalist White Linen Shorts',   999.00, 'Bottomwear', 'Shorts',         'Minimalist', 'White', 'https://assets.retailcart.io/SHT-WHT-LNN.webp'),
    ('CHN-OLV-SLM', 'Field Olive Slim Chinos',        1499.00, 'Bottomwear', 'Chinos',         'Minimalist', 'Olive', 'https://assets.retailcart.io/CHN-OLV-SLM.webp');


-- =============================================================================
-- SECTION 3 — PHYSICAL TAG REGISTRY: inventory_live
-- Maps each physical UHF RFID EPC tag to a product SKU.
-- One tag per physical item on the shelf / in the store.
-- =============================================================================

CREATE TABLE IF NOT EXISTS inventory_live (
    epc_id          VARCHAR(20)         NOT NULL
                        COMMENT 'Raw EPC string from UHF RFID reader',
    sku             VARCHAR(20)         NOT NULL,
    location_zone   VARCHAR(40)         NULL
                        COMMENT 'Optional: shelf / aisle zone code',
    tagged_at       TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active       TINYINT(1)          NOT NULL DEFAULT 1
                        COMMENT '0 = tag decommissioned',

    CONSTRAINT pk_inventory_live    PRIMARY KEY (epc_id),
    CONSTRAINT fk_il_sku            FOREIGN KEY (sku)
                                    REFERENCES  product_master (sku)
                                    ON UPDATE CASCADE
                                    ON DELETE RESTRICT,
    INDEX idx_il_sku                (sku),
    INDEX idx_il_active             (is_active)

) ENGINE=InnoDB COMMENT='EPC tag → SKU registry; bridge between physical and digital';


INSERT INTO inventory_live (epc_id, sku, location_zone) VALUES
    -- Streetwear section
    ('E200001', 'HD-BLK-OVR',  'A-01'),
    ('E200002', 'JGR-BLK-SLM', 'A-02'),
    ('E200003', 'JGR-CHR-SLM', 'A-02'),
    ('E200004', 'CGO-OLV-TCT', 'A-03'),
    ('E200005', 'TS-WHT-OVR',  'A-04'),
    ('E200006', 'HD-GRY-GFX',  'A-01'),
    ('E200007', 'SNK-WHT-CRT', 'A-05'),
    ('E200008', 'SNK-BLK-RNR', 'A-05'),
    -- Ethnic section
    ('E200009', 'KRT-MRN-LNN', 'B-01'),
    ('E200010', 'KRT-IVR-CTN', 'B-01'),
    ('E200011', 'CHN-BGE-SLM', 'B-02'),
    ('E200012', 'PJM-WHT-ETH', 'B-02'),
    ('E200013', 'SND-TAN-KLP', 'B-03'),
    -- Minimalist section
    ('E200014', 'TS-NVY-CRW',  'C-01'),
    ('E200015', 'TS-WHT-PMA',  'C-01'),
    ('E200016', 'SHT-BLK-DRP', 'C-02'),
    ('E200017', 'JNS-BLK-SLM', 'C-03'),
    ('E200018', 'JNS-NVY-RAW', 'C-03'),
    ('E200019', 'SHT-WHT-LNN', 'C-04'),
    ('E200020', 'CHN-OLV-SLM', 'C-02');


-- =============================================================================
-- SECTION 4 — AI ENGINE TABLES
-- These tables replace the Python dicts in smart_cart_api.py so the
-- scoring logic can be database-driven and updated without redeploying code.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 4a. pairing_rules
-- Anatomy filter: defines which garment_types can pair with a given cart type.
-- Replaces the PAIRING_RULES dict in the Flask app.
--
-- Query used by the API:
--   SELECT candidate_type FROM pairing_rules WHERE cart_type = ?
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pairing_rules (
    rule_id         SMALLINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    cart_type       VARCHAR(50)         NOT NULL
                        COMMENT 'garment_type of the item in the cart',
    candidate_type  VARCHAR(50)         NOT NULL
                        COMMENT 'garment_type that is anatomically valid to recommend',

    CONSTRAINT pk_pairing_rules     PRIMARY KEY (rule_id),
    CONSTRAINT uq_pairing_combo     UNIQUE      (cart_type, candidate_type),
    CONSTRAINT fk_pr_cart_type      FOREIGN KEY (cart_type)
                                    REFERENCES  garment_types (type_name)
                                    ON UPDATE CASCADE,
    CONSTRAINT fk_pr_candidate_type FOREIGN KEY (candidate_type)
                                    REFERENCES  garment_types (type_name)
                                    ON UPDATE CASCADE,
    INDEX idx_pr_cart_type          (cart_type)

) ENGINE=InnoDB COMMENT='Anatomy filter: valid garment pairings for recommendation';

INSERT INTO pairing_rules (cart_type, candidate_type) VALUES
    -- Hoodie pairings
    ('Hoodie',           'Cargo Pants'),
    ('Hoodie',           'Joggers'),
    ('Hoodie',           'Sneakers'),
    -- Graphic Hoodie pairings
    ('Graphic Hoodie',   'Cargo Pants'),
    ('Graphic Hoodie',   'Joggers'),
    ('Graphic Hoodie',   'Sneakers'),
    -- Kurta pairings
    ('Kurta',            'Chinos'),
    ('Kurta',            'Pajama'),
    ('Kurta',            'Ethnic Sandals'),
    -- T-Shirt pairings
    ('T-Shirt',          'Jeans'),
    ('T-Shirt',          'Shorts'),
    ('T-Shirt',          'Chinos'),
    ('T-Shirt',          'Oversized Shirt'),
    -- Oversized T-Shirt pairings
    ('Oversized T-Shirt','Jeans'),
    ('Oversized T-Shirt','Cargo Pants'),
    ('Oversized T-Shirt','Shorts'),
    -- Cargo Pants pairings
    ('Cargo Pants',      'Oversized T-Shirt'),
    ('Cargo Pants',      'Graphic Hoodie'),
    ('Cargo Pants',      'Sneakers'),
    ('Cargo Pants',      'Hoodie'),
    -- Joggers pairings
    ('Joggers',          'Hoodie'),
    ('Joggers',          'Graphic Hoodie'),
    ('Joggers',          'Oversized T-Shirt'),
    ('Joggers',          'Sneakers'),
    -- Jeans pairings
    ('Jeans',            'T-Shirt'),
    ('Jeans',            'Oversized Shirt'),
    ('Jeans',            'Hoodie'),
    -- Chinos pairings
    ('Chinos',           'T-Shirt'),
    ('Chinos',           'Kurta'),
    ('Chinos',           'Oversized Shirt'),
    -- Sneakers pairings
    ('Sneakers',         'Cargo Pants'),
    ('Sneakers',         'Joggers'),
    ('Sneakers',         'Jeans'),
    ('Sneakers',         'Shorts'),
    ('Sneakers',         'Chinos');


-- -----------------------------------------------------------------------------
-- 4b. color_harmony
-- Outfit color scoring matrix. Replaces COLOR_HARMONY_MATRIX Python dict.
-- score range: -30 (clash) to +30 (perfect complement / monochromatic)
--
-- Query used by the API:
--   SELECT harmony_score FROM color_harmony
--   WHERE source_color = ? AND target_color = ?
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS color_harmony (
    harmony_id      SMALLINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    source_color    VARCHAR(30)         NOT NULL
                        COMMENT 'color_family of the cart item',
    target_color    VARCHAR(30)         NOT NULL
                        COMMENT 'color_family of the candidate item',
    harmony_score   TINYINT             NOT NULL
                        COMMENT 'Range -30 (clash) to +30 (perfect)',
    note            VARCHAR(80)         NULL,

    CONSTRAINT pk_color_harmony     PRIMARY KEY (harmony_id),
    CONSTRAINT uq_color_combo       UNIQUE      (source_color, target_color),
    CONSTRAINT fk_ch_source         FOREIGN KEY (source_color)
                                    REFERENCES  color_families (color_name)
                                    ON UPDATE CASCADE,
    CONSTRAINT fk_ch_target         FOREIGN KEY (target_color)
                                    REFERENCES  color_families (color_name)
                                    ON UPDATE CASCADE,
    INDEX idx_ch_source             (source_color)

) ENGINE=InnoDB COMMENT='Outfit color harmony scoring matrix for the AI engine';

INSERT INTO color_harmony (source_color, target_color, harmony_score, note) VALUES
    -- Black as source
    ('Black','Black',    30, 'Monochromatic stealth'),
    ('Black','White',    28, 'High-contrast classic'),
    ('Black','Charcoal', 25, 'Tonal depth'),
    ('Black','Maroon',   20, 'Deep accent — cinematic'),
    ('Black','Navy',     20, NULL),
    ('Black','Olive',    18, NULL),
    ('Black','Beige',    15, NULL),
    ('Black','Mustard',  10, NULL),
    ('Black','Red',     -10, 'Clash'),
    ('Black','Green',   -20, 'Strong clash'),
    -- White as source
    ('White','White',    30, 'All-white editorial'),
    ('White','Navy',     28, 'Timeless nautical'),
    ('White','Black',    28, 'Classic contrast'),
    ('White','Beige',    22, NULL),
    ('White','Charcoal', 20, NULL),
    ('White','Olive',    18, NULL),
    ('White','Maroon',   15, NULL),
    ('White','Mustard',  12, NULL),
    ('White','Red',       5, NULL),
    ('White','Green',    -5, NULL),
    -- Navy as source
    ('Navy','White',     30, 'Classic navy + white'),
    ('Navy','Beige',     25, NULL),
    ('Navy','Navy',      22, 'Tonal'),
    ('Navy','Black',     20, NULL),
    ('Navy','Charcoal',  18, NULL),
    ('Navy','Olive',     15, NULL),
    ('Navy','Mustard',   12, NULL),
    ('Navy','Maroon',    10, NULL),
    ('Navy','Red',       -5, NULL),
    ('Navy','Green',    -10, 'Clash'),
    -- Maroon as source
    ('Maroon','Beige',   30, 'Signature warm pairing'),
    ('Maroon','White',   25, NULL),
    ('Maroon','Black',   22, NULL),
    ('Maroon','Olive',   18, NULL),
    ('Maroon','Charcoal',15, NULL),
    ('Maroon','Maroon',  12, 'Tonal burgundy'),
    ('Maroon','Navy',    10, NULL),
    ('Maroon','Mustard',  8, NULL),
    ('Maroon','Red',    -15, 'Too close, muddy'),
    ('Maroon','Green',  -20, 'Strong clash'),
    -- Olive as source
    ('Olive','Beige',    28, NULL),
    ('Olive','Black',    25, NULL),
    ('Olive','White',    22, NULL),
    ('Olive','Charcoal', 20, NULL),
    ('Olive','Navy',     18, NULL),
    ('Olive','Olive',    15, 'Tonal'),
    ('Olive','Maroon',   15, NULL),
    ('Olive','Mustard',  10, NULL),
    ('Olive','Red',      -5, NULL),
    ('Olive','Green',   -15, 'Clash'),
    -- Beige as source
    ('Beige','Maroon',   30, 'Warm anchor'),
    ('Beige','Olive',    28, NULL),
    ('Beige','White',    25, NULL),
    ('Beige','Navy',     22, NULL),
    ('Beige','Black',    20, NULL),
    ('Beige','Charcoal', 18, NULL),
    ('Beige','Beige',    18, 'Tonal'),
    ('Beige','Mustard',  10, NULL),
    ('Beige','Red',       5, NULL),
    ('Beige','Green',    -5, NULL),
    -- Charcoal as source
    ('Charcoal','White',    28, NULL),
    ('Charcoal','Black',    25, NULL),
    ('Charcoal','Charcoal', 22, 'Tonal'),
    ('Charcoal','Navy',     20, NULL),
    ('Charcoal','Beige',    18, NULL),
    ('Charcoal','Olive',    15, NULL),
    ('Charcoal','Maroon',   15, NULL),
    ('Charcoal','Mustard',  10, NULL),
    ('Charcoal','Red',      -5, NULL),
    ('Charcoal','Green',   -10, 'Clash');


-- -----------------------------------------------------------------------------
-- 4c. skin_tone_synergy
-- Maps (skin_tone, color_family) → synergy bonus for the AI scoring engine.
-- Replaces SKIN_TONE_SYNERGY Python dict.
-- score range: 0 to +30 (no negatives — skin tone never penalises)
--
-- Query used by the API:
--   SELECT synergy_score FROM skin_tone_synergy
--   WHERE skin_tone = ? AND color_family = ?
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skin_tone_synergy (
    synergy_id      SMALLINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    skin_tone       ENUM(
                        'Warm',
                        'Cool',
                        'Neutral'
                    )                   NOT NULL,
    color_family    VARCHAR(30)         NOT NULL,
    synergy_score   TINYINT UNSIGNED    NOT NULL
                        COMMENT 'Range 0 to 30',
    note            VARCHAR(80)         NULL,

    CONSTRAINT pk_skin_tone_synergy PRIMARY KEY (synergy_id),
    CONSTRAINT uq_skin_color_combo  UNIQUE      (skin_tone, color_family),
    CONSTRAINT fk_sts_color         FOREIGN KEY (color_family)
                                    REFERENCES  color_families (color_name)
                                    ON UPDATE CASCADE,
    INDEX idx_sts_skin_tone         (skin_tone)

) ENGINE=InnoDB COMMENT='Skin tone to color synergy scores for the AI engine';

INSERT INTO skin_tone_synergy (skin_tone, color_family, synergy_score, note) VALUES
    -- Warm skin — earth / autumn palette
    ('Warm','Olive',    30, 'Earth tone — excellent'),
    ('Warm','Mustard',  30, 'Autumn tone — excellent'),
    ('Warm','Maroon',   28, 'Deep warm tone'),
    ('Warm','Beige',    25, 'Warm neutral'),
    ('Warm','White',    15, NULL),
    ('Warm','Black',    10, NULL),
    ('Warm','Navy',      8, NULL),
    ('Warm','Charcoal',  8, NULL),
    ('Warm','Red',       5, NULL),
    ('Warm','Green',     5, NULL),
    -- Cool skin — jewel / arctic palette
    ('Cool','Navy',     30, 'Jewel tone — excellent'),
    ('Cool','Charcoal', 28, 'Deep cool tone'),
    ('Cool','White',    25, 'Arctic clean'),
    ('Cool','Black',    20, NULL),
    ('Cool','Green',    10, NULL),
    ('Cool','Olive',    10, NULL),
    ('Cool','Beige',     8, NULL),
    ('Cool','Maroon',    8, NULL),
    ('Cool','Mustard',   5, NULL),
    ('Cool','Red',       5, NULL),
    -- Neutral skin — flat baseline
    ('Neutral','Black',    15, 'Baseline'),
    ('Neutral','White',    15, 'Baseline'),
    ('Neutral','Navy',     15, 'Baseline'),
    ('Neutral','Olive',    15, 'Baseline'),
    ('Neutral','Beige',    15, 'Baseline'),
    ('Neutral','Maroon',   15, 'Baseline'),
    ('Neutral','Charcoal', 15, 'Baseline'),
    ('Neutral','Mustard',  15, 'Baseline'),
    ('Neutral','Red',      10, NULL),
    ('Neutral','Green',    10, NULL);


-- -----------------------------------------------------------------------------
-- 4d. aesthetic_bonus
-- Cinematic editorial bonus for premium (cart_color, candidate_color) combos.
-- Replaces AESTHETIC_BONUS Python dict.
--
-- Query used by the API:
--   SELECT bonus_score FROM aesthetic_bonus
--   WHERE cart_color = ? AND candidate_color = ?
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aesthetic_bonus (
    bonus_id        SMALLINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    cart_color      VARCHAR(30)         NOT NULL,
    candidate_color VARCHAR(30)         NOT NULL,
    bonus_score     TINYINT UNSIGNED    NOT NULL,
    note            VARCHAR(80)         NULL,

    CONSTRAINT pk_aesthetic_bonus   PRIMARY KEY (bonus_id),
    CONSTRAINT uq_aesthetic_combo   UNIQUE      (cart_color, candidate_color),
    CONSTRAINT fk_ab_cart_color     FOREIGN KEY (cart_color)
                                    REFERENCES  color_families (color_name)
                                    ON UPDATE CASCADE,
    CONSTRAINT fk_ab_cand_color     FOREIGN KEY (candidate_color)
                                    REFERENCES  color_families (color_name)
                                    ON UPDATE CASCADE

) ENGINE=InnoDB COMMENT='Cinematic aesthetic bonus combos for the AI scoring engine';

INSERT INTO aesthetic_bonus (cart_color, candidate_color, bonus_score, note) VALUES
    ('White',    'White',    20, 'All-white editorial'),
    ('Black',    'Black',    15, 'Stealth monochrome'),
    ('Navy',     'White',    15, 'Nautical contrast'),
    ('White',    'Navy',     15, 'Nautical contrast'),
    ('Maroon',   'Beige',    20, 'Burgundy + sand — cinematic'),
    ('Beige',    'Maroon',   20, 'Sand + burgundy — cinematic'),
    ('Black',    'Maroon',   18, 'Dark with wine accent'),
    ('Olive',    'Beige',    15, 'Earth tone pair'),
    ('Beige',    'Olive',    15, 'Earth tone pair'),
    ('Charcoal', 'White',    12, 'Tonal break');


-- =============================================================================
-- SECTION 5 — USEFUL VIEWS
-- Pre-built queries the Flask API (or MySQL Workbench) can call directly.
-- =============================================================================

-- Full product detail view (joins all lookups — replaces PRODUCT_MASTER dict)
CREATE OR REPLACE VIEW vw_product_full AS
SELECT
    pm.sku,
    pm.name,
    pm.price,
    pm.garment_category,
    pm.garment_type,
    pm.style_profile,
    pm.color_family,
    pm.image_url,
    pm.is_active
FROM product_master pm
WHERE pm.is_active = 1;


-- EPC resolution view (one query to go from EPC → full product details)
CREATE OR REPLACE VIEW vw_epc_product AS
SELECT
    il.epc_id,
    il.location_zone,
    pm.sku,
    pm.name,
    pm.price,
    pm.garment_category,
    pm.garment_type,
    pm.style_profile,
    pm.color_family,
    pm.image_url
FROM inventory_live il
INNER JOIN product_master pm ON il.sku = pm.sku
WHERE il.is_active = 1
  AND pm.is_active  = 1;


-- Candidate pool view for a given cart garment type
-- Usage: SELECT * FROM vw_valid_candidates WHERE cart_type = 'Kurta'
CREATE OR REPLACE VIEW vw_valid_candidates AS
SELECT
    pr.cart_type,
    pm.sku,
    pm.name,
    pm.price,
    pm.garment_type,
    pm.style_profile,
    pm.color_family,
    pm.image_url
FROM pairing_rules pr
INNER JOIN product_master pm
    ON pm.garment_type = pr.candidate_type
   AND pm.is_active    = 1;


-- =============================================================================
-- SECTION 6 — RE-ENABLE FK CHECKS
-- =============================================================================
SET FOREIGN_KEY_CHECKS = 1;


-- =============================================================================
-- QUICK VERIFICATION QUERIES (run after import to confirm row counts)
-- =============================================================================
-- SELECT 'style_profiles'    AS tbl, COUNT(*) AS rows FROM style_profiles   UNION ALL
-- SELECT 'color_families',            COUNT(*)         FROM color_families   UNION ALL
-- SELECT 'garment_types',             COUNT(*)         FROM garment_types    UNION ALL
-- SELECT 'product_master',            COUNT(*)         FROM product_master   UNION ALL
-- SELECT 'inventory_live',            COUNT(*)         FROM inventory_live   UNION ALL
-- SELECT 'pairing_rules',             COUNT(*)         FROM pairing_rules    UNION ALL
-- SELECT 'color_harmony',             COUNT(*)         FROM color_harmony    UNION ALL
-- SELECT 'skin_tone_synergy',         COUNT(*)         FROM skin_tone_synergy UNION ALL
-- SELECT 'aesthetic_bonus',           COUNT(*)         FROM aesthetic_bonus;
--
-- Expected: 3 | 10 | 14 | 20 | 20 | 35 | 70 | 30 | 10
-- =============================================================================