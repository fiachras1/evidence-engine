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

# The settings below control HVN / LVN detection. Each is keyed by window
# length. Change them, rerun build_profiles.py, and look at the chart.
SMOOTH_PTS = {1: 1.5, 5: 3, 20: 6}       # how much to smooth the profile (points)
NODE_MIN_PROMINENCE = 0.10               # HVN/LVN must stand out by 10% of POC volume

# --- Ledges --------------------------------------------------------------------
# A ledge is the steep part of the slope where a volume node falls away into a
# thin area (an LVN, or the end of the profile).
LEDGE_MIN_FALL = 0.40        # volume must fall by at least 40% of the node's own volume
LEDGE_MIN_SIZE = 0.12        # ...and by at least 12% of the profile's POC volume
LEDGE_MAX_WIDTH = 15         # points. Wider than this is marked "wide" and not graded
LEDGE_MIN_NODE = 0.10        # the node must hold at least 10% of the profile's volume

# --- Ledge grades ----------------------------------------------------------------
# A ledge is graded when at least 2 daily profiles show it at the same price.
#   A  = 2+ daily profiles, the 5-day and the 20-day
#   B+ = 2+ daily profiles and the 20-day
#   B  = 2+ daily profiles and the 5-day
#   C  = 2+ daily profiles only
GRADE_DAYS = 5               # daily profiles looked at: the last 5 sessions...
GRADE_MAX_DAYS = 20          # ...plus earlier ones while price stayed in the same range
GRADE_TOLERANCE = 10         # points. Ledges this close together count as the same ledge
GRADE_ORDER = ("A", "B+", "B", "C")

# --- Micro balance (test 003) -----------------------------------------------------
MICRO_SHARE = (0.05, 0.25)   # a micro balance holds between 5% and 25% of the day's volume
