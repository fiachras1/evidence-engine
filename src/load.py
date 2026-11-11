"""Load the downloaded bars into DuckDB.

    python src/load.py

Creates bars_1m (1-minute bars) and, if 1-second data has been downloaded,
bars_1s.
"""
import sys

import duckdb

import config

if not config.RAW_PARQUET.exists():
    sys.exit(f"{config.RAW_PARQUET} not found. Run src/download.py --yes first.")

con = duckdb.connect(str(config.DB_PATH))
columns = "ts_event, symbol, instrument_id, open, high, low, close, volume"


def load(table, files):
    con.execute(f"""
        CREATE OR REPLACE TABLE {table} AS
        SELECT DISTINCT ON (ts_event) {columns}
        FROM read_parquet('{files}')
        ORDER BY ts_event
    """)
    n, first, last = con.execute(
        f"SELECT count(*), min(ts_event), max(ts_event) FROM {table}").fetchone()
    print(f"{table}: {n:,} bars from {first} to {last}")


load("bars_1m", config.RAW_PARQUET)
if any(config.RAW_1S_DIR.glob("*.parquet")):
    load("bars_1s", config.RAW_1S_DIR / "*.parquet")
else:
    print("No 1-second data yet (optional): python src/download.py 1s")
con.close()
