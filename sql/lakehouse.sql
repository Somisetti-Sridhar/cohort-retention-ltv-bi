-- DuckDB gold layer. Monetary columns are DECIMAL; identities are source scoped.
CREATE OR REPLACE TABLE retail_classified AS
WITH numbered AS (
 SELECT *, row_number() OVER (PARTITION BY invoice,stock_code,description,quantity,invoice_date,price,customer_id,country ORDER BY invoice) AS duplicate_n
 FROM bronze_retail
)
SELECT *, CASE
 WHEN duplicate_n > 1 THEN 'duplicate'
 WHEN invoice IS NULL OR stock_code IS NULL OR invoice_date IS NULL OR price IS NULL OR quantity IS NULL THEN 'invalid'
 WHEN starts_with(invoice,'C') OR quantity < 0 THEN 'return_or_cancellation'
 WHEN quantity <= 0 OR price <= 0 THEN 'nonpositive'
 WHEN customer_id IS NULL THEN 'unattributed_sale'
 ELSE 'attributed_sale' END AS disposition,
 CAST(round(quantity * price,2) AS DECIMAL(18,2)) AS line_revenue
FROM numbered;

CREATE OR REPLACE TABLE fact_lines AS
SELECT 'retail' AS source, 'GBP' AS currency, 'retail:' || CAST(CAST(customer_id AS BIGINT) AS VARCHAR) AS customer_key,
 invoice AS order_id, stock_code AS product_id, invoice_date AS ordered_at,
 CAST(quantity AS DOUBLE) AS quantity, line_revenue AS revenue,
 CAST(0 AS DECIMAL(18,2)) AS retail_discount, CAST(0 AS DECIMAL(18,2)) AS coupon_discount,
 country AS geography, 'unknown' AS store_id, CAST(NULL AS INTEGER) AS week,
 'Unclassified' AS department
FROM retail_classified WHERE disposition='attributed_sale'
UNION ALL
SELECT 'journey','USD','journey:' || CAST(t.household_id AS VARCHAR),CAST(t.basket_id AS VARCHAR),CAST(t.product_id AS VARCHAR),
 t.transaction_timestamp,CAST(t.quantity AS DOUBLE),CAST(t.sales_value AS DECIMAL(18,2)),
 CAST(t.retail_disc AS DECIMAL(18,2)),CAST(t.coupon_disc AS DECIMAL(18,2)),
 'United States',CAST(t.store_id AS VARCHAR),CAST(t.week AS INTEGER),coalesce(p.department,'Unknown')
FROM bronze_transactions t LEFT JOIN bronze_products p USING(product_id)
WHERE t.quantity > 0 AND t.sales_value > 0 AND t.household_id IS NOT NULL
 AND t.basket_id IS NOT NULL AND t.transaction_timestamp IS NOT NULL;

CREATE OR REPLACE TABLE fact_orders AS
SELECT source,currency,customer_key,order_id,min(ordered_at) AS ordered_at,sum(revenue) AS revenue,count(*) AS lines
FROM fact_lines GROUP BY ALL;

CREATE OR REPLACE TABLE dim_customers AS
WITH stats AS (
 SELECT source,currency,customer_key,min(ordered_at) AS first_purchase,max(ordered_at) AS last_purchase,
 count(*) AS orders,sum(revenue) AS revenue FROM fact_orders GROUP BY ALL
), scored AS (
 SELECT *,date_trunc('month',first_purchase)::DATE AS cohort_month,
 date_diff('day',last_purchase,max(last_purchase) OVER (PARTITION BY source)) AS recency_days,
 ntile(5) OVER (PARTITION BY source ORDER BY last_purchase,customer_key) AS r_score,
 ntile(5) OVER (PARTITION BY source ORDER BY orders,customer_key) AS f_score,
 ntile(5) OVER (PARTITION BY source ORDER BY revenue,customer_key) AS m_score
 FROM stats
)
SELECT *,CASE WHEN r_score<=2 AND f_score>=3 THEN 'At risk'
 WHEN r_score>=4 AND f_score>=4 THEN 'Champions' WHEN f_score>=4 THEN 'Loyal'
 WHEN r_score>=4 THEN 'Promising' WHEN r_score<=2 AND f_score<=2 THEN 'Dormant'
 ELSE 'Needs attention' END AS segment FROM scored;

