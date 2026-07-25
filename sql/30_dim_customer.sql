-- Dim_Customer with the derived acquisition fields that power cohorts:
--  first_purchase_date  = the customer's earliest clean order,
--  cohort_month         = 'YYYY-MM' of that first purchase (the cohort label).

TRUNCATE dim_customer RESTART IDENTITY CASCADE;

INSERT INTO dim_customer (customer_id, country, first_purchase_date, cohort_month)
SELECT
    c.customer_id,
    -- a customer can appear with one country in this dataset; take the modal/first.
    MIN(c.country)                                              AS country,
    MIN(c.invoice_date_only)                                    AS first_purchase_date,
    TO_CHAR(MIN(c.invoice_date_only), 'YYYY-MM')               AS cohort_month
FROM staging_clean c
GROUP BY c.customer_id;