"""Step 4: build the sessions table and export it for checking against Notion.

    python src/build_sessions.py
"""
import duckdb

import config

con = duckdb.connect(str(config.DB_PATH))
con.execute(config.SESSIONS_SQL.read_text())
con.execute(f"COPY sessions TO '{config.SESSIONS_CSV}' (HEADER, DELIMITER ',')")

print(con.sql("""
    SELECT session_date, rth_high, rth_low, rth_close, ib_high, ib_low,
           ib_extension, ext_up_pts, ext_down_pts
    FROM sessions ORDER BY session_date DESC LIMIT 10
"""))
total = con.execute("SELECT count(*) FROM sessions").fetchone()[0]
print(f"{total} sessions built. Full table exported to {config.SESSIONS_CSV}")
con.close()
