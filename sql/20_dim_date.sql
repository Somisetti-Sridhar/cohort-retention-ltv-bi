-- Continious calender covering the data range. A complete Date dimension is what enables
-- time-intelligence DAX in PowerBI (it must be marked as the Date table)

TRUNCATE dim_date CASCADE;

INSERT INTO dim_date (date_key, date, year, quarter, month, month_name, day, day_of_week,
                      is_weekday, year_month)
SELECT
    CAST(TO_CHAR(d, 'YYYYMMDD') AS INTEGER)        AS date_key,
    d::DATE                                         AS date,
    EXTRACT(YEAR FROM d)::INT                       AS year,
    EXTRACT(QUARTER FROM d)::INT                    AS quarter,
    EXTRACT(MONTH FROM d)::INT                      AS month,
    TO_CHAR(d, 'Mon')                              AS month_name,
    EXTRACT(DAY FROM d)::INT                        AS day,
    EXTRACT(ISODOW FROM d)::INT                     AS day_of_week,
    EXTRACT(ISODOW FROM d) < 6                      AS is_weekday,
    TO_CHAR(d, 'YYYY-MM')                          AS year_month
FROM generate_series(
        (SELECT MIN(invoice_date_only) FROM staging_clean),
        (SELECT MAX(invoice_date_only) FROM staging_clean),
        INTERVAL '1 day'
     ) AS d;