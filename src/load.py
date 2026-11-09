"""Step 3: load the downloaded bars into DuckDB as the table bars_1m.

    python src/load.py
"""
import sys

import duckdb
import pandas as pd

import config

if not config.RAW_PARQUET.exists():
    sys.exit(f"{config.RAW_PARQUET} not found. Run src/download.py --yes first.")

df = pd.read_parquet(config.RAW_PARQUET)
if "ts_event" not in df.columns:      # timestamp may arrive as the index
    df = df.reset_index()

bars = df[["ts_event", "symbol", "open", "high", "low", "close", "volume"]].copy()
bars["ts_event"] = pd.to_datetime(bars["ts_event"], utc=True)
bars = bars.sort_values("ts_event").drop_duplicates("ts_event")

con = duckdb.connect(str(config.DB_PATH))
con.execute("CREATE OR REPLACE TABLE bars_1m AS SELECT * FROM bars")
n, first, last = con.execute(
    "SELECT count(*), min(ts_event), max(ts_event) FROM bars_1m"
).fetchone()
print(f"bars_1m: {n:,} bars from {first} to {last}")
con.close()
