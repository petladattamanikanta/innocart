-- =============================================================================
-- INNOCART V2 — Supabase (PostgreSQL) Seed Data Script
-- File    : migrations/supabase_seed.sql
-- Purpose : Populate Supabase PostgreSQL DB with 21 product catalogue SKUs,
--           EPC tags, 5-stage AI scoring rules, rush deals, and admin user.
-- =============================================================================

-- 1. STORES
INSERT INTO stores (store_id, name, location, city) VALUES
    ('STORE-001', 'Zudio Flagship Store', 'Phoenix Marketcity, Lower Parel', 'Mumbai')
ON CONFLICT (store_id) DO UPDATE SET name = EXCLUDED.name;

-- 2. LOOKUPS
INSERT INTO style_profiles (style_name, description) VALUES
    ('Streetwear', 'Urban, oversized silhouettes, graphic elements, monochrome palettes'),
    ('Ethnic',     'Traditional South-Asian garments — Kurta, Pajama, Kolhapuri'),
    ('Minimalist', 'Clean cuts, neutral tones, no embellishment')
ON CONFLICT (style_name) DO UPDATE SET description = EXCLUDED.description;

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
    ('Green',    '#27AE60')
ON CONFLICT (color_name) DO UPDATE SET hex_code = EXCLUDED.hex_code;

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
    ('Ethnic Sandals',      'Footwear')
ON CONFLICT (type_name) DO UPDATE SET category = EXCLUDED.category;

-- 3. PRODUCT MASTER (21 Catalogue SKUs matching Simulator)
INSERT INTO product_master 
    (sku, name, price, garment_category, garment_type, style_profile, color_family, image_url, aisle_location)
