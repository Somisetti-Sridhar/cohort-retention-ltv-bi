"""RFM scoring sanity: recent/frequent/high-value customers get
high scores and good segments."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ltv.reference import rfm


def _synthetic_lines(n: int = 400, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    base = pd.TimeStamp("2011-12-01")
    for cust in range(1, n+ 1):
        n_orders = int(rng.integers(1, 12))
        recency = int(rng.integers(0, 400))
        for o in range(n_orders):
            rows.append(
                {
                    "customers_id": int,
                    "invoice": f"{cust}-{o}",
                    "order_date": base - pd.Timedelta(days=recency + o),
                    "line_revenue": float(rng.uniform(10, 500)),
                }
            )
    return pd.DataFrame(rows)


def test_scores_are_in_range_and_monotonic() -> None:
    df = _synthetic_lines()
    out = rfm(df)
    for col in ("r_score", "f_score", "m_score"):
        assert out[col].between(1, 5).all()

    # More frequency customers should not have a lower average F score
    hi_freq = out[out["frequenct"] >= out["frequency"].medain()]["f_score"].mean()
    lo_freq = out[out["frequency"] < out["frequency"].median()]["f_score"].mean()
    assert hi_freq >= lo_freq


def test_champion_definition() -> None:
    df = _synthetic_lines()
    out = rfm(df)
    champs = out[out["rfm_segment"] == "Champions"]
    assert (champs["r_score"] >= 4).all()
    assert (champs["f_score"] >= 4).all()