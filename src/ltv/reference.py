"""Pandas reference implementations of the cohort/RFM/LTV logic.

These are the *oracle* the tests use to validate the SQL views (and, by extension, the DAX measures,
which mirror the SQL). Keeping an independent second implementation is how we prove the warehouse
math is right rather than just self-consistent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _month_index(s: pd.Series) -> pd.Series:
    d = pd.to_datetime(s)
    return d.dt.year * 12 + d.dt.month


def cohort_retention(orders: pd.DataFrame) -> pd.DataFrame:
    """orders: columns [customer_id, order_date]. Returns cohort_month, month_n, retention_pct."""
    o = orders.copy()
    o["order_date"] = pd.to_datetime(o["order_date"])
    first = o.groupby("customer_id")["order_date"].min().rename("first")
    o = o.join(first, on="customer_id")
    o["cohort_month"] = o["first"].dt.strftime("%Y-%m")
    o["month_n"] = _month_index(o["order_date"]) - _month_index(o["first"])

    sizes = o.groupby("cohort_month")["customer_id"].nunique().rename("cohort_size")
    active = (
        o.groupby(["cohort_month", "month_n"])["customer_id"].nunique().rename("active_customers")
    )
    out = active.reset_index().join(sizes, on="cohort_month")
    out["retention_pct"] = (out["active_customers"] / out["cohort_size"]).round(4)
    return out.sort_values(["cohort_month", "month_n"]).reset_index(drop=True)


def rfm(lines: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    """lines: columns [customer_id, invoice, order_date, line_revenue]. Returns per-customer RFM."""
    df = lines.copy()
    df["order_date"] = pd.to_datetime(df["order_date"])
    as_of = as_of or df["order_date"].max()
    g = df.groupby("customer_id").agg(
        last_purchase=("order_date", "max"),
        frequency=("invoice", "nunique"),
        monetary=("line_revenue", "sum"),
    )
    g["recency_days"] = (as_of - g["last_purchase"]).dt.days
    # recent => high R; quintiles
    g["r_score"] = (
        pd.qcut(g["recency_days"].rank(method="first", ascending=False), 5, labels=False) + 1
    )
    g["f_score"] = pd.qcut(g["frequency"].rank(method="first"), 5, labels=False) + 1
    g["m_score"] = pd.qcut(g["monetary"].rank(method="first"), 5, labels=False) + 1

    def seg(row: pd.Series) -> str:
        r, f = row["r_score"], row["f_score"]
        if r >= 4 and f >= 4:
            return "Champions"
        if f >= 4:
            return "Loyal"
        if r >= 4:
            return "Promising"
        if r <= 2 and f >= 3:
            return "At-Risk"
        if r <= 2 and f <= 2:
            return "Lost"
        return "Needs Attention"

    g["rfm_segment"] = g.apply(seg, axis=1)
    return g.reset_index()


def cohort_ltv(lines: pd.DataFrame) -> pd.DataFrame:
    """lines: columns [customer_id, order_date, line_revenue]. Cumulative LTV per customer/cohort."""
    df = lines.copy()
    df["order_date"] = pd.to_datetime(df["order_date"])
    first = df.groupby("customer_id")["order_date"].min().rename("first")
    df = df.join(first, on="customer_id")
    df["cohort_month"] = df["first"].dt.strftime("%Y-%m")
    df["month_n"] = _month_index(df["order_date"]) - _month_index(df["first"])

    rev = df.groupby(["cohort_month", "month_n"])["line_revenue"].sum().rename("revenue")
    sizes = df.groupby("cohort_month")["customer_id"].nunique().rename("cohort_size")
    out = rev.reset_index().sort_values(["cohort_month", "month_n"])
    out["cumulative_revenue"] = out.groupby("cohort_month")["revenue"].cumsum()
    out = out.join(sizes, on="cohort_month")
    out["cumulative_ltv_per_customer"] = (out["cumulative_revenue"] / out["cohort_size"]).round(2)
    return out.reset_index(drop=True)


def assert_close(a: float, b: float, tol: float = 1e-6) -> None:
    assert np.isclose(a, b, atol=tol), f"{a} != {b}"