VALUES
    -- Streetwear
    ('HD-BLK-OVR',  'Void Black Oversized Hoodie',    2499.00, 'Topwear',    'Hoodie',            'Streetwear', 'Black',    'https://assets.retailcart.io/HD-BLK-OVR.webp', 'Aisle A-01'),
    ('JGR-BLK-SLM', 'Matte Black Slim Joggers',       1599.00, 'Bottomwear', 'Joggers',           'Streetwear', 'Black',    'https://assets.retailcart.io/JGR-BLK-SLM.webp', 'Aisle A-02'),
    ('JGR-CHR-SLM', 'Charcoal Tech Joggers',          1699.00, 'Bottomwear', 'Joggers',           'Streetwear', 'Charcoal', 'https://assets.retailcart.io/JGR-CHR-SLM.webp', 'Aisle A-02'),
    ('CGO-OLV-TCT', 'Tactical Olive Cargo Pants',     1999.00, 'Bottomwear', 'Cargo Pants',       'Streetwear', 'Olive',    'https://assets.retailcart.io/CGO-OLV-TCT.webp', 'Aisle A-03'),
    ('TS-WHT-OVR',  'Clean Canvas Oversized Tee',      899.00, 'Topwear',    'Oversized T-Shirt', 'Streetwear', 'White',    'https://assets.retailcart.io/TS-WHT-OVR.webp', 'Aisle A-04'),
    ('HD-GRY-GFX',  'Ash Graphic Hoodie',             2199.00, 'Topwear',    'Graphic Hoodie',    'Streetwear', 'Charcoal', 'https://assets.retailcart.io/HD-GRY-GFX.webp', 'Aisle A-01'),
    ('SNK-WHT-CRT', 'Triple White Court Sneakers',    3499.00, 'Footwear',   'Sneakers',          'Streetwear', 'White',    'https://assets.retailcart.io/SNK-WHT-CRT.webp', 'Aisle A-05'),
    ('SNK-BLK-RNR', 'Stealth Black Runner Sneakers',  3299.00, 'Footwear',   'Sneakers',          'Streetwear', 'Black',    'https://assets.retailcart.io/SNK-BLK-RNR.webp', 'Aisle A-05'),

    -- Ethnic
    ('KRT-MRN-LNN', 'Ember Maroon Linen Kurta',       1799.00, 'Topwear',    'Kurta',          'Ethnic', 'Maroon', 'https://assets.retailcart.io/KRT-MRN-LNN.webp', 'Aisle B-01'),
    ('KRT-IVR-CTN', 'Ivory Cotton Kurta',             1599.00, 'Topwear',    'Kurta',          'Ethnic', 'Beige',  'https://assets.retailcart.io/KRT-IVR-CTN.webp', 'Aisle B-01'),
    ('CHN-BGE-SLM', 'Sand Beige Slim Chinos',         1499.00, 'Bottomwear', 'Chinos',         'Ethnic', 'Beige',  'https://assets.retailcart.io/CHN-BGE-SLM.webp', 'Aisle B-02'),
    ('PJM-WHT-ETH', 'Crisp White Ethnic Pajama',       799.00, 'Bottomwear', 'Pajama',         'Ethnic', 'White',  'https://assets.retailcart.io/PJM-WHT-ETH.webp', 'Aisle B-02'),
    ('SND-TAN-KLP', 'Artisan Tan Kolhapuri Sandals',  1299.00, 'Footwear',   'Ethnic Sandals', 'Ethnic', 'Beige',  'https://assets.retailcart.io/SND-TAN-KLP.webp', 'Aisle B-03'),

    -- Minimalist
    ('TS-NVY-CRW',  'Essential Navy Crew Tee',        799.00, 'Topwear',    'T-Shirt',          'Minimalist', 'Navy',  'https://assets.retailcart.io/TS-NVY-CRW.webp', 'Aisle C-01'),
    ('TS-WHT-PMA',  'Classic White Pima Tee',         699.00, 'Topwear',    'T-Shirt',          'Minimalist', 'White', 'https://assets.retailcart.io/TS-WHT-PMA.webp', 'Aisle C-01'),
    ('SHT-BLK-DRP', 'Drop-Shoulder Black Shirt',     1399.00, 'Topwear',    'Oversized Shirt',  'Minimalist', 'Black', 'https://assets.retailcart.io/SHT-BLK-DRP.webp', 'Aisle C-02'),
    ('JNS-BLK-SLM', 'Washed Black Slim Jeans',        1999.00, 'Bottomwear', 'Jeans',            'Minimalist', 'Black', 'https://assets.retailcart.io/JNS-BLK-SLM.webp', 'Aisle C-03'),
    ('JNS-NVY-RAW', 'Raw Indigo Slim Jeans',          1999.00, 'Bottomwear', 'Jeans',            'Minimalist', 'Navy',  'https://assets.retailcart.io/JNS-NVY-RAW.webp', 'Aisle C-03'),
    ('SHT-WHT-LNN', 'Minimalist White Linen Shorts',  999.00, 'Bottomwear', 'Shorts',           'Minimalist', 'White', 'https://assets.retailcart.io/SHT-WHT-LNN.webp', 'Aisle C-04'),
    ('CHN-OLV-SLM', 'Field Olive Slim Chinos',        1499.00, 'Bottomwear', 'Chinos',           'Minimalist', 'Olive', 'https://assets.retailcart.io/CHN-OLV-SLM.webp', 'Aisle C-02')
ON CONFLICT (sku) DO UPDATE SET name = EXCLUDED.name, price = EXCLUDED.price;

