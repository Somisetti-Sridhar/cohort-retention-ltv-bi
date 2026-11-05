"""Independently reconcile all Spark promotion aggregates with DuckDB outputs."""

import json
from pathlib import Path

import duckdb

root = Path("data")
con = duckdb.connect()
spark = "read_parquet('data/spark/mart_promotions/**/*.parquet', hive_partitioning=true)"
gold = "read_parquet('data/gold/mart_promotions.parquet')"
different = con.execute(f"""
 SELECT count(*) FROM {spark} s FULL OUTER JOIN {gold} g USING(week,promotion_status)
 WHERE s.week IS NULL OR g.week IS NULL OR s.transaction_lines<>g.transaction_lines
 OR s.baskets<>g.baskets OR abs(s.revenue-g.revenue)>0.005
 OR abs(s.retail_discount-g.retail_discount)>0.005
""").fetchone()[0]
if different:
    raise ValueError(f"{different} Spark aggregate rows disagree with the local reference")
evidence = json.loads((root / "spark/evidence.json").read_text())
evidence["cross_engine_mismatches"] = different
evidence["aggregate_rows"] = con.execute(f"SELECT count(*) FROM {gold}").fetchone()[0]
Path("reports").mkdir(exist_ok=True)
Path("reports/spark_evidence.json").write_text(json.dumps(evidence, indent=2))
print(json.dumps(evidence, indent=2))
