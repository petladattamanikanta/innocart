-- Supabase Database Seed & Schema Alteration Script
-- File: supabase/migrations/20260729000000_seed_product_master.sql

-- 1. Ensure style_profiles Table Exists & Populate Master Style Entries
CREATE TABLE IF NOT EXISTS public.style_profiles (
    style_profile VARCHAR(50) PRIMARY KEY,
    description TEXT
);

INSERT INTO public.style_profiles (style_profile) VALUES 
('Streetwear'),
('Ethnic Wear'),
('Sports Wear'),
('Casual'),
('Formal'),
('Ethnic'),
('Western')
ON CONFLICT (style_profile) DO NOTHING;

-- 2. Ensure product_master Table Exists
CREATE TABLE IF NOT EXISTS public.product_master (
    sku VARCHAR(50) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    image_url VARCHAR(255)
);

-- 3. Drop Legacy Restrictive Foreign Keys & Check Constraints if They Exist
ALTER TABLE public.product_master DROP CONSTRAINT IF EXISTS product_master_style_profile_fkey;
ALTER TABLE public.product_master DROP CONSTRAINT IF EXISTS product_master_garment_category_check;
ALTER TABLE public.product_master DROP CONSTRAINT IF EXISTS product_master_style_profile_check;
ALTER TABLE public.product_master DROP CONSTRAINT IF EXISTS product_master_garment_type_check;

-- 4. Safely Add Missing Columns to Existing product_master Table
ALTER TABLE public.product_master ADD COLUMN IF NOT EXISTS garment_category VARCHAR(50) DEFAULT 'Topwear';
ALTER TABLE public.product_master ADD COLUMN IF NOT EXISTS garment_type VARCHAR(50) DEFAULT 'Garment';
ALTER TABLE public.product_master ADD COLUMN IF NOT EXISTS style_profile VARCHAR(50) DEFAULT 'Casual';
ALTER TABLE public.product_master ADD COLUMN IF NOT EXISTS color_family VARCHAR(50) DEFAULT 'Blue';
ALTER TABLE public.product_master ADD COLUMN IF NOT EXISTS major_color_hex VARCHAR(10) DEFAULT '#00F5FF';
ALTER TABLE public.product_master ADD COLUMN IF NOT EXISTS pattern VARCHAR(50) DEFAULT 'Solid';
ALTER TABLE public.product_master ADD COLUMN IF NOT EXISTS aisle_location VARCHAR(50) DEFAULT 'Aisle 1';
ALTER TABLE public.product_master ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

-- 5. Ensure inventory_live Table Exists & Has Missing Columns
CREATE TABLE IF NOT EXISTS public.inventory_live (
    epc_id VARCHAR(50) PRIMARY KEY,
    sku VARCHAR(50) NOT NULL
);
ALTER TABLE public.inventory_live ADD COLUMN IF NOT EXISTS store_id VARCHAR(50) DEFAULT 'STORE-001';
ALTER TABLE public.inventory_live ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE public.inventory_live ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- 6. Ensure cart_sessions & cart_items Exist
CREATE TABLE IF NOT EXISTS public.cart_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    store_id VARCHAR(50) DEFAULT 'STORE-001',
    created_at VARCHAR(50),
    updated_at VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    applied_deal_code VARCHAR(50),
    discount_amount DECIMAL(10,2) DEFAULT 0.00
);

CREATE TABLE IF NOT EXISTS public.cart_items (
    session_id VARCHAR(50),
    sku VARCHAR(50),
    name VARCHAR(150),
    price DECIMAL(10,2),
    image_url VARCHAR(255),
    quantity INT DEFAULT 1,
    added_at VARCHAR(50),
    updated_at VARCHAR(50),
    PRIMARY KEY (session_id, sku)
);

