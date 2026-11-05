"""Hand-calculated regression cases are test fixtures, never analytical report data."""

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from ltv.data_source import load_raw
from ltv.lakehouse import SQL


@pytest.fixture
def db():
    con = duckdb.connect()
    con.execute("""
    CREATE TABLE bronze_retail(invoice VARCHAR,stock_code VARCHAR,description VARCHAR,quantity INTEGER,invoice_date TIMESTAMP,price DOUBLE,customer_id DOUBLE,country VARCHAR);
    INSERT INTO bronze_retail VALUES
    ('a','x','Item',1,'2010-01-01',100,1,'UK'),
    ('a','x','Item',1,'2010-01-01',100,1,'UK'),
    ('b','x','Item',1,'2010-03-01',50,1,'UK'),
    ('c','x','Item',1,'2010-04-30',200,2,'UK'),
    ('C1','x','Item',-1,'2010-03-01',50,1,'UK'),
    ('anon','x','Item',1,'2010-02-01',40,NULL,'UK');
    CREATE TABLE bronze_transactions(household_id VARCHAR,store_id VARCHAR,basket_id VARCHAR,product_id VARCHAR,quantity DOUBLE,sales_value DOUBLE,retail_disc DOUBLE,coupon_disc DOUBLE,week INTEGER,transaction_timestamp TIMESTAMP);
    INSERT INTO bronze_transactions VALUES ('1','s','j1','p',1,10,2,1,1,'2017-01-01'),('1','s','j2','p',1,20,0,0,14,'2017-04-30');
    CREATE TABLE bronze_products(product_id VARCHAR,department VARCHAR);
    INSERT INTO bronze_products VALUES ('p','Food');
    CREATE TABLE bronze_campaigns(campaign_id VARCHAR,household_id VARCHAR);
    INSERT INTO bronze_campaigns VALUES ('c','1'),('c','1'),('c','2');
    CREATE TABLE bronze_coupon_redemptions(campaign_id VARCHAR,household_id VARCHAR);
    INSERT INTO bronze_coupon_redemptions VALUES ('c','1'),('c','1');
    """)
    con.execute(SQL.read_text())
    yield con
    con.close()


def test_missing_source_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError, match="Real data missing"):
        load_raw(tmp_path / "absent.csv")


def test_observed_zero_and_future_absent(db):
    assert db.execute(
        "SELECT active_customers,retention FROM mart_cohorts WHERE source='retail' AND cohort_month='2010-01-01' AND month_n=1"
    ).fetchone() == (0, 0)
    assert (
        db.execute(
            "SELECT count(*) FROM mart_cohorts WHERE source='retail' AND cohort_month='2010-04-01' AND month_n>0"
        ).fetchone()[0]
        == 0
    )


def test_ltv_carries_through_empty_month(db):
    values = db.execute(
        "SELECT cumulative_revenue_per_customer FROM mart_cohorts WHERE source='retail' AND cohort_month='2010-01-01' ORDER BY month_n"
    ).fetchall()
    assert [float(x[0]) for x in values] == [100, 100, 150, 150]


def test_dispositions_and_money(db):
    assert db.execute("SELECT count(*) FROM fact_lines WHERE source='retail'").fetchone()[0] == 3
    assert (
        float(db.execute("SELECT sum(revenue) FROM fact_lines WHERE source='retail'").fetchone()[0])
        == 350
    )
    assert db.execute("SELECT sum(rows) FROM mart_quality WHERE source='retail'").fetchone()[0] == 6
    assert (
        float(
            db.execute("SELECT sum(revenue) FROM fact_lines WHERE source='journey'").fetchone()[0]
        )
        == 30
    )  # discounts not subtracted twice


def test_identity_and_campaign_fanout(db):
    assert db.execute("SELECT count(*) FROM dim_customers").fetchone()[0] == 3
    assert db.execute(
        "SELECT targeted_households,redeeming_households,redemptions FROM mart_campaigns"
    ).fetchone() == (2, 1, 2)


def test_90_day_followup_denominator(db):
    assert db.execute(
        "SELECT eligible_customers,repeated_90d FROM mart_repeat WHERE source='retail'"
    ).fetchone() == (1, 1)
    assert db.execute(
        "SELECT eligible_customers,repeated_90d FROM mart_repeat WHERE source='journey'"
    ).fetchone() == (1, 0)


def test_rebuild_is_idempotent(db):
    before = db.execute("SELECT * FROM mart_cohorts ORDER BY ALL").fetchall()
    db.execute(SQL.read_text())
    assert before == db.execute("SELECT * FROM mart_cohorts ORDER BY ALL").fetchall()


def test_incomplete_month_flag(db):
    db.execute("UPDATE bronze_retail SET invoice_date='2010-04-09' WHERE invoice='c'")
    db.execute(SQL.read_text())
    assert (
        db.execute(
            "SELECT bool_or(is_complete_month) FROM mart_cohorts WHERE source='retail' AND activity_month='2010-04-01'"
        ).fetchone()[0]
        is False
    )


def test_workbook_reads_all_real_format_sheets(tmp_path):
    # Only a loader test, not a dataset used by any report.
    row = {
        "Invoice": ["1"],
        "StockCode": ["x"],
        "Description": ["Item"],
        "Quantity": [1],
        "InvoiceDate": ["2010-01-01"],
        "Price": [2],
        "Customer ID": [1],
        "Country": ["UK"],
    }
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame(row).to_excel(writer, sheet_name="Year1", index=False)
        pd.DataFrame(row).to_excel(writer, sheet_name="Year2", index=False)
    assert len(load_raw(path)) == 2


@pytest.mark.skipif(
    not Path("data/retail.duckdb").exists(), reason="Full real-data build not present"
)
def test_real_data_ledger():
    con = duckdb.connect("data/retail.duckdb", read_only=True)
    try:
        assert con.execute("SELECT count(*) FROM bronze_retail").fetchone()[0] == 1067371
        assert con.execute("SELECT count(*) FROM bronze_transactions").fetchone()[0] == 1469307
        assert (
            con.execute("SELECT sum(revenue) FROM fact_lines").fetchone()
            == con.execute("SELECT sum(revenue) FROM mart_cohorts").fetchone()
        )
        assert con.execute("SELECT count(*) FROM dim_customers").fetchone()[0] > 5000
    finally:
        con.close()
