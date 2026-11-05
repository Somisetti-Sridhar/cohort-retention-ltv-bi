"""Generate SnowSQL load scripts from validated gold schemas. No cloud actions."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def sql_type(t):
    if pa.types.is_boolean(t):
        return "BOOLEAN"
    if pa.types.is_integer(t):
        return "NUMBER(38,0)"
    if pa.types.is_floating(t):
        return "FLOAT"
    if pa.types.is_decimal(t):
        return f"NUMBER({t.precision},{t.scale})"
    if pa.types.is_date(t):
        return "DATE"
    if pa.types.is_timestamp(t):
        return "TIMESTAMP_NTZ"
    return "VARCHAR"


def generate(root=Path("data/gold"), output=Path("snowflake/load_gold.sql")):
    files = sorted(root.glob("*.parquet"))
    if not files:
        raise FileNotFoundError("Build validated gold marts first")
    lines = [
        "-- Generated from actual gold schemas. Run with SnowSQL from the repository root.",
        "-- Uses your currently selected database, schema, warehouse, and role.",
        "-- Set a small warehouse with AUTO_SUSPEND=60 in your own account.",
        "CREATE STAGE IF NOT EXISTS RETAIL_OBSERVATORY_STAGE;",
        "CREATE FILE FORMAT IF NOT EXISTS RETAIL_PARQUET TYPE=PARQUET;",
    ]
    for path in files:
        name = path.stem.upper()
        columns = ",\n  ".join(
            f'"{f.name.upper()}" {sql_type(f.type)}' for f in pq.read_schema(path)
        )
        lines.extend(
            [
                f"PUT file://data/gold/{path.name} @RETAIL_OBSERVATORY_STAGE/{path.stem}/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;",
                f"CREATE OR REPLACE TABLE {name}_CANDIDATE (\n  {columns}\n);",
                f"COPY INTO {name}_CANDIDATE FROM @RETAIL_OBSERVATORY_STAGE/{path.stem}/ FILE_FORMAT=(FORMAT_NAME=RETAIL_PARQUET) MATCH_BY_COLUMN_NAME=CASE_INSENSITIVE ON_ERROR=ABORT_STATEMENT;",
                f"-- Validate row count against local export before promoting this candidate: {pq.read_metadata(path).num_rows}",
                f"SELECT COUNT(*) AS LOADED_ROWS FROM {name}_CANDIDATE;",
                f"-- After validation: ALTER TABLE {name}_CANDIDATE RENAME TO {name};",
            ]
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    generate()