-- 7. Seed & Upsert 30 Master Products Data (Using Boolean true for PostgreSQL)
INSERT INTO public.product_master 
(sku, name, price, image_url, garment_category, garment_type, style_profile, color_family, major_color_hex, pattern, aisle_location, is_active)
VALUES
('SKU-KRT-01', 'Men''s Slim Kurta — Blue', 799.00, 'https://assets.retailcart.io/KRT-BLU.webp', 'Topwear', 'Kurta', 'Ethnic Wear', 'Blue', '#1A73E8', 'Solid', 'Aisle 3', true),
('SKU-TRS-02', 'Chino Trousers — Khaki', 1199.00, 'https://assets.retailcart.io/TRS-KHK.webp', 'Bottomwear', 'Trousers', 'Casual', 'Khaki', '#795548', 'Solid', 'Aisle 4', true),
('SKU-SHT-03', 'Cotton Casual Shirt — White', 649.00, 'https://assets.retailcart.io/SHT-WHT.webp', 'Topwear', 'Shirt', 'Casual', 'White', '#F5F5F5', 'Solid', 'Aisle 2', true),
('SKU-SRT-04', 'Cargo Shorts — Olive Green', 899.00, 'https://assets.retailcart.io/SRT-GRN.webp', 'Bottomwear', 'Shorts', 'Streetwear', 'Green', '#388E3C', 'Camouflage', 'Aisle 5', true),
('SKU-JKT-05', 'Classic Denim Jacket — Indigo', 1999.00, 'https://assets.retailcart.io/JKT-IND.webp', 'Topwear', 'Jacket', 'Streetwear', 'Indigo', '#1A1AFF', 'Solid', 'Aisle 1', true),
('SKU-SNK-06', 'White Minimal Sneakers', 1499.00, 'https://assets.retailcart.io/SNK-WHT.webp', 'Footwear', 'Sneakers', 'Casual', 'White', '#FFFFFF', 'Solid', 'Aisle 7', true),
('SKU-HD-01', 'Void Black Oversized Hoodie', 2499.00, 'https://assets.retailcart.io/HD-BLK.webp', 'Topwear', 'Hoodie', 'Streetwear', 'Black', '#111116', 'Graphic Print', 'Aisle 1', true),
('SKU-JOG-04', 'Matte Black Slim Joggers', 1599.00, 'https://assets.retailcart.io/JOG-BLK.webp', 'Bottomwear', 'Joggers', 'Streetwear', 'Black', '#1C1C1E', 'Solid', 'Aisle 4', true),
('SKU-KRT-02', 'Ember Maroon Linen Kurta', 1799.00, 'https://assets.retailcart.io/KRT-MRN.webp', 'Topwear', 'Kurta', 'Ethnic Wear', 'Maroon', '#800020', 'Textured Woven', 'Aisle 3', true),
('SKU-SHR-01', 'Royal Silk Sherwani — Cream', 4999.00, 'https://assets.retailcart.io/SHR-CRM.webp', 'Topwear', 'Sherwani', 'Ethnic Wear', 'Cream', '#FFFDD0', 'Floral Embroidered', 'Aisle 3', true),
('SKU-MOJ-01', 'Gold Embroidered Mojari Shoes', 1899.00, 'https://assets.retailcart.io/MOJ-GLD.webp', 'Footwear', 'Mojari', 'Ethnic Wear', 'Gold', '#FFD700', 'Embroidered', 'Aisle 7', true),
('SKU-TEE-02', 'Compression Dri-FIT Tee — Cyan', 1299.00, 'https://assets.retailcart.io/TEE-CYN.webp', 'Topwear', 'T-Shirt', 'Sports Wear', 'Cyan', '#00F5FF', 'Color-Blocked', 'Aisle 2', true),
('SKU-SRT-02', 'Athletic Running Shorts — Red', 999.00, 'https://assets.retailcart.io/SRT-RED.webp', 'Bottomwear', 'Shorts', 'Sports Wear', 'Red', '#FF3B30', 'Solid', 'Aisle 5', true),
('SKU-TRN-01', 'Performance Pro Trainers — Green', 3299.00, 'https://assets.retailcart.io/TRN-GRN.webp', 'Footwear', 'Trainers', 'Sports Wear', 'Green', '#00E676', 'Mesh Textured', 'Aisle 7', true),
('SKU-SHT-04', 'Oxford Gingham Check Shirt', 1299.00, 'https://assets.retailcart.io/SHT-CHK.webp', 'Topwear', 'Shirt', 'Casual', 'Teal', '#00C4CC', 'Checkered', 'Aisle 2', true),
('SKU-BLZ-01', 'Italian Cut Blazer — Charcoal', 3999.00, 'https://assets.retailcart.io/BLZ-CHR.webp', 'Topwear', 'Blazer', 'Formal', 'Charcoal', '#2E2E34', 'Solid', 'Aisle 6', true),
('SKU-TRS-03', 'Tailored Formal Dress Trousers', 1899.00, 'https://assets.retailcart.io/TRS-BLK.webp', 'Bottomwear', 'Trousers', 'Formal', 'Black', '#0D0D0D', 'Pinstripe', 'Aisle 6', true),
('SKU-OXF-01', 'Classic Leather Oxfords — Brown', 3499.00, 'https://assets.retailcart.io/OXF-BRN.webp', 'Footwear', 'Formal Shoes', 'Formal', 'Brown', '#4A2E16', 'Smooth Leather', 'Aisle 7', true),
('SKU-HAT-01', 'Streetwear Canvas Bucket Hat', 499.00, 'https://assets.retailcart.io/HAT-AMB.webp', 'Accessories', 'Hat', 'Streetwear', 'Amber', '#FFB300', 'Embroidered Logo', 'Aisle 9', true),
('SKU-ACC-02', 'Aviator Gold Sunglasses', 1199.00, 'https://assets.retailcart.io/ACC-GLD.webp', 'Accessories', 'Eyewear', 'Casual', 'Gold', '#FFD700', 'Tinted Lens', 'Aisle 9', true),
('SKU-NHR-01', 'Handloom Nehru Jacket — Ochre', 2199.00, 'https://assets.retailcart.io/NHR-OCH.webp', 'Topwear', 'Nehru Jacket', 'Ethnic Wear', 'Ochre', '#CC7722', 'Woven Texture', 'Aisle 3', true),
('SKU-ANK-01', 'Anarkali Kurti & Dupatta Set', 2799.00, 'https://assets.retailcart.io/ANK-PNK.webp', 'Topwear', 'Kurti', 'Ethnic Wear', 'Pink', '#FF69B4', 'Gota Patti Work', 'Aisle 3', true),
('SKU-SPO-01', 'High-Impact Sports Bra & Leggings', 1999.00, 'https://assets.retailcart.io/SPO-PRP.webp', 'Bottomwear', 'Leggings', 'Sports Wear', 'Purple', '#8A2BE2', 'Color-Blocked', 'Aisle 5', true),
('SKU-TRK-01', 'Zip Track Jacket — Navy Blue', 2299.00, 'https://assets.retailcart.io/TRK-NVY.webp', 'Topwear', 'Track Jacket', 'Sports Wear', 'Navy', '#000080', 'Striped Sleeve', 'Aisle 2', true),
('SKU-CRG-02', 'Tactical Cargo Pants — Black', 2199.00, 'https://assets.retailcart.io/CRG-BLK.webp', 'Bottomwear', 'Cargo Pants', 'Streetwear', 'Black', '#1A1A1A', 'Multi-Pocket', 'Aisle 4', true),
('SKU-SNK-02', 'High-Top Chunky Trainers — Neon', 3799.00, 'https://assets.retailcart.io/SNK-NEO.webp', 'Footwear', 'Sneakers', 'Streetwear', 'Neon', '#39FF14', 'Futuristic Mesh', 'Aisle 7', true),
('SKU-POL-01', 'Pique Cotton Polo Tee — Burgundy', 999.00, 'https://assets.retailcart.io/POL-BUR.webp', 'Topwear', 'Polo', 'Casual', 'Burgundy', '#800020', 'Solid Collar', 'Aisle 2', true),
('SKU-LOF-01', 'Suede Penny Loafers — Tan', 2899.00, 'https://assets.retailcart.io/LOF-TAN.webp', 'Footwear', 'Loafers', 'Casual', 'Tan', '#D2B48C', 'Suede Texture', 'Aisle 7', true),
('SKU-TIE-01', 'Pure Silk Patterned Necktie', 699.00, 'https://assets.retailcart.io/TIE-SIL.webp', 'Accessories', 'Tie', 'Formal', 'Navy', '#1A237E', 'Jacquard Weave', 'Aisle 9', true),
('SKU-BLZ-02', 'Single-Breasted Velvet Tuxedo', 5499.00, 'https://assets.retailcart.io/BLZ-VLV.webp', 'Topwear', 'Tuxedo', 'Formal', 'Black', '#050505', 'Velvet Solid', 'Aisle 6', true)
ON CONFLICT (sku) DO UPDATE SET
name = EXCLUDED.name,
price = EXCLUDED.price,
garment_category = EXCLUDED.garment_category,
style_profile = EXCLUDED.style_profile,
major_color_hex = EXCLUDED.major_color_hex,
pattern = EXCLUDED.pattern,
is_active = EXCLUDED.is_active;

