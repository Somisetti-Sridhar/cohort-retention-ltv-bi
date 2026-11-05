# Retail Observatory

**Customer retention, observed value, and promotion analytics on real retail data.**

This project expands a PostgreSQL cohort warehouse into a reproducible analytical platform: attributable source downloads → Parquet bronze → validated customer/order facts → BI marts → an offline report and interactive dashboard. A separate PySpark job processes the full promotion dataset; Snowflake loading scripts are generated from actual export schemas.

## Start with the results

- [Portable interactive BI report](reports/retail_observatory.html): download/open locally; Plotly is embedded, so no external chart service is needed.
- [Measured executive findings](reports/EXECUTIVE_BRIEF.md)
- [Build evidence](reports/build_evidence.json) and [source ledger](reports/source_manifest.json)
- [Power BI import kit](docs/powerbi/README.md)
- [Presentation walkthrough](docs/PRESENTATION.md)

The analytical questions are concrete: who purchases again, how much observed revenue comes from returning cohorts, which customer groups merit a controlled intervention, and how sales associate with recorded promotion placement. **Historical revenue is not profit, predicted LTV, or realized business uplift.**

## Real sources and scale

| Source | Published scale | Role |
|---|---:|---|
| UCI Online Retail II | 1,067,371 transaction lines | UK customer cohorts, returns, missing-identity audit |
| Complete Journey transactions | 1,469,307 transaction lines | US household purchasing and value |
| Complete Journey promotions | 20,940,529 product/store/week records | Large-table promotion joins and exposure associations |
| Complete Journey supporting tables | Products, demographics, campaigns, campaign descriptions, coupons, redemptions | Real relational keys and marketing context |

Actual downloaded row counts and SHA-256 hashes are recorded in the source ledger. The Complete Journey R package is a processed one-year study extract, not the entirety of the original two-year source release. See [source attribution and limits](docs/DATA_SOURCES.md).

No synthetic transaction fallback exists. Retail and grocery customer IDs are namespaced and never linked to each other. Currency-specific business metrics never add GBP and USD. The 300-million-row dunnhumby “Sort-of-Real” dataset is explicitly excluded because it is simulated.

## Run locally

Python 3.12+:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev,app]"
.venv/Scripts/python.exe -m ltv.ingest
.venv/Scripts/python.exe -m ltv.lakehouse
.venv/Scripts/python.exe -m ltv.report
.venv/Scripts/python.exe -m ltv.snowflake_export
.venv/Scripts/python.exe -m streamlit run app/observatory.py
```

On macOS/Linux replace `.venv/Scripts/python.exe` with `.venv/bin/python`. Downloads require network access; the pipeline and report then work offline. Budget several GB of local disk/memory for RDS conversion and the promotion join. `--skip-promotions` is an explicit smaller ingestion mode; it does not fabricate data. For a clean small run use a separate `--root`.

The source cache is reusable; Parquet conversion is skipped when present. Remove a specific source and corresponding Parquet intentionally to refresh it, then regenerate evidence. This is a **batch full refresh**, not CDC or incremental ingestion. SQL transformations commit only after quality gates pass. Gold marts are compact exports for BI; raw customer-level data is gitignored.

## Execute PySpark

```powershell
docker compose -f infra/analytics-compose.yml run --rm spark
.venv/Scripts/python.exe scripts/verify_spark.py
```

The job reads all promotion rows, collapses to a unique product/store/week key, joins positive grocery lines, reconciles rows and money, and writes weekly partitioned Parquet. It uses Spark SQL, adaptive query execution, and distributed aggregation, with no `toPandas()` on large tables. The supplied profile runs locally with two workers; it is not evidence of a multi-node production deployment. [Architecture and tradeoffs](docs/ARCHITECTURE.md).

## Snowflake and Power BI

`python -m ltv.snowflake_export` produces [SnowSQL staging and COPY statements](snowflake/load_gold.sql), with typed tables and abort-on-error behavior. This is an optional cloud serving path; no account or credits are needed for the local project. Cloud execution is not claimed unless separately evidenced.

The [Power BI kit](docs/powerbi/README.md) contains Power Query imports, DAX definitions, a theme, relationship guidance, and a report specification. The delivered HTML report and Streamlit app are runnable BI artifacts; the kit is **not a fabricated PBIX or a published Power BI Service report**.

## Validation

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
```

Tests cover missing-data failure, real-source loading, censored cohort grids, missing activity months, duplicate handling, identity isolation, monetary reconciliation, promotion join fanout and rerun stability. Small hand-calculated test cases are software test fixtures, never report data. Full-data integration tests activate when real local bronze files exist. CI runs unit tests and lint; the full data download is not repeated on every push.

## Existing PostgreSQL path

The original `python -m ltv.pipeline` and `app/streamlit_app.py` remain available with `infra/docker-compose.yml`. This legacy model handles UCI only and its sparse cohort views are not the authoritative completed-month BI marts. The new default is `ltv.lakehouse` + `app/observatory.py`. The PostgreSQL loader now correctly reads all workbook sheets and fails if real data is missing; quality failures now raise errors.

## What this demonstrates

- Data engineering: multi-source ingestion, columnar storage, lineage/checksums, explicit grains, typed money, join cardinality control, quality gates, transaction rollback, reproducible exports.
- Analytics: observation-aware retention, 90-day repeat purchase, revenue composition, RFM, observed cumulative revenue, campaign redemption, merchandising associations.
- BI: an offline presentation report, six interactive report pages, Power BI import assets and optional Snowflake serving.
- Judgment: separate populations/currencies, transparent exclusions, no causal claims from observational targeting, no unsupported revenue-uplift claims.
