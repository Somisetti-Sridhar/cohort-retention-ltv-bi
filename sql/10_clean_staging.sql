-- Cleanse layer: staging_raw -> staging_clean.
-- Rules 
--      * Drop rows with no customer_id (cannot attribute to a cohort),
--      * drop cancellations: invoices starting with 'C', or non-positive quantity/price,
--      * de-duplicate identical order lines,
--      * cast customer_id to a clean integer and compute line_revenue = quantity * price.

DROP TABLE IF EXISTS staging_clean;

CREATE TABLE staging_clean AS
with filtered AS (
    SELECT
        invoice,
        stock_code,
        NULLIF(TRIM(description), '') AS description,
        quantity,
        invoice_date,
        price,
        CAST(customer_id AS BIGINT) as customer_id,
        COALESCE(NULLIF(TRIM(country), ''), 'Unspecified') as country
    FROM staging_raw
    WHERE customer_id IS NOT NULL
     AND quantity > 0
     AND price > 0
     AND invoice NOT LIKE 'C%'
),
deduped AS (
    SELECT DISTINCT
        invoice, stock_code, description, quantity, invoice_date, price, customer_id, country
    FROM filtered
)
SELECT
    invoice,
    stock_code,
    description,
    quantity,
    invoice_date,
    CAST(invoice_date AS DATE) AS invoice_date_only,
    price,
    customer_id,
    country,
    ROUND(quantity * price, 2) as line_revenue
from deduped;