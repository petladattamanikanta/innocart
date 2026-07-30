import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("innocart.supabase_seed")

# Supabase Connection Parameters from environment or default
SUPABASE_HOST = os.getenv("MYSQL_HOST", "aws-0-ap-southeast-2.pooler.supabase.com")
SUPABASE_PORT = int(os.getenv("MYSQL_PORT", "6543"))
SUPABASE_USER = os.getenv("MYSQL_USER", "postgres.uczulnmdbsslqqgxnbyd")
SUPABASE_PASSWORD = os.getenv("MYSQL_PASSWORD", "Somanathi@7463")
SUPABASE_DB = os.getenv("MYSQL_DB", "postgres")

# 30 Master Products Dataset
MASTER_PRODUCTS_DATA = [
    {
        "sku": "SKU-KRT-01", "name": "Men's Slim Kurta — Blue", "price": 799.0,
        "image_url": "https://assets.retailcart.io/KRT-BLU.webp", "garment_category": "Topwear", "garment_type": "Kurta",
        "style_profile": "Ethnic Wear", "color_family": "Blue", "major_color_hex": "#1A73E8", "pattern": "Solid", "aisle_location": "Aisle 3", "epc_id": "E280110C"
    },
    {
        "sku": "SKU-TRS-02", "name": "Chino Trousers — Khaki", "price": 1199.0,
        "image_url": "https://assets.retailcart.io/TRS-KHK.webp", "garment_category": "Bottomwear", "garment_type": "Trousers",
        "style_profile": "Casual", "color_family": "Khaki", "major_color_hex": "#795548", "pattern": "Solid", "aisle_location": "Aisle 4", "epc_id": "E280110D"
    },
    {
        "sku": "SKU-SHT-03", "name": "Cotton Casual Shirt — White", "price": 649.0,
        "image_url": "https://assets.retailcart.io/SHT-WHT.webp", "garment_category": "Topwear", "garment_type": "Shirt",
        "style_profile": "Casual", "color_family": "White", "major_color_hex": "#F5F5F5", "pattern": "Solid", "aisle_location": "Aisle 2", "epc_id": "E280110E"
    },
    {
        "sku": "SKU-SRT-04", "name": "Cargo Shorts — Olive Green", "price": 899.0,
        "image_url": "https://assets.retailcart.io/SRT-GRN.webp", "garment_category": "Bottomwear", "garment_type": "Shorts",
        "style_profile": "Streetwear", "color_family": "Green", "major_color_hex": "#388E3C", "pattern": "Camouflage", "aisle_location": "Aisle 5", "epc_id": "E280110F"
    },
    {
        "sku": "SKU-JKT-05", "name": "Classic Denim Jacket — Indigo", "price": 1999.0,
        "image_url": "https://assets.retailcart.io/JKT-IND.webp", "garment_category": "Topwear", "garment_type": "Jacket",
        "style_profile": "Streetwear", "color_family": "Indigo", "major_color_hex": "#1A1AFF", "pattern": "Solid", "aisle_location": "Aisle 1", "epc_id": "E280110G"
    },
    {
        "sku": "SKU-SNK-06", "name": "White Minimal Sneakers", "price": 1499.0,
        "image_url": "https://assets.retailcart.io/SNK-WHT.webp", "garment_category": "Footwear", "garment_type": "Sneakers",
        "style_profile": "Casual", "color_family": "White", "major_color_hex": "#FFFFFF", "pattern": "Solid", "aisle_location": "Aisle 7", "epc_id": "E280110H"
    },
    {
        "sku": "SKU-HD-01", "name": "Void Black Oversized Hoodie", "price": 2499.0,
        "image_url": "https://assets.retailcart.io/HD-BLK.webp", "garment_category": "Topwear", "garment_type": "Hoodie",
        "style_profile": "Streetwear", "color_family": "Black", "major_color_hex": "#111116", "pattern": "Graphic Print", "aisle_location": "Aisle 1", "epc_id": "E280110I"
    },
    {
        "sku": "SKU-JOG-04", "name": "Matte Black Slim Joggers", "price": 1599.0,
        "image_url": "https://assets.retailcart.io/JOG-BLK.webp", "garment_category": "Bottomwear", "garment_type": "Joggers",
        "style_profile": "Streetwear", "color_family": "Black", "major_color_hex": "#1C1C1E", "pattern": "Solid", "aisle_location": "Aisle 4", "epc_id": "E280110J"
    },
    {
        "sku": "SKU-KRT-02", "name": "Ember Maroon Linen Kurta", "price": 1799.0,
        "image_url": "https://assets.retailcart.io/KRT-MRN.webp", "garment_category": "Topwear", "garment_type": "Kurta",
        "style_profile": "Ethnic Wear", "color_family": "Maroon", "major_color_hex": "#800020", "pattern": "Textured Woven", "aisle_location": "Aisle 3", "epc_id": "E280110K"
    },
    {
        "sku": "SKU-SHR-01", "name": "Royal Silk Sherwani — Cream", "price": 4999.0,
        "image_url": "https://assets.retailcart.io/SHR-CRM.webp", "garment_category": "Topwear", "garment_type": "Sherwani",
        "style_profile": "Ethnic Wear", "color_family": "Cream", "major_color_hex": "#FFFDD0", "pattern": "Floral Embroidered", "aisle_location": "Aisle 3", "epc_id": "E280110L"
    },
    {
        "sku": "SKU-MOJ-01", "name": "Gold Embroidered Mojari Shoes", "price": 1899.0,
        "image_url": "https://assets.retailcart.io/MOJ-GLD.webp", "garment_category": "Footwear", "garment_type": "Mojari",
        "style_profile": "Ethnic Wear", "color_family": "Gold", "major_color_hex": "#FFD700", "pattern": "Embroidered", "aisle_location": "Aisle 7", "epc_id": "E280110M"
    },
    {
        "sku": "SKU-TEE-02", "name": "Compression Dri-FIT Tee — Cyan", "price": 1299.0,
        "image_url": "https://assets.retailcart.io/TEE-CYN.webp", "garment_category": "Topwear", "garment_type": "T-Shirt",
        "style_profile": "Sports Wear", "color_family": "Cyan", "major_color_hex": "#00F5FF", "pattern": "Color-Blocked", "aisle_location": "Aisle 2", "epc_id": "E280110N"
    },
    {
        "sku": "SKU-SRT-02", "name": "Athletic Running Shorts — Red", "price": 999.0,
        "image_url": "https://assets.retailcart.io/SRT-RED.webp", "garment_category": "Bottomwear", "garment_type": "Shorts",
        "style_profile": "Sports Wear", "color_family": "Red", "major_color_hex": "#FF3B30", "pattern": "Solid", "aisle_location": "Aisle 5", "epc_id": "E280110O"
    },
    {
        "sku": "SKU-TRN-01", "name": "Performance Pro Trainers — Green", "price": 3299.0,
        "image_url": "https://assets.retailcart.io/TRN-GRN.webp", "garment_category": "Footwear", "garment_type": "Trainers",
        "style_profile": "Sports Wear", "color_family": "Green", "major_color_hex": "#00E676", "pattern": "Mesh Textured", "aisle_location": "Aisle 7", "epc_id": "E280110P"
    },
    {
        "sku": "SKU-SHT-04", "name": "Oxford Gingham Check Shirt", "price": 1299.0,
        "image_url": "https://assets.retailcart.io/SHT-CHK.webp", "garment_category": "Topwear", "garment_type": "Shirt",
        "style_profile": "Casual", "color_family": "Teal", "major_color_hex": "#00C4CC", "pattern": "Checkered", "aisle_location": "Aisle 2", "epc_id": "E280110Q"
    },
    {
        "sku": "SKU-BLZ-01", "name": "Italian Cut Blazer — Charcoal", "price": 3999.0,
        "image_url": "https://assets.retailcart.io/BLZ-CHR.webp", "garment_category": "Topwear", "garment_type": "Blazer",
        "style_profile": "Formal", "color_family": "Charcoal", "major_color_hex": "#2E2E34", "pattern": "Solid", "aisle_location": "Aisle 6", "epc_id": "E280110R"
    },
    {
        "sku": "SKU-TRS-03", "name": "Tailored Formal Dress Trousers", "price": 1899.0,
        "image_url": "https://assets.retailcart.io/TRS-BLK.webp", "garment_category": "Bottomwear", "garment_type": "Trousers",
        "style_profile": "Formal", "color_family": "Black", "major_color_hex": "#0D0D0D", "pattern": "Pinstripe", "aisle_location": "Aisle 6", "epc_id": "E280110S"
    },
    {
        "sku": "SKU-OXF-01", "name": "Classic Leather Oxfords — Brown", "price": 3499.0,
        "image_url": "https://assets.retailcart.io/OXF-BRN.webp", "garment_category": "Footwear", "garment_type": "Formal Shoes",
        "style_profile": "Formal", "color_family": "Brown", "major_color_hex": "#4A2E16", "pattern": "Smooth Leather", "aisle_location": "Aisle 7", "epc_id": "E280110T"
    },
    {
        "sku": "SKU-HAT-01", "name": "Streetwear Canvas Bucket Hat", "price": 499.0,
        "image_url": "https://assets.retailcart.io/HAT-AMB.webp", "garment_category": "Accessories", "garment_type": "Hat",
        "style_profile": "Streetwear", "color_family": "Amber", "major_color_hex": "#FFB300", "pattern": "Embroidered Logo", "aisle_location": "Aisle 9", "epc_id": "E280110U"
    },
    {
        "sku": "SKU-ACC-02", "name": "Aviator Gold Sunglasses", "price": 1199.0,
        "image_url": "https://assets.retailcart.io/ACC-GLD.webp", "garment_category": "Accessories", "garment_type": "Eyewear",
        "style_profile": "Casual", "color_family": "Gold", "major_color_hex": "#FFD700", "pattern": "Tinted Lens", "aisle_location": "Aisle 9", "epc_id": "E280110V"
    },
    {
        "sku": "SKU-NHR-01", "name": "Handloom Nehru Jacket — Ochre", "price": 2199.0,
        "image_url": "https://assets.retailcart.io/NHR-OCH.webp", "garment_category": "Topwear", "garment_type": "Nehru Jacket",
        "style_profile": "Ethnic Wear", "color_family": "Ochre", "major_color_hex": "#CC7722", "pattern": "Woven Texture", "aisle_location": "Aisle 3", "epc_id": "E280110W"
    },
    {
        "sku": "SKU-ANK-01", "name": "Anarkali Kurti & Dupatta Set", "price": 2799.0,
        "image_url": "https://assets.retailcart.io/ANK-PNK.webp", "garment_category": "Topwear", "garment_type": "Kurti",
        "style_profile": "Ethnic Wear", "color_family": "Pink", "major_color_hex": "#FF69B4", "pattern": "Gota Patti Work", "aisle_location": "Aisle 3", "epc_id": "E280110X"
    },
    {
        "sku": "SKU-SPO-01", "name": "High-Impact Sports Bra & Leggings", "price": 1999.0,
        "image_url": "https://assets.retailcart.io/SPO-PRP.webp", "garment_category": "Bottomwear", "garment_type": "Leggings",
        "style_profile": "Sports Wear", "color_family": "Purple", "major_color_hex": "#8A2BE2", "pattern": "Color-Blocked", "aisle_location": "Aisle 5", "epc_id": "E280110Y"
    },
    {
        "sku": "SKU-TRK-01", "name": "Zip Track Jacket — Navy Blue", "price": 2299.0,
        "image_url": "https://assets.retailcart.io/TRK-NVY.webp", "garment_category": "Topwear", "garment_type": "Track Jacket",
        "style_profile": "Sports Wear", "color_family": "Navy", "major_color_hex": "#000080", "pattern": "Striped Sleeve", "aisle_location": "Aisle 2", "epc_id": "E280110Z"
    },
    {
        "sku": "SKU-CRG-02", "name": "Tactical Cargo Pants — Black", "price": 2199.0,
        "image_url": "https://assets.retailcart.io/CRG-BLK.webp", "garment_category": "Bottomwear", "garment_type": "Cargo Pants",
        "style_profile": "Streetwear", "color_family": "Black", "major_color_hex": "#1A1A1A", "pattern": "Multi-Pocket", "aisle_location": "Aisle 4", "epc_id": "E280111A"
    },
    {
        "sku": "SKU-SNK-02", "name": "High-Top Chunky Trainers — Neon", "price": 3799.0,
        "image_url": "https://assets.retailcart.io/SNK-NEO.webp", "garment_category": "Footwear", "garment_type": "Sneakers",
        "style_profile": "Streetwear", "color_family": "Neon", "major_color_hex": "#39FF14", "pattern": "Futuristic Mesh", "aisle_location": "Aisle 7", "epc_id": "E280111B"
    },
    {
        "sku": "SKU-POL-01", "name": "Pique Cotton Polo Tee — Burgundy", "price": 999.0,
        "image_url": "https://assets.retailcart.io/POL-BUR.webp", "garment_category": "Topwear", "garment_type": "Polo",
        "style_profile": "Casual", "color_family": "Burgundy", "major_color_hex": "#800020", "pattern": "Solid Collar", "aisle_location": "Aisle 2", "epc_id": "E280111C"
    },
    {
        "sku": "SKU-LOF-01", "name": "Suede Penny Loafers — Tan", "price": 2899.0,
        "image_url": "https://assets.retailcart.io/LOF-TAN.webp", "garment_category": "Footwear", "garment_type": "Loafers",
        "style_profile": "Casual", "color_family": "Tan", "major_color_hex": "#D2B48C", "pattern": "Suede Texture", "aisle_location": "Aisle 7", "epc_id": "E280111D"
    },
    {
        "sku": "SKU-TIE-01", "name": "Pure Silk Patterned Necktie", "price": 699.0,
        "image_url": "https://assets.retailcart.io/TIE-SIL.webp", "garment_category": "Accessories", "garment_type": "Tie",
        "style_profile": "Formal", "color_family": "Navy", "major_color_hex": "#1A237E", "pattern": "Jacquard Weave", "aisle_location": "Aisle 9", "epc_id": "E280111E"
    },
    {
        "sku": "SKU-BLZ-02", "name": "Single-Breasted Velvet Tuxedo", "price": 5499.0,
        "image_url": "https://assets.retailcart.io/BLZ-VLV.webp", "garment_category": "Topwear", "garment_type": "Tuxedo",
        "style_profile": "Formal", "color_family": "Black", "major_color_hex": "#050505", "pattern": "Velvet Solid", "aisle_location": "Aisle 6", "epc_id": "E280111F"
    }
]

