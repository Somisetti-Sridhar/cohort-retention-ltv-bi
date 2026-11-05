"""Real source files only; missing inputs never produce fabricated transactions."""

from pathlib import Path

import pandas as pd

from ltv.config import get_settings

CANNONICAL = [
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "price",
    "customer_id",
    "country",
]


def load_raw(path: str | Path | None = None) -> pd.DataFrame:
    path = Path(path or get_settings().raw_path)
    if not path.is_file():
        raise FileNotFoundError(f"Real data missing: {path}. Run python -m ltv.ingest first.")
    if path.suffix.lower() == ".xlsx":
        frame = pd.concat(pd.read_excel(path, sheet_name=None).values(), ignore_index=True)
    elif path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, dtype={"Invoice": str, "StockCode": str})
    else:
        raise ValueError(f"Unsupported source: {path.suffix}")
    return _normalize(frame)


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(
        columns={
            "Invoice": "invoice",
            "StockCode": "stock_code",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "invoice_date",
            "Price": "price",
            "Customer ID": "customer_id",
            "Country": "country",
        }
    ).copy()
    missing = set(CANNONICAL) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required source columns: {sorted(missing)}")
    for col in ("invoice", "stock_code", "description", "country"):
        df[col] = df[col].astype("string")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="raise")
    return df[CANNONICAL]
