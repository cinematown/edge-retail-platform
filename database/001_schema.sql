-- Edge Retail Platform schema
-- Target: MySQL 8.x

SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS edge_retail
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE edge_retail;

CREATE TABLE products (
    sku VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    unit_price INT UNSIGNED NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE checkouts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    checkout_id VARCHAR(100) NOT NULL,
    event_id VARCHAR(100) NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    tracking_session_id VARCHAR(100) NOT NULL,
    cart_track_id BIGINT NOT NULL,
    payer_track_id BIGINT NOT NULL,
    total_item_count INT UNSIGNED NOT NULL,
    total_amount INT UNSIGNED NOT NULL,
    completed_at DATETIME(3) NOT NULL,
    received_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    UNIQUE KEY uk_checkouts_checkout_id (checkout_id),
    UNIQUE KEY uk_checkouts_event_id (event_id),
    INDEX idx_checkouts_completed_at (completed_at),
    INDEX idx_checkouts_device_time (device_id, completed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE checkout_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    checkout_id VARCHAR(100) NOT NULL,
    sku VARCHAR(50) NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    unit_price INT UNSIGNED NOT NULL,
    subtotal_amount INT UNSIGNED NOT NULL,
    confidence DECIMAL(5,4),
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT fk_checkout_items_checkout
        FOREIGN KEY (checkout_id)
        REFERENCES checkouts(checkout_id),

    CONSTRAINT fk_checkout_items_product
        FOREIGN KEY (sku)
        REFERENCES products(sku),

    INDEX idx_checkout_items_checkout_id (checkout_id),
    INDEX idx_checkout_items_sku (sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE device_status (
    device_id VARCHAR(50) PRIMARY KEY,
    status ENUM('ONLINE', 'OFFLINE', 'ERROR') NOT NULL,
    model_version VARCHAR(100),
    tracking_session_id VARCHAR(100),
    last_seen_at DATETIME(3) NOT NULL,
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