def seed_supabase():
    print(f"Connecting to Supabase PostgreSQL at {SUPABASE_HOST}:{SUPABASE_PORT}...")
    try:
        conn = psycopg2.connect(
            host=SUPABASE_HOST,
            port=SUPABASE_PORT,
            user=SUPABASE_USER,
            password=SUPABASE_PASSWORD,
            dbname=SUPABASE_DB,
            sslmode="require",
            connect_timeout=10
        )
        cursor = conn.cursor()
        print("[SUCCESS] Connected to Supabase PostgreSQL database successfully!")

        # 1. Create product_master table in PostgreSQL
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_master (
                sku VARCHAR(50) PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                image_url VARCHAR(255),
                garment_category VARCHAR(50) NOT NULL DEFAULT 'Topwear',
                garment_type VARCHAR(50) NOT NULL DEFAULT 'Garment',
                style_profile VARCHAR(50) NOT NULL DEFAULT 'Casual',
                color_family VARCHAR(50) DEFAULT 'Blue',
                major_color_hex VARCHAR(10) NOT NULL DEFAULT '#00F5FF',
                pattern VARCHAR(50) NOT NULL DEFAULT 'Solid',
                aisle_location VARCHAR(50) DEFAULT 'Aisle 1',
                is_active BOOLEAN DEFAULT TRUE
            );
            ALTER TABLE product_master ADD COLUMN IF NOT EXISTS image_url VARCHAR(255);
            ALTER TABLE product_master ADD COLUMN IF NOT EXISTS garment_category VARCHAR(50) DEFAULT 'Topwear';
            ALTER TABLE product_master ADD COLUMN IF NOT EXISTS garment_type VARCHAR(50) DEFAULT 'Garment';
            ALTER TABLE product_master ADD COLUMN IF NOT EXISTS style_profile VARCHAR(50) DEFAULT 'Casual';
            ALTER TABLE product_master ADD COLUMN IF NOT EXISTS color_family VARCHAR(50) DEFAULT 'Blue';
            ALTER TABLE product_master ADD COLUMN IF NOT EXISTS major_color_hex VARCHAR(10) DEFAULT '#00F5FF';
            ALTER TABLE product_master ADD COLUMN IF NOT EXISTS pattern VARCHAR(50) DEFAULT 'Solid';
            ALTER TABLE product_master ADD COLUMN IF NOT EXISTS aisle_location VARCHAR(50) DEFAULT 'Aisle 1';
            ALTER TABLE product_master ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
            ALTER TABLE product_master DROP CONSTRAINT IF EXISTS product_master_style_profile_fkey;
            ALTER TABLE product_master DROP CONSTRAINT IF EXISTS product_master_color_family_fkey;
            ALTER TABLE product_master DROP CONSTRAINT IF EXISTS product_master_garment_category_fkey;
            ALTER TABLE product_master DROP CONSTRAINT IF EXISTS product_master_garment_type_fkey;
            ALTER TABLE product_master DROP CONSTRAINT IF EXISTS product_master_pattern_fkey;
            ALTER TABLE product_master DROP CONSTRAINT IF EXISTS product_master_garment_category_check;
            ALTER TABLE product_master DROP CONSTRAINT IF EXISTS product_master_garment_type_check;
            ALTER TABLE product_master DROP CONSTRAINT IF EXISTS product_master_style_profile_check;
        """)

        # 2. Create inventory_live table in PostgreSQL
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_live (
                epc_id VARCHAR(50) PRIMARY KEY,
                sku VARCHAR(50) NOT NULL,
                store_id VARCHAR(50) DEFAULT 'STORE-001',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Create cart_sessions & cart_items tables in PostgreSQL
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_sessions (
                session_id VARCHAR(50) PRIMARY KEY,
                store_id VARCHAR(50) DEFAULT 'STORE-001',
                created_at VARCHAR(50),
                updated_at VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                applied_deal_code VARCHAR(50),
                discount_amount DECIMAL(10,2) DEFAULT 0.00,
                phone VARCHAR(50),
                name VARCHAR(150)
            );
            ALTER TABLE cart_sessions ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
            ALTER TABLE cart_sessions ADD COLUMN IF NOT EXISTS name VARCHAR(150);
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
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
        """)

        # 4. Create users table in PostgreSQL / Supabase
        cursor.execute("""
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
            ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ DEFAULT NULL;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS skin_texture VARCHAR(50) NOT NULL DEFAULT 'Smooth & Uniform';
            ALTER TABLE users ADD COLUMN IF NOT EXISTS skin_texture_score FLOAT NOT NULL DEFAULT 0.85;
        """)

        conn.commit()
        print("[SUCCESS] Created tables 'product_master', 'inventory_live', 'cart_sessions', 'cart_items', 'users' in Supabase.")

        # 4. Insert/Upsert 30 Master Products
        inserted_count = 0
        for p in MASTER_PRODUCTS_DATA:
            upsert_sql = """
                INSERT INTO product_master 
                (sku, name, price, image_url, garment_category, garment_type, style_profile, color_family, major_color_hex, pattern, aisle_location, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (sku) DO UPDATE SET
                name = EXCLUDED.name,
                price = EXCLUDED.price,
                garment_category = EXCLUDED.garment_category,
                style_profile = EXCLUDED.style_profile,
                major_color_hex = EXCLUDED.major_color_hex,
                pattern = EXCLUDED.pattern;
            """
            cursor.execute(upsert_sql, (
                p["sku"], p["name"], p["price"], p["image_url"], p["garment_category"], p["garment_type"],
                p["style_profile"], p["color_family"], p["major_color_hex"], p["pattern"], p["aisle_location"]
            ))

            inv_sql = """
                INSERT INTO inventory_live (epc_id, sku, store_id, is_active)
                VALUES (%s, %s, 'STORE-001', TRUE)
                ON CONFLICT (epc_id) DO UPDATE SET sku = EXCLUDED.sku, is_active = TRUE;
            """
            cursor.execute(inv_sql, (p["epc_id"], p["sku"]))
            inserted_count += 1

        conn.commit()
        print(f"[SUCCESS] Successfully seeded {inserted_count} master garments into Supabase PostgreSQL!")
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] Supabase seeding error: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_supabase()
