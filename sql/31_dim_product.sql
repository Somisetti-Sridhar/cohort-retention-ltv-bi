-- Dim_Product. Category is a light derivation from the description's first token (enough for segmentation)
-- Use proper category tags if using RLT data

TRUNCATE dim_product RESTART IDENTITY CASCADE;

INSERT INTO dim_product (stock_code, description, category)
SELECT
    stock_code,
    MIN(description) as description,
    INITCAP(SPLIT_PART(COALESCE(MIN(description), 'Unknown'), '', 1)) AS category
FROM staging_clean
GROUP BY stock_code;