"""Download NQ bars from Databento.

    python src/download.py              1-minute bars: shows the cost only
    python src/download.py --yes        1-minute bars: downloads
    python src/download.py 1s           1-second bars: shows the cost only
    python src/download.py 1s --yes     1-second bars: downloads, one month at a time
    python src/download.py early        earlier history (both kinds): shows the cost only
    python src/download.py early --yes  earlier history: downloads

"early" covers EARLY_START up to START in config.py.
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
early = "early" in sys.argv
common = dict(dataset=config.DATASET, symbols=config.SYMBOL, stype_in="continuous")
start, end = (config.EARLY_START, config.START) if early else (config.START, config.END)
total = 0.0


def missing_months():
    """(first day, day after last) for each month of 1-second data not yet on disk."""
    edges = [pd.Timestamp(start)]
    edges += list(pd.date_range(start, end, freq="MS", inclusive="neither"))
    edges.append(pd.Timestamp(end))
    return [(a, b) for a, b in zip(edges[:-1], edges[1:])
            if not (config.RAW_1S_DIR / f"nq_{a:%Y-%m}.parquet").exists()]


# ---- 1-minute bars: one file ------------------------------------------------
minute_file = config.RAW_PARQUET_EARLY if early else config.RAW_PARQUET
want_minute = early or "1s" not in sys.argv
if want_minute and not (early and minute_file.exists()):
    request = dict(common, schema=config.SCHEMA, start=start, end=end)
    cost = client.metadata.get_cost(**request)
    total += cost
    print(f"{config.SYMBOL} {config.SCHEMA} {start} to {end}: ${cost:.2f}")
    if go:
        minute_file.parent.mkdir(parents=True, exist_ok=True)
        client.timeseries.get_range(**request).to_parquet(minute_file)
        print(f"  saved {minute_file.name}")

# ---- 1-second bars: one file per month ------------------------------------------
if early or "1s" in sys.argv:
    months = missing_months()
    cost = sum(client.metadata.get_cost(**common, schema="ohlcv-1s",
                                        start=a.date().isoformat(), end=b.date().isoformat())
               for a, b in months)
    total += cost
    print(f"{config.SYMBOL} ohlcv-1s {start} to {end}, {len(months)} months still to download: ${cost:.2f}")
    if go:
        config.RAW_1S_DIR.mkdir(parents=True, exist_ok=True)
        for a, b in months:
            path = config.RAW_1S_DIR / f"nq_{a:%Y-%m}.parquet"
            part = path.with_suffix(".part")      # only renamed once the month is complete
            data = client.timeseries.get_range(
                **common, schema="ohlcv-1s", start=a.date().isoformat(), end=b.date().isoformat())
            data.to_parquet(part)
            part.rename(path)
            print(f"  saved {path.name}")

print(f"Total: ${total:.2f}")
print("Done." if go else "Nothing downloaded. Run again with --yes to download.")
