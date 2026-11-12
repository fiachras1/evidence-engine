"""Build volume profiles: daily, 5-day and 20-day, with POC, value area,
HVNs, LVNs, ledges and ledge grades.

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

levels, nodes, ledges = [], [], []
ledges_by = {}                      # (session date, window) -> that profile's ledges
day = {}                            # session date -> (VAL, VAH, low, high) of its daily profile
for window in config.WINDOWS:
    for i in range(window - 1, len(dates)):
        window_dates = dates[i - window + 1:i + 1]
        prices, vol = vp.composite(window_dates, profiles, gaps)
        poc, val, vah = vp.value_area(vol)
        spans_roll = len({contracts[d] for d in window_dates}) > 1
        levels.append((dates[i], window, prices[poc], prices[vah], prices[val],
                       prices[0], prices[-1], vol.sum(), spans_roll))
        found, found_ledges, _ = vp.find_nodes(prices, vol, window)
        nodes += [(dates[i], window, kind, price, round(strength, 3))
                  for kind, price, strength in found]
        ledges += [(dates[i], window, g.low, g.high, g.width, round(g.fall, 3),
                    round(g.size, 3), round(g.node, 3), g.side, g.wide) for g in found_ledges]
        ledges_by[dates[i], window] = found_ledges
        if window == 1:
            day[dates[i]] = (prices[val], prices[vah], prices[0], prices[-1])

# Grade ledges as of each session's close. Older contracts' prices are shifted
# by the roll gap so every ledge is in terms of that session's contract.
grades = []
for i in range(19, len(dates)):
    today = dates[i]
    val, vah, low, high = day[today]

    def shift(d):                   # points to add to session d's prices
        return (gaps[today] - gaps[d]) / vp.TICKS_PER_POINT

    # The last GRADE_DAYS sessions, plus earlier ones for as long as price stayed
    # in the same range: their value area overlaps the latest session's.
    compare = list(dates[i - config.GRADE_DAYS + 1:i + 1])
    j = i - config.GRADE_DAYS
    while j >= 0 and len(compare) < config.GRADE_MAX_DAYS:
        d_val, d_vah = day[dates[j]][0] + shift(dates[j]), day[dates[j]][1] + shift(dates[j])
        if d_vah < val or d_val > vah:
            break
        compare.append(dates[j])
        j -= 1

    daily = {d: [g._replace(low=g.low + shift(d), high=g.high + shift(d))
                 for g in ledges_by[d, 1]] for d in compare}
    for row in vp.grade_ledges(daily, ledges_by[today, 5], ledges_by[today, 20], low, high):
        grades.append((today, len(compare)) + row)

profile_levels = pd.DataFrame(levels, columns=[
    "session_date", "window_days", "poc", "vah", "val",
    "low", "high", "volume", "spans_roll"])
profile_nodes = pd.DataFrame(nodes, columns=[
    "session_date", "window_days", "kind", "price", "strength"])
profile_ledges = pd.DataFrame(ledges, columns=[
    "session_date", "window_days", "low", "high", "width", "fall", "size", "node", "side", "wide"])
ledge_grades = pd.DataFrame(grades, columns=[
    "session_date", "days_compared", "grade", "low", "high", "side",
    "daily_profiles", "in_5d", "in_20d", "status"])
for table, frame in (("profile_levels", profile_levels), ("profile_nodes", profile_nodes),
                     ("profile_ledges", profile_ledges), ("ledge_grades", ledge_grades)):
    con.register("new_rows", frame)     # a separate name, so the old table is never read back
    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM new_rows")
    con.unregister("new_rows")

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
print(con.sql("""
    SELECT window_days, count(*) FILTER (WHERE NOT wide) AS ledges,
           count(*) FILTER (WHERE wide) AS too_wide
    FROM profile_ledges GROUP BY window_days ORDER BY window_days
"""))
print(con.sql("""
    SELECT grade, count(*) AS graded_ledges,
           count(*) FILTER (WHERE status = 'active') AS active,
           round(count(*) / (SELECT count(DISTINCT session_date) FROM ledge_grades), 1) AS avg_per_session
    FROM ledge_grades GROUP BY grade ORDER BY grade
"""))
con.close()
