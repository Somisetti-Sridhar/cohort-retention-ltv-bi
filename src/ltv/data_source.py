"""
Load raw transactions.

Primary source: **UCI Online Retail II** (.xlsx, two yearly sheets). If the workbook is absent, a
reproducible synthetic dataset with the same schema and realistic repeat-purchase behaviour is
generated so the warehouse builds end-to-end..

"""

from __future__ import annotations

import structlog

from pathlib import Path

import numpy as np
import pandas as pd

from ltv.config import get_settings
from ltv.logging_config import get_logger

log: structlog.stdlib.BoundLogger = get_logger(__name__)

CANNONICAL: list[str] = [
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "price",
    "customer_id",
    "country",
]


def load_raw(path: str | Path | None = None) -> pd.DataFrame:
    path = Path(path or get_settings().raw_path)
    if path.exists():
        log.info("loading_online_retail_ii", path = str(path))
        df = pd.read_csv(path)
        # df = pd.concat(sheets.values(), ignore_index=True)
        return _normalize(df)
    log.warning("raw_not_found_using_synthetic", expected=str(path))
    return generate_synthetic()


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "Invoice": "invoice",
        "StockCode": "stock_code",
        "Description": "description",
        "Quantity": "quantity",
        "InvoiceDate": "invoice_date",
        "Price": "price",
        "Customer ID": "customer_id",
        "Country": "country",
    }
    df = df.rename(columns=rename)
    df["invoice"] = df["invoice"].astype("str")
    df["stock_code"] = df["stock_code"].astype(str)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    return df[CANNONICAL]


def generate_synthetic(n_customers: int = 1500, seed: int = 42) -> pd.DataFrame:
    """
    Synthetic e-commerce transactions with cohort structure:
    customers acquire across months and churn with a geometric tail, so retention/LTV curves are realistic and testable.
    """

    rng = np.random.default_rng(seed)
    countries = ["United Kingdom", "Germany", "France", "EIRE", "Spain", "Netherlands"]
    products = [
        (f"SKU{1000 + i}", name)
        for i, name in enumerate(
            ["WHITE MUG", "RED LANTERN", "JUMBO BAG", "PHOTO FRAME", "CANDLE SET",
             "TEA TOWEL", "NOTEBOOK", "GLASS JAR", "WALL CLOCK", "CUSHION COVER"]
        )
    ]
    start = pd.Timestamp("2009-12-01")
    rows: list[dict] = []
    invoice_no = 500000

    for cust in range(1, n_customers + 1):
        first_month = int(rng.integers(0, 22)) # acquired within a ~2yr window
        acq = start + pd.DateOffset(months = first_month)
        country = countries[int(rng.integers(0, len(countries)))]
        # Number of active months follows a geometric districbution => natural churn.
        lifetime_months = 1 + int(rng.geometric(0.35))
        spend_level = rng.uniform(0.8, 3.0)

        for m in range(lifetime_months):
            # skip some months are customers do not but every month
            if m > 0 and rng.random() < 0.48:
                continue
            order_date = acq + pd.DateOffset(months=m) + pd.to_timedelta(int(rng.integers(0, 27)), unit="D")
            if order_date > start + pd.DateOffset(months=24):
                break # we need data for 2 years
            invoice_no += 1
            n_lines = 1 + int(rng.integers(0, 4))
            for _ in range(n_lines):
                sku, name = products[int(rng.integers(0, len(products)))]
                qty = int(rng.integers(1, 12))
                price = round(float(rng.uniform(1.0, 12.0)) * spend_level, 2)
                rows.append(
                    {
                        "invoice": str(invoice_no),
                        "stock_code": sku,
                        "description": name,
                        "quantity": qty,
                        "invoice_date": order_date,
                        "price": price,
                        "customer_id": float(cust),
                        "country": country,
                    }
                )
    
    # inject a few cancellations (negative qty) and some missing customer ids
    df = pd.DataFrame(rows)
    cancels = df.sample(frac = 0.02, random_state = seed).copy()
    cancels["invoice"] = "C" + cancels["invoice"]
    cancels["quantity"] = -cancels["quantity"]
    df = pd.concat([df, cancels], ignore_index = True)
    null_idx = df.sample(frac = 0.03, random_state = seed + 1).index
    df.loc[null_idx, "customer_id"] = np.nan

    df = df[CANNONICAL].sort_values("invoice_date").reset_index(drop = True)
    log.info("synthetic generated", rows=len(df), customers = n_customers)
    return df