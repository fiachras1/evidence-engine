"""Download NQ bars from Databento.

    python src/download.py              1-minute bars: shows the cost only
    python src/download.py --yes        1-minute bars: downloads
    python src/download.py 1s           1-second bars: shows the cost only
    python src/download.py 1s --yes     1-second bars: downloads, one month at a time

1-second months already on disk are skipped, so if a download is interrupted
you can run the command again without paying twice.
"""
import os
import sys

import databento as db
import pandas as pd
from dotenv import load_dotenv

import config

load_dotenv(config.ROOT / ".env")
key = os.getenv("DATABENTO_API_KEY")
if not key:
    sys.exit("No API key found. Copy .env.example to .env and paste your key in.")

client = db.Historical(key)
go = "--yes" in sys.argv
common = dict(dataset=config.DATASET, symbols=config.SYMBOL, stype_in="continuous")

if "1s" not in sys.argv:
    # ---- 1-minute bars: one file ------------------------------------------
    request = dict(common, schema=config.SCHEMA, start=config.START, end=config.END)
    cost = client.metadata.get_cost(**request)
    print(f"{config.SYMBOL} {config.SCHEMA} {config.START} to {config.END}: ${cost:.2f}")
    if not go:
        sys.exit("Nothing downloaded. Run again with --yes to download.")
    config.RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    client.timeseries.get_range(**request).to_parquet(config.RAW_PARQUET)
    print(f"Saved to {config.RAW_PARQUET}")
    sys.exit()

# ---- 1-second bars: one file per month ------------------------------------
edges = [pd.Timestamp(config.START)]
edges += list(pd.date_range(config.START, config.END, freq="MS", inclusive="neither"))
edges.append(pd.Timestamp(config.END))
months = [(a, b) for a, b in zip(edges[:-1], edges[1:])
          if not (config.RAW_1S_DIR / f"nq_{a:%Y-%m}.parquet").exists()]
if not months:
    sys.exit("All months are already downloaded.")

total = 0.0
for a, b in months:
    total += client.metadata.get_cost(
        **common, schema="ohlcv-1s", start=a.date().isoformat(), end=b.date().isoformat())
print(f"{config.SYMBOL} ohlcv-1s, {len(months)} months still to download: ${total:.2f}")
if not go:
    sys.exit("Nothing downloaded. Run again with --yes to download.")

config.RAW_1S_DIR.mkdir(parents=True, exist_ok=True)
for a, b in months:
    path = config.RAW_1S_DIR / f"nq_{a:%Y-%m}.parquet"
    part = path.with_suffix(".part")          # only renamed once the month is complete
    data = client.timeseries.get_range(
        **common, schema="ohlcv-1s", start=a.date().isoformat(), end=b.date().isoformat())
    data.to_parquet(part)
    part.rename(path)
    print(f"  saved {path.name}")
print("Done.")
