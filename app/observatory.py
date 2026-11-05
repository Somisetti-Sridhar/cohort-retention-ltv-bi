"""Interactive BI over small, validated gold marts; no raw data in the UI."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from ltv.bi import load_mart

st.set_page_config(page_title="Retail Observatory", page_icon="📊", layout="wide")
ROOT = Path(__file__).resolve().parents[1] / "data"
st.title("Retail Observatory")
st.caption("Real transactions. Observed customer value. Measurable retention.")
if not (ROOT / "build.json").exists():
    st.info(
        "Build the real-data reports first: python -m ltv.ingest, then python -m ltv.lakehouse."
    )
    st.stop()


@st.cache_data(ttl=60)
def load(name):
    return load_mart(ROOT / "gold" / f"mart_{name}.parquet")


source = st.sidebar.selectbox(
    "Retail population",
    ["retail", "journey"],
    format_func=lambda x: {
        "retail": "UK online retail · GBP",
        "journey": "US household grocery · USD",
    }[x],
)
page = st.sidebar.radio(
    "Report",
    [
        "Executive overview",
        "Retention & observed value",
        "Customer segments",
        "Campaigns & promotions",
        "Product portfolio",
        "Quality & provenance",
    ],
)
currency = "GBP" if source == "retail" else "USD"
build = json.loads((ROOT / "build.json").read_text())
summary = next(x for x in build["summary"] if x["source"] == source)
st.sidebar.caption(
    f"Observed {summary['first_observed'][:10]} to {summary['last_observed'][:10]}. Historical research data."
)
st.sidebar.caption(
    "Retailers have independent identities and currencies. Cohorts mean first observed purchase, not verified acquisition."
)

if page == "Executive overview":
    cols = st.columns(3)
    cols[0].metric(f"Positive attributed sales ({currency})", f"{summary['revenue']:,.0f}")
    cols[1].metric("Observed customers", f"{summary['customers']:,}")
    cols[2].metric("Orders", f"{summary['orders']:,}")
    m = load("monthly").query("source==@source")
    st.plotly_chart(
        px.bar(
            m,
            x="month",
            y=["first_observed_cohort_revenue", "returning_cohort_revenue"],
            title=f"Monthly revenue composition ({currency})",
        ),
        width="stretch",
    )
    st.caption(
        "The final observed month may be incomplete. Revenue excludes returns and missing identities; see Quality for exclusions."
    )
    r = load("repeat").query("source==@source").iloc[0]
    st.metric("Repeat within 90 days", f"{r.repeat_rate_90d:.1%}")
    st.caption(
        f"{int(r.eligible_customers):,} customers with at least 90 days of follow-up. This is repeat purchasing, not subscription retention."
    )
elif page == "Retention & observed value":
    c = load("cohorts").query("source==@source")
    if st.checkbox("Completed calendar months only", True):
        c = c[c.is_complete_month]
    if st.checkbox("Exclude first cohort (left-censored)", False):
        c = c[~c.is_left_censored_cohort]
    heat = c.pivot(index="cohort_month", columns="month_n", values="retention")
    heat.index = pd.to_datetime(heat.index).strftime("%Y-%m")
    st.plotly_chart(
        px.imshow(
            heat,
            aspect="auto",
            zmin=0,
            zmax=1,
            color_continuous_scale="Blues",
            labels={"x": "Month since first observed purchase", "color": "Retention"},
        ),
        width="stretch",
    )
    st.plotly_chart(
        px.line(
            c,
            x="month_n",
            y="cumulative_revenue_per_customer",
            color=c.cohort_month.astype(str),
            title=f"Observed cumulative revenue per customer ({currency})",
        ),
        width="stretch",
    )
    st.caption(
        "Blank = not observed. Zero = observed without repeat activity. Revenue LTV is not a forecast or profit estimate."
    )
elif page == "Customer segments":
    s = load("segments").query("source==@source")
    st.plotly_chart(
        px.bar(
            s,
            x="segment",
            y="historical_revenue",
            title=f"Historical revenue by RFM segment ({currency})",
        ),
        width="stretch",
    )
    st.dataframe(s, hide_index=True)
    st.subheader("Win-back planning scenario")
    st.caption(
        "User assumptions applied to real segment counts; not measured uplift or forecast revenue."
    )
    rate = st.slider("Assumed incremental response (%)", 0.0, 20.0, 2.0) / 100
    contribution = st.number_input(
        f"Assumed contribution per incremental responder ({currency})", min_value=0.0, value=20.0
    )
    cost = st.number_input(
        f"Assumed contact cost per targeted customer ({currency})", min_value=0.0, value=1.0
    )
    count = int(s.loc[s.segment == "At risk", "customers"].sum())
    st.metric(
        "Scenario net contribution", f"{currency} {count * (rate * contribution - cost):,.2f}"
    )
    st.caption(
        f"{count:,} at-risk customers × (assumed response × contribution − contact cost). Validate in a randomized holdout."
    )
elif page == "Campaigns & promotions":
    if source != "journey":
        st.info(
            "Campaign and promotion observations are available only for the US grocery population."
        )
    else:
        c = load("campaigns")
        st.plotly_chart(
            px.scatter(
                c,
                x="targeted_households",
                y="household_redemption_rate",
                size="redemptions",
                hover_name="campaign_id",
            ),
            width="stretch",
        )
        if (ROOT / "gold/mart_promotions.parquet").exists():
            p = load("promotions")
            st.plotly_chart(
                px.bar(
                    p.groupby("promotion_status", as_index=False).revenue.sum(),
                    x="revenue",
                    y="promotion_status",
                    orientation="h",
                ),
                width="stretch",
            )
        st.warning(
            "Descriptive associations only. Targeting and placement are not randomized; no causal lift or ROI is established."
        )
elif page == "Product portfolio":
    p = load("products").query("source==@source").sort_values("revenue", ascending=False)
    st.plotly_chart(
        px.bar(
            p.head(20),
            x="revenue",
            y="product_id",
            orientation="h",
            title=f"Top 20 products by revenue ({currency})",
        ),
        width="stretch",
    )
    st.dataframe(p.head(100), hide_index=True)
else:
    st.dataframe(load("quality").query("source==@source"), hide_index=True)
    st.json(build["checks"])
    st.json(json.loads((ROOT / "manifest.json").read_text()))