-- 4. INVENTORY LIVE (EPC Mappings matching Simulator E1/E2/E3 ranges)
INSERT INTO inventory_live (epc_id, sku, store_id) VALUES
    ('E100001', 'HD-BLK-OVR', 'STORE-001'), ('E100002', 'HD-BLK-OVR', 'STORE-001'), ('E100003', 'HD-BLK-OVR', 'STORE-001'),
    ('E100004', 'JGR-BLK-SLM', 'STORE-001'), ('E100005', 'JGR-BLK-SLM', 'STORE-001'), ('E100006', 'JGR-BLK-SLM', 'STORE-001'),
    ('E100007', 'JGR-CHR-SLM', 'STORE-001'), ('E100008', 'JGR-CHR-SLM', 'STORE-001'), ('E100009', 'JGR-CHR-SLM', 'STORE-001'),
    ('E100010', 'CGO-OLV-TCT', 'STORE-001'), ('E100011', 'CGO-OLV-TCT', 'STORE-001'), ('E100012', 'CGO-OLV-TCT', 'STORE-001'),
    ('E100013', 'TS-WHT-OVR',  'STORE-001'), ('E100014', 'TS-WHT-OVR',  'STORE-001'), ('E100015', 'TS-WHT-OVR',  'STORE-001'),
    ('E100016', 'HD-GRY-GFX',  'STORE-001'), ('E100017', 'HD-GRY-GFX',  'STORE-001'), ('E100018', 'HD-GRY-GFX',  'STORE-001'),
    ('E100019', 'SNK-WHT-CRT', 'STORE-001'), ('E100020', 'SNK-WHT-CRT', 'STORE-001'), ('E100021', 'SNK-WHT-CRT', 'STORE-001'),
    ('E100022', 'SNK-BLK-RNR', 'STORE-001'), ('E100023', 'SNK-BLK-RNR', 'STORE-001'), ('E100024', 'SNK-BLK-RNR', 'STORE-001'),
    
    ('E200001', 'KRT-MRN-LNN', 'STORE-001'), ('E200002', 'KRT-MRN-LNN', 'STORE-001'), ('E200003', 'KRT-MRN-LNN', 'STORE-001'),
    ('E200004', 'KRT-IVR-CTN', 'STORE-001'), ('E200005', 'KRT-IVR-CTN', 'STORE-001'), ('E200006', 'KRT-IVR-CTN', 'STORE-001'),
    ('E200007', 'CHN-BGE-SLM', 'STORE-001'), ('E200008', 'CHN-BGE-SLM', 'STORE-001'), ('E200009', 'CHN-BGE-SLM', 'STORE-001'),
    ('E200010', 'PJM-WHT-ETH', 'STORE-001'), ('E200011', 'PJM-WHT-ETH', 'STORE-001'), ('E200012', 'PJM-WHT-ETH', 'STORE-001'),
    ('E200013', 'SND-TAN-KLP', 'STORE-001'), ('E200014', 'SND-TAN-KLP', 'STORE-001'), ('E200015', 'SND-TAN-KLP', 'STORE-001'),

    ('E300001', 'TS-NVY-CRW',  'STORE-001'), ('E300002', 'TS-NVY-CRW',  'STORE-001'), ('E300003', 'TS-NVY-CRW',  'STORE-001'),
    ('E300004', 'TS-WHT-PMA',  'STORE-001'), ('E300005', 'TS-WHT-PMA',  'STORE-001'), ('E300006', 'TS-WHT-PMA',  'STORE-001'),
    ('E300007', 'SHT-BLK-DRP', 'STORE-001'), ('E300008', 'SHT-BLK-DRP', 'STORE-001'), ('E300009', 'SHT-BLK-DRP', 'STORE-001'),
    ('E300010', 'JNS-BLK-SLM', 'STORE-001'), ('E300011', 'JNS-BLK-SLM', 'STORE-001'), ('E300012', 'JNS-BLK-SLM', 'STORE-001'),
    ('E300013', 'JNS-NVY-RAW', 'STORE-001'), ('E300014', 'JNS-NVY-RAW', 'STORE-001'), ('E300015', 'JNS-NVY-RAW', 'STORE-001'),
    ('E300016', 'SHT-WHT-LNN', 'STORE-001'), ('E300017', 'SHT-WHT-LNN', 'STORE-001'), ('E300018', 'SHT-WHT-LNN', 'STORE-001'),
    ('E300019', 'CHN-OLV-SLM', 'STORE-001'), ('E300020', 'CHN-OLV-SLM', 'STORE-001'), ('E300021', 'CHN-OLV-SLM', 'STORE-001')
