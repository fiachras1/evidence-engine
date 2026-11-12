"""Show the graded ledges as of one session's close.

    python src/show_ledges.py 2026-09-07

These are the ledges you would have going into the NEXT session.
Grades: A = 2+ daily profiles + 5-day + 20-day, B+ = 2+ daily + 20-day,
B = 2+ daily + 5-day, C = 2+ daily profiles only.
"pending" means the latest RTH session traded through the ledge, so it only
becomes a level once price has left it.
"""
import sys

import duckdb

import config

if len(sys.argv) < 2:
    sys.exit("Give a date, e.g.  python src/show_ledges.py 2026-09-07")

con = duckdb.connect(str(config.DB_PATH), read_only=True)
rows = con.execute("""
    SELECT grade, low, high, side, daily_profiles, in_5d, in_20d, status, days_compared
    FROM ledge_grades WHERE session_date = ? ORDER BY low DESC
""", [sys.argv[1]]).fetchall()
con.close()
if not rows:
    sys.exit(f"No graded ledges for {sys.argv[1]}. Weekend, holiday, or none found.")

print(f"\nGraded ledges as of the close on {sys.argv[1]} ({rows[0][8]} daily profiles compared)")
for grade, low, high, side, days, in_5d, in_20d, status, _ in rows:
    where = [f"{days} daily"] + (["5-day"] if in_5d else []) + (["20-day"] if in_20d else [])
    print(f"  {grade:<2}  {low:.2f} to {high:.2f}   {side:<6} of node   {status:<8} ({', '.join(where)})")
