"""Settings shared by every script. Change things here, not in the scripts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_PARQUET = DATA_DIR / "raw" / "nq_ohlcv_1m.parquet"   # 1-minute bars: session stats
RAW_1S_DIR = DATA_DIR / "raw" / "1s"                      # 1-second bars: volume profiles
DB_PATH = DATA_DIR / "engine.duckdb"
SESSIONS_CSV = DATA_DIR / "sessions.csv"
SESSIONS_SQL = ROOT / "sql" / "sessions.sql"
PROFILES_SQL = ROOT / "sql" / "profiles.sql"
CHARTS_DIR = DATA_DIR / "charts"

# --- What to download -------------------------------------------------------
DATASET = "GLBX.MDP3"   # CME Globex
SYMBOL = "NQ.v.0"       # NQ front month, rolled by volume (prices NOT back-adjusted)
SCHEMA = "ohlcv-1m"     # 1-minute bars
START = "2025-01-01"
END = "2026-11-07"      # exclusive: data runs up to the day before

# --- Volume profile settings --------------------------------------------------
TICK = 0.25              # NQ tick size
ROW_TICKS = 5            # ticks grouped into one profile row (5 ticks = 1.25 points)
VALUE_AREA = 0.70        # share of volume inside the value area
WINDOWS = (1, 5, 20)     # 1 = single day, 5 and 20 = rolling composites

# The settings below control HVN / LVN / ledge detection. Each is keyed by
# window length. Change them, rerun build_profiles.py, and look at the chart.
SMOOTH_PTS = {1: 1.5, 5: 3, 20: 6}       # how much to smooth the profile (points)
NODE_MIN_PROMINENCE = 0.10               # HVN/LVN must stand out by 10% of POC volume
LEDGE_SPAN_PTS = {1: 5, 5: 8, 20: 12}    # a ledge is a drop that happens within this many points
LEDGE_MIN_DROP = 0.35                    # ...and is at least 35% of POC volume