ON CONFLICT (epc_id) DO UPDATE SET store_id = EXCLUDED.store_id;

-- 5. PAIRING RULES
TRUNCATE TABLE pairing_rules RESTART IDENTITY;
INSERT INTO pairing_rules (cart_type, candidate_type) VALUES
    ('Hoodie',           'Cargo Pants'), ('Hoodie',           'Joggers'),     ('Hoodie',           'Sneakers'),
    ('Graphic Hoodie',   'Cargo Pants'), ('Graphic Hoodie',   'Joggers'),     ('Graphic Hoodie',   'Sneakers'),
    ('Kurta',            'Chinos'),      ('Kurta',            'Pajama'),      ('Kurta',            'Ethnic Sandals'),
    ('T-Shirt',          'Jeans'),       ('T-Shirt',          'Shorts'),      ('T-Shirt',          'Chinos'),
    ('Oversized T-Shirt','Jeans'),       ('Oversized T-Shirt','Cargo Pants'), ('Oversized T-Shirt','Shorts'),
    ('Cargo Pants',      'Oversized T-Shirt'), ('Cargo Pants','Graphic Hoodie'), ('Cargo Pants',  'Sneakers'),
    ('Joggers',          'Hoodie'),      ('Joggers',          'Oversized T-Shirt'), ('Joggers',    'Sneakers'),
    ('Jeans',            'T-Shirt'),     ('Jeans',            'Oversized Shirt'),  ('Jeans',      'Hoodie'),
    ('Chinos',           'T-Shirt'),     ('Chinos',           'Kurta'),            ('Chinos',     'Oversized Shirt'),
    ('Sneakers',         'Cargo Pants'), ('Sneakers',         'Joggers'),          ('Sneakers',   'Jeans');

-- 6. COLOR HARMONY
TRUNCATE TABLE color_harmony RESTART IDENTITY;
INSERT INTO color_harmony (source_color, target_color, harmony_score) VALUES
    ('Black','Black', 30), ('Black','White', 28), ('Black','Charcoal', 25), ('Black','Maroon', 20), ('Black','Navy', 20), ('Black','Olive', 18), ('Black','Beige', 15), ('Black','Red', -10),
    ('White','White', 30), ('White','Navy', 28), ('White','Black', 28), ('White','Beige', 22), ('White','Charcoal', 20), ('White','Olive', 18), ('White','Maroon', 15),
    ('Navy','White', 30), ('Navy','Beige', 25), ('Navy','Navy', 22), ('Navy','Black', 20), ('Navy','Charcoal', 18), ('Navy','Olive', 15),
    ('Maroon','Beige', 30), ('Maroon','White', 25), ('Maroon','Black', 22), ('Maroon','Olive', 18), ('Maroon','Charcoal', 15), ('Maroon','Maroon', 12),
    ('Olive','Beige', 28), ('Olive','Black', 25), ('Olive','White', 22), ('Olive','Charcoal', 20), ('Olive','Navy', 18), ('Olive','Olive', 15),
    ('Beige','Maroon', 30), ('Beige','Olive', 28), ('Beige','White', 25), ('Beige','Navy', 22), ('Beige','Black', 20), ('Beige','Charcoal', 18),
    ('Charcoal','White', 28), ('Charcoal','Black', 25), ('Charcoal','Charcoal', 22), ('Charcoal','Navy', 20), ('Charcoal','Beige', 18);

