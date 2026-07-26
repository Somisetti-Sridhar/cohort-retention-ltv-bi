-- Analytical views: the SQL equivalents of the DAX measures. For serving on the Streamlit companion app
-- and validation test, and document the exact business logic the PowerBI measures replicate

-- Cohort retention triangle
-- -- -- -- -- -- -- -- -- --
DROP VIEW IF EXISTS v_cohort_retention CASCADE;
CREATE VIEW v_cohort_retention AS
WITH activity AS (
    SELECT
        dc.customer_key,
        dc.cohort_month,
        dd.year_month AS activity_month
    FROM fact_sales f 
    JOIN dim_customer dc ON dc.customer_key = f.customer_key
    JOIN dim_date     dd ON dd.date_key = f.date_key
),
offsets AS (
    SELECT
        cohort_month,
        customer_key,
        (EXTRACT(YEAR FROM TO_DATE(activity_month, 'YYYY-MM')) * 12 
        + EXTRACT(MONTH FROM TO_DATE(activity_month, 'YYYY-MM')))
        - (EXTRACT(YEAR FROM TO_DATE(cohort_month, 'YYYY-MM')) * 12
        + EXTRACT(MONTH FROM TO_DATE(cohort_month, 'YYYY-MM')))
        AS month_n
    FROM activity
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_key) AS cohort_size
    FROM dim_customer
    GROUP BY cohort_month
),
active AS (
    SELECT cohort_month, month_n::INT AS month_n, COUNT(DISTINCT customer_key) AS active_customers
    FROM offsets
    GROUP BY cohort_month, month_n
)
SELECT
    a.cohort_month,
    a.month_n,
    a.active_customers,
    cs.cohort_size,
    ROUND(a.active_customers:: NUMERIC / NULLIF(cs.cohort_size, 0), 4) AS retention_pct
FROM active a 
JOIN cohort_sizes cs USING (cohort_month);
