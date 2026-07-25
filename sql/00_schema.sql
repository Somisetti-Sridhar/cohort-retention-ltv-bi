-- Star-schema warehouse DDL. Idempotent: drops and recreates every table so a refresh is a clean,
-- repeatable rebuild. Money is NUMERIC (never float); dates are real DATE/TIMESTAMP types/

DROP TABLE IF EXISTS fact_sales CASCADE;
DROP TABLE IF EXISTS dim_customer CASCADE;
DROP TABLE IF EXISTS dim_product CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE if EXISTS staging_clean CASCADE;
DROP TABLE if EXISTS staging_raw CASCADE;

-- Raw loading zone (loaded as-is by the python loader, then cleansed in SQL).
CREATE TABLE staging_raw (
    invoice TEXT,
    stock_code TEXT,
    description TEXT,
    quantity INTEGER,
    invoice_date TIMESTAMP,
    price NUMERIC(12, 4),
    customer_id DOUBLE PRECISION,
    country TEXT
);

-- Dimensions
-- -- -- -- -- -- -- -- --
CREATE TABLE dim_date (
    date_key    INTEGER PRIMARY KEY,        -- yyyymmdd
    date        DATE NOT NULL,
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    month_name  TEXT NOT NULL,
    day         INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,           -- 1=Mon, 7=Sat
    is_weekday  BOOLEAN NOT NULL,
    year_month TEXT NOT NULL               -- 'YYYY-MM' for cohort joins
);

CREATE TABLE dim_customer (
    customer_key        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id         BIGINT UNIQUE NOT NULL,
    country             TEXT,
    first_purchase_date DATE,
    cohort_month        TEXT                -- 'YYYY-MM' of first purchase
);

CREATE TABLE dim_product(
    product_key         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stock_code          TEXT UNIQUE NOT NULL,
    description         TEXT,
    category            TEXT
);


-- Fact (grain = one order line)
-- -- -- -- -- -- -- -- -- -- -- 
CREATE TABLE fact_sales (
    sales_key       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice         TEXT NOT NULL,
    customer_key    INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    date_key        INTEGER NOT NULL REFERENCES dim_date(date_key),
    product_key     INTEGER NOT NULL REFERENCES dim_product(product_key),
    quantity        INTEGER NOT NULL,
    unit_price      NUMERIC(12, 4) NOT NULL,
    line_revenue    NUMERIC(14, 2) NOT NULL
);

-- Create Indexes
CREATE INDEX ix_fact_customer ON fact_sales(customer_key);
CREATE INDEX ix_fact_date     ON fact_sales(date_key);
CREATE INDEX ix_fact_product  ON fact_sales(product_key);
CREATE INDEX ix_customer_cohort ON dim_customer(cohort_month);