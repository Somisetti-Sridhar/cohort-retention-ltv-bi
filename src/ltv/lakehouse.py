"""Transactional local lakehouse build, hard quality gates, and portable BI marts."""

from __future__ import annotations

import argparse
import contextlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

SQL = Path(__file__).resolve().parents[2] / "sql" / "lakehouse.sql"
MARTS = [
    "mart_cohorts",
    "mart_monthly",
    "mart_segments",
    "mart_repeat",
    "mart_quality",
    "mart_products",
    "mart_campaigns",
]


def build(root: Path = Path("data")) -> dict:
    started = time.perf_counter()
    root.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(root / "retail.duckdb"))
    con.execute("SET memory_limit='2GB'")
    con.execute("SET threads=4")
    checks = {}
    try:
        con.execute("BEGIN")
        for path in sorted((root / "bronze").glob("*.parquet")):
            if not path.stem.replace("_", "").isalnum():
                raise ValueError("Invalid table name")
            con.execute(
                f"CREATE OR REPLACE VIEW bronze_{path.stem} AS SELECT * FROM read_parquet('{path.resolve().as_posix().replace(chr(39), chr(39) * 2)}')"
            )
        if con.execute(
            "SELECT count(*)-count(DISTINCT product_id) FROM bronze_products"
        ).fetchone()[0]:
            raise ValueError("Product dimension is not unique; join would multiply revenue")
        con.execute(SQL.read_text(encoding="utf-8"))
        if (root / "bronze/promotions.parquet").exists():
            con.execute("""
              CREATE OR REPLACE TABLE promotion_keys AS
              SELECT product_id,store_id,week,
              bool_or(CAST(display_location AS VARCHAR)<>'0') AS on_display,
              bool_or(CAST(mailer_location AS VARCHAR)<>'0') AS in_mailer
              FROM bronze_promotions GROUP BY ALL;
              CREATE OR REPLACE TABLE mart_promotions AS
              SELECT t.week,CASE WHEN p.product_id IS NULL THEN 'No matched promotion record'
                WHEN p.on_display AND p.in_mailer THEN 'Display and mailer'
                WHEN p.on_display THEN 'Display only' WHEN p.in_mailer THEN 'Mailer only'
                ELSE 'Recorded without placement' END AS promotion_status,
              count(*) AS transaction_lines,count(DISTINCT t.basket_id) AS baskets,
              sum(CAST(t.sales_value AS DECIMAL(18,2))) AS revenue,
              sum(CAST(t.retail_disc AS DECIMAL(18,2))) AS retail_discount
              FROM bronze_transactions t LEFT JOIN promotion_keys p USING(product_id,store_id,week)
              WHERE t.quantity>0 AND t.sales_value>0 AND t.household_id IS NOT NULL
                AND t.basket_id IS NOT NULL AND t.transaction_timestamp IS NOT NULL
              GROUP BY ALL
            """)
        else:
            con.execute("DROP TABLE IF EXISTS mart_promotions")
        checks["nonempty_sources"] = con.execute(
            "SELECT count(DISTINCT source)=2 FROM fact_lines"
        ).fetchone()[0]
        checks["orders_reconcile"] = con.execute(
            "SELECT (SELECT sum(revenue) FROM fact_lines)=(SELECT sum(revenue) FROM fact_orders)"
        ).fetchone()[0]
        checks["journey_join_preserves_rows"] = con.execute(
            "SELECT (SELECT count(*) FROM fact_lines WHERE source='journey')=(SELECT sum(rows) FROM mart_quality WHERE source='journey' AND disposition='attributed_sale')"
        ).fetchone()[0]
        checks["retail_dispositions_reconcile"] = con.execute(
            "SELECT (SELECT sum(rows) FROM mart_quality WHERE source='retail')=(SELECT count(*) FROM bronze_retail)"
        ).fetchone()[0]
        checks["retention_bounds"] = con.execute(
            "SELECT count(*)=0 FROM mart_cohorts WHERE retention<0 OR retention>1 OR (month_n=0 AND retention<>1)"
        ).fetchone()[0]
        checks["cohort_revenue_reconciles"] = con.execute(
            "SELECT (SELECT sum(revenue) FROM mart_cohorts)=(SELECT sum(revenue) FROM fact_lines)"
        ).fetchone()[0]
        checks["identity_unique"] = con.execute(
            "SELECT count(*)=count(DISTINCT customer_key) FROM dim_customers"
        ).fetchone()[0]
        if (root / "bronze/promotions.parquet").exists():
            checks["promotion_join_preserves_revenue"] = con.execute(
                "SELECT (SELECT sum(revenue) FROM mart_promotions)=(SELECT sum(revenue) FROM fact_lines WHERE source='journey')"
            ).fetchone()[0]
        if not all(checks.values()):
            raise ValueError(f"Quality gates failed: {checks}")
        con.execute("COMMIT")
        gold = root / "gold"
        gold.mkdir(exist_ok=True)
        tables = MARTS + (
            ["mart_promotions"] if (root / "bronze/promotions.parquet").exists() else []
        )
        for name in tables:
            arrow = con.sql(f"SELECT * FROM {name} ORDER BY ALL").to_arrow_table()
            pq.write_table(arrow, gold / f"{name}.parquet", coerce_timestamps="us")
            arrow.to_pandas().to_csv(gold / f"{name}.csv", index=False)
        summary = (
            con.execute(
                "SELECT source,currency,count(*) AS customers,sum(orders) AS orders,sum(revenue) AS revenue,min(first_purchase) AS first_observed,max(last_purchase) AS last_observed FROM dim_customers GROUP BY ALL ORDER BY source"
            )
            .df()
            .to_dict(orient="records")
        )
        report = {
            "built_at_utc": datetime.now(UTC).isoformat(),
            "elapsed_seconds": round(time.perf_counter() - started, 2),
            "checks": checks,
            "summary": summary,
            "fact_lines": con.execute("SELECT count(*) FROM fact_lines").fetchone()[0],
        }
        (root / "build.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
        print(json.dumps(report, indent=2, default=str))
        return report
    except Exception:
        with contextlib.suppress(duckdb.Error):
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data"))
    build(parser.parse_args().root)
