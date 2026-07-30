-- Migration: Add users table and skin_texture, skin_texture_score, last_login_at columns for Supabase PostgreSQL
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
