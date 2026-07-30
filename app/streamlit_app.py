"""Streamlit companion to the Power BI report - renders the same three pages from the warehouse.

Not a replacement for the Power BI Service deliverable; it's a runnable, reviewable view of the
exact SQL views (and a quick way to eyeball that the model is correct). Run:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import os

import altair as alt
import pandas as pd
import streamlit as st

from ltv.db import get_engine

st.set_page_config(page_title="Cohort · Retention · LTV", layout="wide")


USE_SPARK_AGGREGATES = os.getenv("LTV_ANALYTICS_SOURCE", "warehouse").lower() == "spark"


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, get_engine())


st.title("Cohort, Retention & LTV")
page = st.sidebar.radio("Page", ["Acquisition & Retention", "Segmentation (RFM)", "LTV & Revenue"])

if USE_SPARK_AGGREGATES:
    st.caption("Spark AVS aggregates: the raw transactions never enter the BI application.")
else:
    st.caption("Warehouse views: Part 1 Online Retail model.")
    kpis = q("SELECT * FROM v_kpis")
    if not kpis.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Revenue", f"{kpis.total_revenue[0]:,.0f}")
        c2.metric("Customers", f"{kpis.distinct_customers[0]:,}")
        c3.metric("Orders", f"{kpis.orders[0]:,}")
        c4.metric("Avg Order Value", f"{kpis.avg_order_value[0]:,.2f}")

if page == "Acquisition & Retention":
    st.subheader("Retention by cohort (month N)")
    r = q(
        "SELECT cohort_month, month_n, retention_pct FROM "
        + ("agg_cohort_retention" if USE_SPARK_AGGREGATES else "v_cohort_retention")
    )
    heat = (
        alt.Chart(r)
        .mark_rect()
        .encode(
            x=alt.X("month_n:O", title="Months since acquisition"),
            y=alt.Y("cohort_month:O", title="Cohort"),
            color=alt.Color("retention_pct:Q", scale=alt.Scale(scheme="greens"), title="Retention"),
            tooltip=["cohort_month", "month_n", alt.Tooltip("retention_pct:Q", format=".1%")],
        )
    )
    st.altair_chart(heat, use_container_width=True)

elif page == "Segmentation (RFM)":
    st.subheader("Revenue & customers by RFM segment")
    seg = q(
        "SELECT * FROM agg_rfm_segments"
        if USE_SPARK_AGGREGATES
        else (
            "SELECT rfm_segment, COUNT(*) AS customers, ROUND(SUM(monetary),2) AS revenue "
            "FROM v_rfm GROUP BY rfm_segment ORDER BY revenue DESC"
        )
    )
    st.altair_chart(
        alt.Chart(seg)
        .mark_bar()
        .encode(
            x=alt.X("revenue:Q", title="Revenue"),
            y=alt.Y("rfm_segment:N", sort="-x", title=""),
            tooltip=["rfm_segment", "customers", "revenue"],
        ),
        use_container_width=True,
    )
    st.dataframe(seg, use_container_width=True)

else:
    st.subheader("Cumulative LTV per customer by cohort")
    ltv = q(
        "SELECT cohort_month, month_n, cumulative_ltv_per_customer FROM "
        + ("agg_cohort_ltv" if USE_SPARK_AGGREGATES else "v_cohort_ltv")
    )
    st.altair_chart(
        alt.Chart(ltv)
        .mark_line(point=True)
        .encode(
            x=alt.X("month_n:O", title="Months since acquisition"),
            y=alt.Y("cumulative_ltv_per_customer:Q", title="Cumulative LTV / customer"),
            color="cohort_month:N",
            tooltip=["cohort_month", "month_n", "cumulative_ltv_per_customer"],
        ),
        use_container_width=True,
    )
