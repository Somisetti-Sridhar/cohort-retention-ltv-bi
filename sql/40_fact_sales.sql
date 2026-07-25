-- Fact Sales ar order-line grain, joined to dimension surrogate keys(star, not snowflake).

TRUNCATE fact_sales RESTART IDENTITY;

INSERT INTO fact_sales (invoice, customer_key, date_key, product_key, quantity, unit_price, line_revenue)
SELECT
    s.invoice,
    dc.customer_key,
    CAST(TO_CHAR(s.invoice_date_only, 'YYYYMMDD') AS INTEGER)
    AS date_key,
    dp.product_key,
    s.quantity,
    s.price,
    s.line_revenue
FROM staging_clean s
JOIN dim_customer dc ON dc.customer_id = s.customer_id
JOIN dim_product  dp ON dp.stock_code  = s.stock_code
JOIN dim_date     dd ON dd.date_key    = CAST(TO_CHAR(s.invoice_date_only, 'YYYYMMDD') AS INTEGER);    