-- 8. Seed & Link UHF RFID Tags in inventory_live Table
INSERT INTO public.inventory_live (epc_id, sku, store_id, is_active)
VALUES
('E280110C', 'SKU-KRT-01', 'STORE-001', true),
('E280110D', 'SKU-TRS-02', 'STORE-001', true),
('E280110E', 'SKU-SHT-03', 'STORE-001', true),
('E280110F', 'SKU-SRT-04', 'STORE-001', true),
('E280110G', 'SKU-JKT-05', 'STORE-001', true),
('E280110H', 'SKU-SNK-06', 'STORE-001', true),
('E280110I', 'SKU-HD-01', 'STORE-001', true),
('E280110J', 'SKU-JOG-04', 'STORE-001', true),
('E280110K', 'SKU-KRT-02', 'STORE-001', true),
('E280110L', 'SKU-SHR-01', 'STORE-001', true),
('E280110M', 'SKU-MOJ-01', 'STORE-001', true),
('E280110N', 'SKU-TEE-02', 'STORE-001', true),
('E280110O', 'SKU-SRT-02', 'STORE-001', true),
('E280110P', 'SKU-TRN-01', 'STORE-001', true),
('E280110Q', 'SKU-SHT-04', 'STORE-001', true),
('E280110R', 'SKU-BLZ-01', 'STORE-001', true),
('E280110S', 'SKU-TRS-03', 'STORE-001', true),
('E280110T', 'SKU-OXF-01', 'STORE-001', true),
('E280110U', 'SKU-HAT-01', 'STORE-001', true),
('E280110V', 'SKU-ACC-02', 'STORE-001', true),
('E280110W', 'SKU-NHR-01', 'STORE-001', true),
('E280110X', 'SKU-ANK-01', 'STORE-001', true),
('E280110Y', 'SKU-SPO-01', 'STORE-001', true),
('E280110Z', 'SKU-TRK-01', 'STORE-001', true),
('E280111A', 'SKU-CRG-02', 'STORE-001', true),
('E280111B', 'SKU-SNK-02', 'STORE-001', true),
('E280111C', 'SKU-POL-01', 'STORE-001', true),
('E280111D', 'SKU-LOF-01', 'STORE-001', true),
('E280111E', 'SKU-TIE-01', 'STORE-001', true),
('E280111F', 'SKU-BLZ-02', 'STORE-001', true)
ON CONFLICT (epc_id) DO UPDATE SET sku = EXCLUDED.sku, is_active = EXCLUDED.is_active;
