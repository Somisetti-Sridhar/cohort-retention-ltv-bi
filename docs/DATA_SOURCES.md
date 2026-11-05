# Source register and interpretation

## UCI Online Retail II

- Publisher: Daqing Chen / UCI Machine Learning Repository.
- [Dataset and license](https://archive.ics.uci.edu/dataset/502/online+retail+ii); DOI: [10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D).
- [Original ZIP](https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip), containing both yearly workbook sheets.
- License: CC BY 4.0. Preserve attribution when sharing outputs.
- Historical UK retailer, 2009–2011; invoice lines, quantities, prices in GBP, anonymous customer IDs and countries. Missing identities, cancellation invoices and source duplicates are real issues.
- Exact duplicate removal is an analytical policy, not proof every duplicate was erroneous. Excluded rows and signed source value are reported.

## Complete Journey

- Original provenance: 84.51° / dunnhumby household shopping study. [Publisher overview](https://www.dunnhumby.com/source-files/).
- We download the processed data published by [Brad Boehmke and Steven Mortimer](https://github.com/bradleyboehmke/completejourney), not an unaudited third-party CSV.
- [Transactions](https://bradleyboehmke.github.io/completejourney/reference/get_transactions.html): 1,469,307 lines; [promotions](https://bradleyboehmke.github.io/completejourney/reference/get_promotions.html): 20,940,529 records.
- [Field definitions](https://bradleyboehmke.github.io/completejourney/reference/transactions_sample.html); [promotion codebook](https://bradleyboehmke.github.io/completejourney/reference/promotions_sample.html).
- This is the package's processed year of transactions. Its timestamps are the processed source's analysis dates; do not claim unmodified original dates or contemporaneity with UCI.
- The source describes `sales_value` as dollars received by the retailer. It is used directly; discounts are not subtracted a second time. Discounts are descriptive fields, not proven margin erosion.
- Source data access terms apply independently of package code licensing. Raw RDS/Parquet and customer-level outputs are not redistributed in git. Public downloads do not imply unlimited commercial data redistribution rights.
- Frequent-shopper panel selection affects retention; demographics are available for only some households. Missing demographics are not imputed. There is no supported customer linkage to UCI.

## Natural joins

| Join | Keys | Cardinality protection |
|---|---|---|
| Grocery purchases → products | product_id | Fail if product key is not unique |
| Purchases → promotions | product_id, store_id, week | Collapse promotion rows before join; reconcile revenue and line count |
| Assignments → redemptions | household_id, campaign_id | Deduplicate assignments; aggregate redemptions before join |
| Purchases → households | source-scoped customer key | One observed customer per source identity |

Promotion matching is placement context, not verified human exposure. A missing match is explicitly “No matched promotion record,” not “unexposed control.” Coupons can map to many products; do not directly join the coupon table into transaction facts without pre-aggregation.

## Larger datasets considered

- dunnhumby Sort-of-Real: 300M transactions, **rejected because simulated**.
- [NYC TLC trip records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page): large real data, rejected for this project because public records do not establish persistent passenger identities for customer retention.
- UCI Online Retail (single-year): overlaps Online Retail II; adding it would inflate scale through double counting.

No synthetic identity bridges are needed for the chosen datasets. Any later scenario must be labeled as an assumption, and excluded from observed KPI marts.
