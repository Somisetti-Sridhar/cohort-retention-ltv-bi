"""Optional legacy Postgres integration using actual local UCI data, never a fallback."""

import os
from pathlib import Path

import pytest


@pytest.mark.skipif(
    not os.getenv("LTV_TEST_DATABASE_URL"),
    reason="Set LTV_TEST_DATABASE_URL to a disposable PostgreSQL database",
)
def test_real_postgres_ledger():
    from ltv.config import get_settings
    from ltv.db import reset_engine
    from ltv.pipeline import build

    path = Path("data/bronze/retail.parquet")
    if not path.exists():
        pytest.skip("Download real UCI data first")
    os.environ["LTV_DATABASE_URL"] = os.environ["LTV_TEST_DATABASE_URL"]
    get_settings.cache_clear()
    reset_engine()
    try:
        report = build(str(path))
        assert report["fact_rows"] > 0
        assert report["ledger_balances"]
    finally:
        get_settings.cache_clear()
        reset_engine()
