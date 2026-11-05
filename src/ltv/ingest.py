"""Download real datasets; record source URLs, row counts and content checksums."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

UCI = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
JOURNEY = "https://raw.githubusercontent.com/bradleyboehmke/completejourney/5b5d06192b9856edd04e4d405787af2f2e4a1fef/data/"
TABLES = [
    "transactions",
    "products",
    "demographics",
    "campaigns",
    "campaign_descriptions",
    "coupons",
    "coupon_redemptions",
    "promotions",
]


def digest(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def download(url: str, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".partial")
        for attempt in range(3):
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "retail-observatory/1.0"}
                )
                with (
                    urllib.request.urlopen(request, timeout=180) as response,
                    temporary.open("wb") as out,
                ):
                    shutil.copyfileobj(response, out)
                temporary.replace(path)
                break
            except Exception:
                temporary.unlink(missing_ok=True)
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
    return {
        "url": url,
        "path": path.as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data"))
    parser.add_argument("--skip-promotions", action="store_true")
    args = parser.parse_args()
    import pyarrow.parquet as pq
    import pyreadr

    from ltv.data_source import load_raw

    raw, bronze = args.root / "raw", args.root / "bronze"
    bronze.mkdir(parents=True, exist_ok=True)
    entries = []
    entry = download(UCI, raw / "online_retail_ii.zip")
    workbook = raw / "online_retail_II.xlsx"
    if not workbook.exists():
        with zipfile.ZipFile(raw / "online_retail_ii.zip") as z:
            member = next(n for n in z.namelist() if n.endswith(".xlsx"))
            with z.open(member) as source, workbook.open("wb") as out:
                shutil.copyfileobj(source, out)
    target = bronze / "retail.parquet"
    if not target.exists():
        load_raw(workbook).to_parquet(target, index=False, coerce_timestamps="us")
    entry.update(
        table="retail", rows=pq.read_metadata(target).num_rows, parquet_sha256=digest(target)
    )
    entries.append(entry)
    print(f"retail: {entry['rows']:,} rows", flush=True)
    for name in TABLES:
        if name == "promotions" and args.skip_promotions:
            continue
        extension = ".rds" if name in ("transactions", "promotions") else ".rda"
        source_file = raw / (name + extension)
        entry = download(JOURNEY + name + extension, source_file)
        target = bronze / (name + ".parquet")
        if not target.exists():
            frame = next(iter(pyreadr.read_r(str(source_file)).values()))
            for col in frame.select_dtypes("category"):
                frame[col] = frame[col].astype("string")
            for col in frame.select_dtypes("datetimetz"):
                frame[col] = frame[col].dt.tz_convert("UTC").dt.tz_localize(None)
            frame.to_parquet(target, index=False, coerce_timestamps="us")
            del frame
        entry.update(
            table=name, rows=pq.read_metadata(target).num_rows, parquet_sha256=digest(target)
        )
        entries.append(entry)
        print(f"{name}: {entry['rows']:,} rows", flush=True)
    manifest = {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "synthetic": False,
        "sources": entries,
    }
    (args.root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
