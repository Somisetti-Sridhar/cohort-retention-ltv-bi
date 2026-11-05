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


-- RFM segmentation
-- -- -- -- -- -- --
DROP VIEW IF EXISTS v_rfm CASCADE;
CREATE VIEW v_rfm AS
WITH as_of AS (
    SELECT MAX(dd.date) AS d FROM fact_sales f JOIN dim_date dd
    ON dd.date_key = f.date_key
),
cust AS (
    SELECT
        f.customer_key,
        MAX(dd.date)                AS last_purchase,
        COUNT(DISTINCT f.invoice)   AS frequency,
        SUM(f.line_revenue)         AS monetary
    FROM fact_sales f
    JOIN dim_date dd ON dd.date_key = f.date_key
    GROUP BY f.customer_key
),
scored AS (
    SELECT
        c.customer_key,
        ((SELECT d FROM as_of) - c.last_purchase) AS
        recency_days,
        c.frequency,
        c.monetary,
        NTILE(5) OVER (ORDER BY ((SELECT d FROM as_of) - c.last_purchase) DESC) AS r_score,
        NTILE(5) OVER (ORDER BY c.frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY c.monetary ASC) AS m_score
    FROM cust c
)
SELECT
    s.*,
    CASE
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At-Risk'
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN f_score >= 4                  THEN 'Loyal'
        WHEN r_score >= 4                  THEN 'Promising'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
        ELSE 'Needs Attention'
    END AS rfm_segment
FROM scored s;


-- LTV per cohort (and the cumulative curve)
-- -- -- -- -- -- -- -- -- -- -- -- -- -- --
DROP VIEW IF EXISTS v_cohort_ltv CASCADE;
CREATE VIEW v_cohort_ltv AS
WITH rev AS (
    SELECT
        dc.cohort_month,
        (EXTRACT(YEAR FROM dd.date) * 12 + EXTRACT(MONTH FROM dd.date))
        - (EXTRACT(YEAR FROM TO_DATE(dc.cohort_month, 'YYYY-MM')) * 12 + EXTRACT(MONTH FROM TO_DATE(dc.cohort_month, 'YYYY-MM'))) AS month_n,
        f.line_revenue
    FROM fact_sales f
    JOIN dim_customer   dc ON dc.customer_key = f.customer_key
    JOIN dim_date      dd ON dd.date_key = f.date_key
),
by_month AS (
    SELECT cohort_month, month_n::INT AS month_n, SUM(line_revenue) AS revenue
    FROM rev
    GROUP BY cohort_month, month_n
),
sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_key) AS cohort_size
    FROM dim_customer GROUP BY cohort_month
)
SELECT
    b.cohort_month,
    b.month_n,
    s.cohort_size,
    ROUND(b.revenue, 2) AS revenue,
    ROUND(SUM(b.revenue) OVER (PARTITION BY b.cohort_month ORDER BY b.month_n), 2) AS cumulative_revenue,
    ROUND(SUM(b.revenue) OVER (PARTITION BY b.cohort_month ORDER BY b.month_n)
        / NULLIF(s.cohort_size, 0), 2) AS cumulative_ltv_per_customer
    FROM by_month b 
    JOIN sizes s USING (cohort_month);


-- Headline KPIs
-- -- -- -- -- --
DROP VIEW IF EXISTS v_kpis CASCADE;
CREATE VIEW v_kpis AS
SELECT
    ROUND(SUM(line_revenue), 2)     AS total_revenue,
    COUNT(DISTINCT customer_key)    AS distinct_customers,
    COUNT(DISTINCT invoice)         AS orders,
    ROUND(SUM(line_revenue) / NULLIF(COUNT(DISTINCT invoice), 0), 2)                          AS avg_order_value
FROM fact_sales;
