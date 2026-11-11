"""Build volume profiles: daily, 5-day and 20-day, with POC, value area,
HVNs, LVNs and ledges.

    python src/build_profiles.py

Each row is the profile of the N sessions ENDING on session_date, that day
included. So the levels you would have had on your chart going into a trading
day are the row for the session BEFORE it.
"""
import duckdb
import pandas as pd

import config
import vp

con = duckdb.connect(str(config.DB_PATH))
tables = {t[0] for t in con.execute("SHOW TABLES").fetchall()}
source = "bars_1s" if "bars_1s" in tables else "bars_1m"
print(f"Building profiles from {source}, {config.ROW_TICKS} ticks per row")
if source == "bars_1m":
    print("  (1-minute bars: coarse structure only. For accurate profiles: python src/download.py 1s)")
con.execute(f"CREATE OR REPLACE VIEW profile_bars AS SELECT * FROM {source}")
con.execute(config.PROFILES_SQL.read_text())
dates, profiles, gaps, contracts = vp.load_daily(con)

levels, nodes = [], []
for window in config.WINDOWS:
    for i in range(window - 1, len(dates)):
        window_dates = dates[i - window + 1:i + 1]
        prices, vol = vp.composite(window_dates, profiles, gaps)
        poc, val, vah = vp.value_area(vol)
        spans_roll = len({contracts[d] for d in window_dates}) > 1
        levels.append((dates[i], window, prices[poc], prices[vah], prices[val],
                       prices[0], prices[-1], vol.sum(), spans_roll))
        found, _ = vp.find_nodes(prices, vol, window)
        nodes += [(dates[i], window, kind, price, round(strength, 3), note)
                  for kind, price, strength, note in found]

profile_levels = pd.DataFrame(levels, columns=[
    "session_date", "window_days", "poc", "vah", "val",
    "low", "high", "volume", "spans_roll"])
profile_nodes = pd.DataFrame(nodes, columns=[
    "session_date", "window_days", "kind", "price", "strength", "note"])
con.execute("CREATE OR REPLACE TABLE profile_levels AS SELECT * FROM profile_levels")
con.execute("CREATE OR REPLACE TABLE profile_nodes AS SELECT * FROM profile_nodes")

print(con.sql("""
    SELECT window_days, count(*) AS profiles,
           count(*) FILTER (WHERE spans_roll) AS spanning_a_roll
    FROM profile_levels GROUP BY window_days ORDER BY window_days
"""))
print(con.sql("""
    SELECT n.window_days, n.kind, count(*) AS found,
           round(count(*) / any_value(t.profiles), 1) AS avg_per_profile
    FROM profile_nodes n
    JOIN (SELECT window_days, count(*) AS profiles FROM profile_levels GROUP BY 1) t
      USING (window_days)
    GROUP BY ALL ORDER BY n.window_days, n.kind
"""))
con.close()
