"""Distributed promotion join with cardinality and monetary reconciliation gates.

Run via docker compose -f infra/analytics-compose.yml run --rm spark.
"""

import argparse
import json
import time
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="/workspace/data")
    args = parser.parse_args()
    root = Path(args.data)
    started = time.perf_counter()
    spark = (
        SparkSession.builder.appName("RetailObservatory-PromotionEvidence")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.shuffle.partitions", "16")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    try:
        promotions = spark.read.parquet(str(root / "bronze/promotions.parquet"))
        tx = spark.read.parquet(str(root / "bronze/transactions.parquet"))
        valid = tx.filter(
            (F.col("quantity") > 0)
            & (F.col("sales_value") > 0)
            & F.col("household_id").isNotNull()
            & F.col("basket_id").isNotNull()
            & F.col("transaction_timestamp").isNotNull()
        )
        keys = promotions.groupBy("product_id", "store_id", "week").agg(
            F.max((F.col("display_location").cast("string") != "0").cast("int")).alias(
                "on_display"
            ),
            F.max((F.col("mailer_location").cast("string") != "0").cast("int")).alias("in_mailer"),
            F.count("*").alias("source_records"),
        )
        joined = valid.join(keys, ["product_id", "store_id", "week"], "left")
        joined = joined.withColumn(
            "promotion_status",
            F.when(F.col("source_records").isNull(), "No matched promotion record")
            .when((F.col("on_display") == 1) & (F.col("in_mailer") == 1), "Display and mailer")
            .when(F.col("on_display") == 1, "Display only")
            .when(F.col("in_mailer") == 1, "Mailer only")
            .otherwise("Recorded without placement"),
        )
        result = (
            joined.groupBy("week", "promotion_status")
            .agg(
                F.count("*").alias("transaction_lines"),
                F.countDistinct("basket_id").alias("baskets"),
                F.sum(F.col("sales_value").cast("decimal(18,2)")).alias("revenue"),
                F.sum(F.col("retail_disc").cast("decimal(18,2)")).alias("retail_discount"),
            )
            .cache()
        )
        before = valid.agg(
            F.count("*").alias("rows"),
            F.sum(F.col("sales_value").cast("decimal(18,2)")).alias("revenue"),
        ).first()
        after = result.agg(
            F.sum("transaction_lines").alias("rows"), F.sum("revenue").alias("revenue")
        ).first()
        if before != after:
            raise ValueError(f"Promotion join changed source ledger: {before} != {after}")
        result.write.mode("overwrite").partitionBy("week").parquet(
            str(root / "spark/mart_promotions")
        )
        evidence = {
            "engine": spark.version,
            "promotion_rows": promotions.count(),
            "transaction_rows": before.rows,
            "revenue": str(before.revenue),
            "ledger_balances": True,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
        }
        (root / "spark/evidence.json").write_text(json.dumps(evidence, indent=2))
        print(json.dumps(evidence))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
