-- schema.sql  — run once:  mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS medcompare
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE medcompare;

-- ── USERS ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(80)  NOT NULL UNIQUE,
    email         VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── MEDICINES (branded, from CDSCO) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS medicines (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    brand_name       VARCHAR(300) NOT NULL,
    salt_composition VARCHAR(500) NOT NULL,
    manufacturer     VARCHAR(300),
    category         VARCHAR(150),
    dosage_form      VARCHAR(100),
    strength         VARCHAR(100),
    source           VARCHAR(50) DEFAULT 'CDSCO',
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_brand (brand_name(100)),
    INDEX idx_salt  (salt_composition(100))
);

-- ── GENERICS (Jan Aushadhi + CDSCO generics) ─────────────────────────────
CREATE TABLE IF NOT EXISTS generics (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    salt_composition   VARCHAR(500) NOT NULL,
    generic_name       VARCHAR(300) NOT NULL,
    manufacturer       VARCHAR(300),
    mrp                DECIMAL(10,2),
    pack_size          VARCHAR(100),
    source             VARCHAR(50),
    jan_aushadhi_code  VARCHAR(50),
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_salt   (salt_composition(100)),
    INDEX idx_source (source)
);

-- ── PRICE CACHE ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS price_cache (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    medicine_id  INT NOT NULL,
    platform     VARCHAR(60) NOT NULL,
    price        DECIMAL(10,2),
    mrp          DECIMAL(10,2),
    discount_pct DECIMAL(5,2),
    product_url  VARCHAR(1000),
    in_stock     TINYINT(1) DEFAULT 1,
    fetched_at   DATETIME NOT NULL,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    INDEX idx_med (medicine_id, platform)
);

-- ── SEARCH HISTORY (per user) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS search_history (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    query       VARCHAR(300),
    searched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
