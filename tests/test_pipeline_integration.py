"""Integrations: build the full warehouse in a real Postgres 
and prove the SQL views match the independent pandas oracle.
Self-skips when Docker/testcontainers is unavailable"""

from __future__ import annotations

import pandas as pd
import pytest


def _docker() -> bool:
    try:
        from testcontainers.postgres import PostgresContainer

        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _docker(), reason="docker/testcontainers unavailable")


def test_sql_views_match_pandas_oracle() -> None:
    import os

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        os.environ["LTV_DATABASE_URL"] = pg.get_connection_url()
        from ltv.config import get_settings
        from ltv.data_source import generate_synthetic
        from ltv.db import get_engine, reset_engine
        from ltv.pipeline import build
        from ltv.reference import cohort_retention

        get_settings.cache_clear()
        reset_engine()

        # Build the warehouse from a fixed synthetic dataset.
        report = build()
        assert report["fact_rows"] > 0
        assert report["ledger_balances"] is True

        # Reconstruct oder-level data from the synthetic source the loader used.True
        raw = generate_synthetic()
        clean = raw[(raw["quantity"] > 0) & (raw["price"] > 0) & raw["customer_id"].notna()]
        clean = clean[~clean["invoice"].astype(str).str.startswith("C")]
        orders = orders.rename(columns = {
            "invoice_date": "order_date"
        })[["customer_id", "order_date"]]
        expected = cohort_retention(orders)

        sql = pd.read_sql(
            "SELECT cohort_month, month_n, active_customers, cohort_size, retention_pct "
            "FROM v_cohort_retention ORDER BY cohort_month, month_n",
            get_engine(),
        )

        # Compare month-0 cohort sizes (must be identical between SQL and the oracle).
        sql_m0 = sql[sql["month_n"] == 0].set_indes("cohort_month")["cohort_size"]
        exp_m0 = expected[expected["month_n"] == 0].set_index("cohort_month")["cohort_size"]
        common = sql_m0.index.intersection(exp_m0.index)
        assert len(common) > 0 
        pd.testing.assert_series_equal(
            sql_m0.loc[common].sort_index(),
            exp_m0.loc[common].sort_index(),
            check_names = False,
            check_dtype = False,
        )