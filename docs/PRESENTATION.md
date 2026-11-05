# A seven-minute project walkthrough

1. **Business question (45 seconds):** which customer relationships generate repeat revenue, and where should a retailer test an intervention? Explain that you measure observed behavior and propose experiments rather than claim invented profit uplift.
2. **Measured scale (45 seconds):** open the source ledger. Show actual row counts and checksums. Distinguish transaction lines from promotion records; do not call every row a sale.
3. **Retention (90 seconds):** open the cohort heatmap. Explain zero vs unobserved cells, left-censored acquisition, and incomplete final months. Compare only mature periods.
4. **Customer value (60 seconds):** show the revenue composition and RFM portfolio. Explain historical at-risk revenue versus forecast lost revenue. Demonstrate the explicitly hypothetical win-back calculator.
5. **Marketing (60 seconds):** show campaign reach/redemption and promotion placement. Explain the natural keys, pre-aggregation preventing join fanout, and why association is not causal lift.
6. **Engineering (90 seconds):** show architecture, one failed-quality test, Spark reconciliation, and the portable BI/Snowflake serving contracts.
7. **Next business step (30 seconds):** propose a randomized second-order or win-back trial, with holdout, fixed observation window, contribution margin, and incremental return measured after costs.

## Resume wording

Use measured figures from `reports/build_evidence.json` and `reports/source_manifest.json`:

> Built a reproducible retail analytics platform integrating UCI transactions and Complete Journey purchasing/promotion data; implemented Parquet ingestion, source lineage, observation-aware retention, RFM and campaign analytics, with reconciled PySpark promotion joins and interactive BI reporting.

Add the exact validated row counts and quality-gate count. Say “Snowflake-ready loading scripts” unless the Snowflake deployment has actually run. Do not claim production users, generated revenue, a multi-node benchmark, or a published Power BI dashboard without evidence.
