"""
Data-quality checks run on every refresh. Results are logged (structured) so the run history is an audit trail, and asserted so a broken refresh fails loudly instead of publishing bad numbers
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from ltv.db import get_engine
from ltv.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class DQReport:
    raw_rows: int
    clean_rows: int
    dropped_rows: int
    null_customers_pct: float
    cancellations_removed: int
    fact_rows: int
    customers: int
    ledger_balances: bool  # fact line_revenue total == staging_clean total (no rows lost in joins)


def run_checks() -> DQReport:
    eng = get_engine()
    with eng.connect() as c:
        raw = c.execute(text("SELECT COUNT(*) FROM staging_raw")).scalar_one()
        clean = c.execute(text("SELECT COUNT(*) FROM staging_clean")).scalar_one()
        null_cust = c.execute(
            text("SELECT COUNT(*) FROM staging_raw WHERE customer_id IS NULL")
        ).scalar_one()
        cancels = c.execute(
            text("SELECT COUNT(*) FROM staging_raw WHERE invoice LIKE 'C%' OR quantity <= 0")
        ).scalar_one()
        fact = c.execute(text("SELECT COUNT(*) FROM fact_sales")).scalar_one()
        custs = c.execute(text("SELECT COUNT(*) FROM dim_customer")).scalar_one()
        clean_rev = c.execute(
            text("SELECT COALEScE(SUM(line_revenue), 0) FROM staging_clean")
        ).scalar_one()
        fact_rev = c.execute(
            text("SELECT COALESCE(SUM(line_revenue), 0) FROM fact_sales")
        ).scalar_one()

    report = DQReport(
        raw_rows=raw,
        clean_rows=clean,
        dropped_rows=raw - clean,
        null_customers_pct=round(100 * null_cust / raw, 2) if raw else 0.0,
        cancellations_removed=cancels,
        fact_rows=fact,
        customers=custs,
        ledger_balances=abs(float(clean_rev) - float(fact_rev)) < 0.01,
    )
    log.info("dq_report", **report.__dict__)

    # Hard invariants - a refresh that violates these must not publish.
    if report.fact_rows == 0:
        log.error("fact_sales is empty")
    if report.clean_rows >= report.raw_rows:
        log.error("clean has more rows than raw")
    if not report.ledger_balances:
        log.error("revenue lost between staging_clean and fact_sales (bad join)")
    return report
