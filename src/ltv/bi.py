"""Presentation-only conversion; gold Parquet retains exact decimal money."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def load_mart(path: Path):
    table = pq.read_table(path)
    frame = table.to_pandas()
    for field in table.schema:
        if pa.types.is_decimal(field.type):
            frame[field.name] = frame[field.name].astype(float)
    return frame
