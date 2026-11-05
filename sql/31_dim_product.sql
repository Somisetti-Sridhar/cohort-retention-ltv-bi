-- Dim_Product. Category is a light derivation from the description's first token (enough for segmentation)
-- Use proper category tags if using RLT data

TRUNCATE dim_product RESTART IDENTITY CASCADE;

INSERT INTO dim_product (stock_code, description, category)
SELECT
    stock_code,
    MIN(description) as description,
    'Unclassified' AS category -- source has no authoritative product taxonomy
FROM staging_clean
GROUP BY stock_code;
