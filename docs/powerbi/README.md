# Power BI report kit

This folder is an import kit, not a PBIX or a published report. A complete rendered BI deliverable is available in `reports/retail_observatory.html`; `app/observatory.py` provides interactive filtering.

## Import

1. Build the project, then open Power BI Desktop.
2. Create a text parameter named `GoldFolder`, the absolute path to `data/gold`, ending in a slash or backslash.
3. Create the `LoadGold` function from [Power Query](queries.pq). Create one query per invocation in that file and apply the specified numeric/date types.
4. Import [theme.json](theme.json).
5. Create `DimSource` with distinct `source,currency` values from `mart_monthly`. Single-direction one-to-many relationships from `DimSource[source]` to every mart that contains `source`. Campaign and promotion tables are grocery-only; do not connect them to retail.
6. Use a **single-select** source slicer on all multi-source pages. Never present totals across currencies. Do not relate cohort, monthly, and segment fact marts directly to each other.
7. Add [DAX measures](measures.dax). Date filters for monthly revenue should not silently filter cohort age; these are different business dimensions.

## Pages

| Page | Visuals | Required filters and interpretation |
|---|---|---|
| Executive | Monthly stacked revenue, orders, 90-day repeat baseline | One source; flag partial final month |
| Retention | Cohort × age matrix, retention conditional formatting | `is_complete_month=true`; blanks remain unobserved |
| Observed value | Cumulative revenue/customer curves | Cohort selected; never sum cumulative points |
| Customer portfolio | Segment customers and historical revenue | RFM ranks are within-source; no churn prediction claim |
| Grocery marketing | Campaign reach/redemption scatter, promotion status revenue | Grocery only; descriptive association, not lift |
| Data trust | Disposition waterfall/table, source hashes, checks | Return values separate from positive-sales revenue |

## Metric rules

Retention totals must use one age value; summing active customers across ages double-counts people. LTV totals must use one age and weighted cohort sizes; summing cumulative values is invalid. Monthly active-customer totals across months are not unique customers. Promotion `baskets` is distinct within a status/week and is non-additive across statuses. Use transaction lines or revenue for additive promotion visuals.

For Snowflake, load generated candidate tables, validate counts, then point Power BI's native connector at the validated marts. Set an appropriate warehouse auto-suspend and refresh cadence in your account. No cloud deployment has been performed by the local build.
