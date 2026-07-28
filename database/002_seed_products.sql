-- Initial product catalog for local development and MVP verification.
SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE edge_retail;

INSERT INTO products (sku, product_name, unit_price)
VALUES
    ('cola_can', '콜라 캔', 1500),
    ('water_bottle', '생수', 1000),
    ('snack_red', '빨간 과자', 2000),
    ('snack_blue', '파란 과자', 2200);