-- Explicit calendar grid: observed zero activity is zero; unobserved future is absent.
CREATE OR REPLACE TABLE mart_cohorts AS
WITH limits AS (SELECT source,max(ordered_at)::DATE AS observed_through FROM fact_orders GROUP BY source),
 sizes AS (SELECT source,currency,cohort_month,count(*) AS cohort_size FROM dim_customers GROUP BY ALL),
 activity AS (
 SELECT o.source,c.cohort_month,date_trunc('month',o.ordered_at)::DATE AS activity_month,
 count(DISTINCT o.customer_key) AS active_customers,sum(o.revenue) AS revenue
 FROM fact_orders o JOIN dim_customers c USING(source,customer_key) GROUP BY ALL
), grid AS (
 SELECT s.*,l.observed_through, CAST(g.month AS DATE) AS activity_month
 FROM sizes s JOIN limits l USING(source),LATERAL generate_series(s.cohort_month,date_trunc('month',l.observed_through),INTERVAL '1 month') g(month)
), monthly AS (
 SELECT g.*,date_diff('month',g.cohort_month,g.activity_month) AS month_n,
 coalesce(a.active_customers,0) AS active_customers,coalesce(a.revenue,0)::DECIMAL(18,2) AS revenue,
 last_day(g.activity_month)<=g.observed_through AS is_complete_month,
 g.cohort_month=(SELECT min(cohort_month) FROM sizes s WHERE s.source=g.source) AS is_left_censored_cohort
 FROM grid g LEFT JOIN activity a USING(source,cohort_month,activity_month)
)
SELECT *,active_customers::DOUBLE/cohort_size AS retention,
 sum(revenue) OVER (PARTITION BY source,cohort_month ORDER BY month_n) / cohort_size AS cumulative_revenue_per_customer
FROM monthly;

CREATE OR REPLACE TABLE mart_monthly AS
SELECT o.source,o.currency,date_trunc('month',o.ordered_at)::DATE AS month,
 count(*) AS orders,count(DISTINCT o.customer_key) AS active_customers,sum(o.revenue) AS revenue,
 sum(CASE WHEN date_trunc('month',o.ordered_at)=c.cohort_month THEN o.revenue ELSE 0 END) AS first_observed_cohort_revenue,
 sum(CASE WHEN date_trunc('month',o.ordered_at)>c.cohort_month THEN o.revenue ELSE 0 END) AS returning_cohort_revenue,
 last_day(date_trunc('month',o.ordered_at)) <= (SELECT max(x.ordered_at)::DATE FROM fact_orders x WHERE x.source=o.source) AS is_complete_month
FROM fact_orders o JOIN dim_customers c USING(source,customer_key) GROUP BY ALL;

CREATE OR REPLACE TABLE mart_segments AS
SELECT source,currency,segment,count(*) AS customers,sum(revenue) AS historical_revenue,
 avg(recency_days) AS mean_recency_days,avg(orders) AS mean_orders FROM dim_customers GROUP BY ALL;

-- 90-day repeat purchase: include only customers with a full 90-day follow-up.
CREATE OR REPLACE TABLE mart_repeat AS
WITH ordered AS (
 SELECT *,row_number() OVER (PARTITION BY source,customer_key ORDER BY ordered_at,order_id) AS purchase_number
 FROM fact_orders
), second AS (
 SELECT source,customer_key,ordered_at AS second_purchase FROM ordered WHERE purchase_number=2
), eligible AS (
 SELECT c.*,s.second_purchase,date_diff('day',c.first_purchase,s.second_purchase) AS days_to_second
 FROM dim_customers c LEFT JOIN second s USING(source,customer_key)
 WHERE c.first_purchase+INTERVAL '90 days' <= (SELECT max(ordered_at) FROM fact_orders o WHERE o.source=c.source)
)
SELECT source,currency,count(*) AS eligible_customers,
 count(*) FILTER(WHERE days_to_second<=90) AS repeated_90d,
 count(*) FILTER(WHERE days_to_second<=90)::DOUBLE/nullif(count(*),0) AS repeat_rate_90d,
 median(days_to_second) FILTER(WHERE days_to_second<=90) AS median_days_to_second_among_repeaters
FROM eligible GROUP BY ALL;

CREATE OR REPLACE TABLE mart_quality AS
SELECT 'retail' AS source,disposition,count(*) AS rows,sum(line_revenue) AS signed_source_value
FROM retail_classified GROUP BY disposition
UNION ALL
SELECT 'journey',CASE WHEN quantity>0 AND sales_value>0 AND household_id IS NOT NULL AND basket_id IS NOT NULL AND transaction_timestamp IS NOT NULL THEN 'attributed_sale' ELSE 'excluded_nonpositive_or_invalid' END,
 count(*),sum(sales_value)::DECIMAL(18,2) FROM bronze_transactions GROUP BY 2;

CREATE OR REPLACE TABLE mart_products AS
SELECT source,currency,department,product_id,count(DISTINCT customer_key) AS customers,
 count(DISTINCT order_id) AS orders,sum(revenue) AS revenue,sum(retail_discount) AS retail_discount,
 sum(coupon_discount) AS coupon_discount FROM fact_lines GROUP BY ALL;

-- Household/campaign assignment is deduplicated BEFORE redemption aggregation.
CREATE OR REPLACE TABLE mart_campaigns AS
WITH assignments AS (SELECT DISTINCT campaign_id,household_id FROM bronze_campaigns),
 redemptions AS (SELECT campaign_id,household_id,count(*) AS redemptions FROM bronze_coupon_redemptions GROUP BY ALL)
SELECT CAST(a.campaign_id AS VARCHAR) AS campaign_id,count(*) AS targeted_households,
 count(r.household_id) AS redeeming_households,coalesce(sum(r.redemptions),0) AS redemptions,
 count(r.household_id)::DOUBLE/count(*) AS household_redemption_rate
FROM assignments a LEFT JOIN redemptions r USING(campaign_id,household_id) GROUP BY a.campaign_id;
