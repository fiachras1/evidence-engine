"""Settings shared by every script. Change things here, not in the scripts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_PARQUET = DATA_DIR / "raw" / "nq_ohlcv_1m.parquet"
DB_PATH = DATA_DIR / "engine.duckdb"
SESSIONS_CSV = DATA_DIR / "sessions.csv"
SESSIONS_SQL = ROOT / "sql" / "sessions.sql"

# --- What to download -------------------------------------------------------
DATASET = "GLBX.MDP3"   # CME Globex
SYMBOL = "NQ.v.0"       # NQ front month, rolled by volume (prices NOT back-adjusted)
SCHEMA = "ohlcv-1m"     # 1-minute bars
START = "2025-01-01"
END = "2026-11-07"      # exclusive: data runs up to the day before