-- 7. SKIN TONE SYNERGY (Legacy)
TRUNCATE TABLE skin_tone_synergy RESTART IDENTITY;
INSERT INTO skin_tone_synergy (skin_tone, color_family, synergy_score) VALUES
    ('Warm','Olive', 30), ('Warm','Mustard', 30), ('Warm','Maroon', 28), ('Warm','Beige', 25), ('Warm','White', 15), ('Warm','Black', 10),
    ('Cool','Navy', 30), ('Cool','Charcoal', 28), ('Cool','White', 25), ('Cool','Black', 20), ('Cool','Green', 10),
    ('Neutral','Black', 15), ('Neutral','White', 15), ('Neutral','Navy', 15), ('Neutral','Olive', 15), ('Neutral','Beige', 15), ('Neutral','Maroon', 15), ('Neutral','Charcoal', 15);

-- 8. AESTHETIC BONUS
TRUNCATE TABLE aesthetic_bonus RESTART IDENTITY;
INSERT INTO aesthetic_bonus (cart_color, candidate_color, bonus_score) VALUES
    ('White','White', 20), ('Black','Black', 15), ('Navy','White', 15), ('White','Navy', 15),
    ('Maroon','Beige', 20), ('Beige','Maroon', 20), ('Black','Maroon', 18), ('Olive','Beige', 15), ('Beige','Olive', 15);

-- 9. HEX SKIN ZONES & FACIAL COLOR HARMONY
TRUNCATE TABLE hex_skin_zones RESTART IDENTITY;
INSERT INTO hex_skin_zones (undertone_label, lum_min, lum_max, hue_min, hue_max, sat_min, sat_max, priority) VALUES
    ('Warm-Golden',   40, 220,  10,  40, 15, 75, 1),
    ('Cool-Rosy',     40, 220, 340,  10, 15, 75, 2),
    ('Neutral-Beige', 30, 230,   0, 360,  0, 25, 3),
    ('Deep-Warm',     10, 120,   5,  35, 10, 80, 4);

TRUNCATE TABLE facial_color_harmony RESTART IDENTITY;
INSERT INTO facial_color_harmony (undertone_label, color_family, harmony_score) VALUES
    ('Warm-Golden',   'Olive',    40),
    ('Warm-Golden',   'Beige',    35),
    ('Warm-Golden',   'Maroon',   35),
    ('Warm-Golden',   'Black',    25),
    ('Warm-Golden',   'White',    20),
    ('Cool-Rosy',     'Navy',     40),
    ('Cool-Rosy',     'White',    35),
    ('Cool-Rosy',     'Charcoal', 35),
    ('Cool-Rosy',     'Black',    25),
    ('Neutral-Beige', 'Black',    30),
    ('Neutral-Beige', 'White',    30),
    ('Neutral-Beige', 'Navy',     30),
    ('Neutral-Beige', 'Olive',    30),
    ('Neutral-Beige', 'Maroon',   30),
    ('Deep-Warm',     'Mustard',  40),
    ('Deep-Warm',     'Maroon',   38),
    ('Deep-Warm',     'Olive',    35),
    ('Deep-Warm',     'White',    30);

-- 10. RUSH DEALS
TRUNCATE TABLE deals;
INSERT INTO deals (deal_code, title, description, discount_type, discount_value, min_cart_value, category_restriction, badge_text) VALUES
    ('RUSH200', '₹200 Instant Rush Discount', 'Save ₹200 on cart value above ₹2,500', 'FIXED', 200.00, 2500.00, NULL, '⚡ RUSH DEAL'),
    ('FOOTWEAR15', '15% Off Footwear', 'Get 15% off sneakers or sandals when added to cart', 'PERCENTAGE', 15.00, 1000.00, 'Footwear', '👟 FOOTWEAR OFFER'),
    ('LOYALTY500', '₹500 VIP Customer Offer', 'Special discount for returning customers with cart total > ₹4,000', 'FIXED', 500.00, 4000.00, NULL, '👑 VIP DEAL');

-- 11. DEFAULT ADMIN USER (Username: admin, Password: adminpassword)
INSERT INTO admin_users (username, password_hash, role, store_id) VALUES
    ('admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'STORE_MANAGER', 'STORE-001')
ON CONFLICT (username) DO UPDATE SET role = EXCLUDED.role;
