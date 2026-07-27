"""Validate cohort retention + LTV on a hand-computed sample
(the DoD 'cohort math validated')"""

from __future__ import annotations

import pandas as pd

from ltv.reference import cohort_ltv, cohort_retention


def test_retention_on_hand_built_example() -> None:
    # 2 customers acquired in Jan-2010. C1 active Jan, Feb, Mar; C2 Jan, Mar, C3 Jan only
    orders = pd.DataFrame(
        {
            "customer_id": [1, 1, 1, 2, 2, 3],
            "order_date": [
                "2010-01-05",
                "2010-02-10",
                "2010-03-12",
                "2010-01-20",
                "2010-03-03",
                "2010-01-25",
            ],
        }
    )
    r = cohort_retention(orders).set_index("month_n")

    # cohort size = 3. Month 0: all 3 active -> 1.0
    assert r.loc[0, "cohort_size"] == 3
    assert r.loc[0, "retention_pct"] == 1.0
    # Month 1 (Feb): only C1 -> 1/3
    assert r.loc[1, "active_customers"] == 1
    assert round(r.loc[1, "retention_pct"], 4) == round(1 / 3, 4)
    # Month 2 (Mar): C1 and C2 -> 2/3
    assert r.loc[2, "active_customers"] == 2
    assert round(r.loc[2, "retention_pct"], 4) == round(2 / 3, 4)


def test_cohort_ltv_cumulative() -> None:
    lines = pd.DataFrame(
        {
            "customer_id": [1, 1, 2],
            "order_date": ["2010-01-05", "2010-02-10", "2010-01-20"],
            "line_revenue": [100.0, 50.0, 200.0],
        }
    )
    ltv = cohort_ltv(lines).set_index("month_n")
    # cohort size = 2. Month 0 revenue = 100 + 200 = 300 -> 150 per customer.
    assert ltv.loc[0, "cumulative_ltv_per_customer"] == 150.0
    # Month 1 adds 50 -> cumulative 350 -> 175 per customer.
    assert ltv.loc[1, "cumulative_ltv_per_customer"] == 175.0
