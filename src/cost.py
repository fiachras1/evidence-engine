"""Print what each level of data detail would cost. Downloads nothing.

    python src/cost.py                 (the full range in config.py)
    python src/cost.py 2026-03-01      (from that date instead)
"""
import os
import sys

import databento as db
from dotenv import load_dotenv

import config

load_dotenv(config.ROOT / ".env")
key = os.getenv("DATABENTO_API_KEY")
if not key:
    sys.exit("No API key found in .env")

client = db.Historical(key)
start = sys.argv[1] if len(sys.argv) > 1 else config.START
print(f"{config.SYMBOL}, {start} to {config.END}")
for schema, what in (("ohlcv-1m", "1-minute bars (what you have)"),
                     ("ohlcv-1s", "1-second bars"),
                     ("trades", "every individual trade (per tick)")):
    cost = client.metadata.get_cost(
        dataset=config.DATASET, symbols=config.SYMBOL, stype_in="continuous",
        schema=schema, start=start, end=config.END)
    size = client.metadata.get_billable_size(
        dataset=config.DATASET, symbols=config.SYMBOL, stype_in="continuous",
        schema=schema, start=start, end=config.END)
    print(f"  {schema:<9} ${cost:>8.2f}   {size / 1e9:>6.2f} GB   {what}")
