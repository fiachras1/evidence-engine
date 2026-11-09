"""Step 2: download NQ 1-minute bars from Databento.

    python src/download.py          -> shows the cost, downloads nothing
    python src/download.py --yes    -> downloads to data/raw/
"""
import os
import sys

import databento as db
from dotenv import load_dotenv

import config

load_dotenv(config.ROOT / ".env")
key = os.getenv("DATABENTO_API_KEY")
if not key:
    sys.exit("No API key found. Copy .env.example to .env and paste your key in.")

client = db.Historical(key)
request = dict(
    dataset=config.DATASET,
    symbols=config.SYMBOL,
    stype_in="continuous",
    schema=config.SCHEMA,
    start=config.START,
    end=config.END,
)

cost = client.metadata.get_cost(**request)
print(f"{config.SYMBOL} {config.SCHEMA} {config.START} to {config.END}: ${cost:.2f}")

if "--yes" not in sys.argv:
    sys.exit("Nothing downloaded. Run again with --yes to download.")

config.RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
data = client.timeseries.get_range(**request)
data.to_parquet(config.RAW_PARQUET)
print(f"Saved to {config.RAW_PARQUET}")
