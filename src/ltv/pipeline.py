"""
End-to-End, idempotent warehouse build.
    raw (xlsx/synthetic) -> staging_rae -> [SQL cleanse] -> star schema (dims + fact) -> views -> DQ

Re-runnable: schema DDL drops/recreates, dim/fact loads TRUNCATE+INSERT, views CREATE OR REPLACE.
Running it twice yields identical output. Run ``python -m ltv.pipeline``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ltv.config import get_settings
from ltv.data_source import load_raw
from ltv.db import get_engine, run_sql_file
from ltv.dq import run_checks
from ltv.logging_config import configure_logging, get_logger

log = get_logger(__name__)

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"

SQL_STEPS = [
    "00_schema.sql",
    "10_clean_staging.sql",
    "20_dim_date.sql",
    "30_dim_customer.sql",
    "31_dim_product.sql",
    "40_fact_sales.sql",
    "50_views.sql",
]


def load_staging(df: pd.DataFrame) -> None:
    """Bulk-load the raw frame into (already-create staging_raw table)"""
    df = df.copy()
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df.to_sql("staging_raw", get_engine(), if_exists="append", index=False, chunksize=10_000)
    log.info("staging_loaded", rows=len(df))


def build(raw_path: str | None = None) -> dict:
    configure_logging()
    settings = get_settings()
    log.info("pipeline_start", db=settings.database_url.split("@")[-1])

    df = load_raw(raw_path)

    # 1) schema (also creates staging_raw), 2) load raw 3) the rest of the SQL transforms.with
    run_sql_file(SQL_DIR / "00_schema.sql")
    load_staging(df)
    for step in SQL_STEPS[1:]:
        run_sql_file(SQL_DIR / step)
        log.info(f"Ran stage {step}")

    report = run_checks()
    log.info("pipeline_complete", fact_rows=report.fact_rows, customers=report.customers)
    return report.__dict__


if __name__ == "__main__":
    build()
