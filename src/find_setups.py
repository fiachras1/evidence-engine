"""Test 001, step 1: find the setups. No outcomes are measured here.

    python src/find_setups.py

A setup is:
  1. a graded ledge (see build_profiles.py)
  2. price LEAVES it: trades LEAVE_PTS beyond the ledge, on the thin side
       top ledge     price goes up, away from the node below it
       bottom ledge  price goes down, away from the node above it
  3. price RETURNS: the first time it trades back to the ledge

Only RTH bars are used, so overnight trade neither leaves nor returns.
Results go in the table setups_001.
"""
import duckdb
import pandas as pd

import config

LEAVE_PTS = 100          # how far price must travel beyond the ledge to have left it
WATCH_SESSIONS = 5       # a ledge must be left within this many sessions of last being graded

con = duckdb.connect(str(config.DB_PATH))

bars = con.execute("""
    SELECT CAST(ts_ny AS DATE) AS session_date, ts_event, high, low
    FROM (SELECT *, ts_event AT TIME ZONE 'America/New_York' AS ts_ny FROM bars_1m)
    WHERE CAST(ts_ny AS TIME) >= TIME '09:30' AND CAST(ts_ny AS TIME) < TIME '16:00'
    ORDER BY ts_event
""").fetchdf()
bars_by_day = {d.date(): g for d, g in bars.groupby("session_date")}
dates = sorted(bars_by_day)

gap = {r[0]: r[1] for r in con.execute(
    "SELECT session_date, roll_gap_total FROM session_contract").fetchall()}
grades = {}
for r in con.execute("""SELECT session_date, grade, low, high, side
                        FROM ledge_grades ORDER BY session_date""").fetchall():
    grades.setdefault(r[0], []).append(r[1:])


watching, setups = [], []
for i, today in enumerate(dates):
    day = bars_by_day[today]
    highs, lows, times = day["high"].to_numpy(), day["low"].to_numpy(), day["ts_event"].to_numpy()

    # 1) follow every ledge found on earlier sessions through today's bars
    still = []
    for g in watching:
        if g["state"] != "left" and i - g["last_seen_i"] > WATCH_SESSIONS:
            continue                                     # no longer graded: stop watching
        still.append(g)
        if g["state"] == "returned":
            continue                                     # already retested: first return only
        move = gap[today] - gap[g["priced_on"]]         # roll adjustment
        low, high = g["low"] + move, g["high"] + move
        start = 0
        if g["state"] == "watching":
            hit = (highs >= high + LEAVE_PTS) if g["side"] == "top" else (lows <= low - LEAVE_PTS)
            if not hit.any():
                continue
            start = int(hit.argmax()) + 1
            g.update(state="left", left_at=times[start - 1], left_i=i)
        back = (lows[start:] <= high) if g["side"] == "top" else (highs[start:] >= low)
        if back.any():
            k = start + int(back.argmax())
            g["state"] = "returned"
            setups.append(dict(
                first_seen=g["first_seen"], last_seen=dates[g["last_seen_i"]], grade=g["grade"],
                side=g["side"], low=low, high=high,
                left_at=g["left_at"], returned_at=times[k], return_date=today,
                sessions_to_return=i - g["left_i"]))
    watching = still

    # 2) add the ledges graded as of today's close. A ledge that matches one
    #    already being followed is the same ledge, not a new one.
    for grade, low, high, side in grades.get(today, []):
        for one_side in (("top", "bottom") if side == "both" else (side,)):
            match = None
            for g in watching:
                move = gap[today] - gap[g["priced_on"]]
                if (g["side"] == one_side and
                        low <= g["high"] + move + config.GRADE_TOLERANCE and
                        high >= g["low"] + move - config.GRADE_TOLERANCE):
                    match = g
                    break
            if match is None:
                match = dict(side=one_side, first_seen=today, state="watching")
                watching.append(match)
            match["last_seen_i"] = i
            if match["state"] == "watching":            # zone and grade freeze once price leaves
                match.update(low=low, high=high, grade=grade, priced_on=today)

unreturned = sum(g["state"] == "left" for g in watching)
found = pd.DataFrame(setups)
con.register("new_rows", found)
con.execute("CREATE OR REPLACE TABLE setups_001 AS SELECT * FROM new_rows")

print(f"Setups found: {len(found)}  (left but not yet returned by the end of the data: {unreturned})")
print(con.sql("""
    SELECT grade, count(*) AS setups,
           count(*) FILTER (WHERE side = 'top') AS retest_from_above,
           count(*) FILTER (WHERE side = 'bottom') AS retest_from_below
    FROM setups_001 GROUP BY grade ORDER BY grade
"""))
print(con.sql("""
    SELECT CASE WHEN sessions_to_return = 0 THEN '0 (same session)'
                WHEN sessions_to_return <= 3 THEN '1-3'
                WHEN sessions_to_return <= 10 THEN '4-10'
                ELSE 'more than 10' END AS sessions_to_return,
           count(*) AS setups
    FROM setups_001 GROUP BY 1 ORDER BY min(sessions_to_return)
"""))
con.close()
