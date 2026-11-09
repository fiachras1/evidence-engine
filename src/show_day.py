"""Print one or more sessions with labelled numbers.

    python src/show_day.py 2026-08-19
    python src/show_day.py 2026-08-18 2026-08-21     (every session in that range)
"""
import sys

import duckdb

import config

if len(sys.argv) < 2:
    sys.exit("Give a date, e.g.  python src/show_day.py 2026-08-19")
start = sys.argv[1]
end = sys.argv[2] if len(sys.argv) > 2 else start

con = duckdb.connect(str(config.DB_PATH), read_only=True)
rows = con.execute(
    "SELECT * FROM sessions WHERE session_date BETWEEN ? AND ? ORDER BY session_date",
    [start, end],
).fetchdf()
if rows.empty:
    sys.exit(f"No session for {start}" + (f" to {end}" if end != start else "")
             + ". Weekend or no data?")

labels = [
    ("IB high", "ib_high"), ("RTH high", "rth_high"),
    ("IB low", "ib_low"), ("RTH low", "rth_low"),
    ("Up ext", "ext_up_pts"), ("Down ext", "ext_down_pts"),
    ("Extension", "ib_extension"),
    ("IB range", "ib_range"), ("RTH range", "rth_range"), ("IB %", "ib_pct_of_range"),
    ("RTH open", "rth_open"), ("RTH close", "rth_close"),
    ("ON high", "on_high"), ("ON low", "on_low"),
    ("Full day", "full_day"),
]
for _, r in rows.iterrows():
    print(f"\n{r['session_date']:%a %d %b %Y}")
    for label, col in labels:
        print(f"  {label:<10} {r[col]}")
