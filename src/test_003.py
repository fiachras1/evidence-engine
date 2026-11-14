"""Test 003: micro balance after a failed expansion.

    python src/test_003.py

The setup (upside case; the downside case is the mirror image):
  1. EXPANSION      the day's high is EXPAND_PTS or more above the previous
                    day's value area high
  2. MICRO BALANCE  the day's profile has a separate small node at its high:
                    split from the rest by a thin area (LVN), holding between
                    SHARE_MIN and SHARE_MAX of the day's volume, and sitting
                    entirely above the previous day's value area
  3. REVERSAL       the day closes back below the micro balance
  4. RETEST         the first time a LATER RTH session trades back up to the
                    bottom of the micro balance. It is only traded if:
                    - OPEN RULE: that session opens in the lower half of the
                      micro balance day's value area, or below it
                    - EXPIRY RULE: the micro balance is at most EXPIRY_SESSIONS
                      old, or it still lies inside the 5-day profile's range

The trade on the retest: sell at the bottom edge of the micro balance, stop
STOP_PTS from the entry, targets TARGETS points from the entry (each reported
separately).

Comparison ("placebo"): the same trade PLACEBO_PTS before the micro balance.
1-second RTH bars. If one bar reaches both target and stop it counts as a loss.
Results go in the tables setups_003 and results_003.
"""
import duckdb
import numpy as np
import pandas as pd

import config
import vp

EXPAND_PTS = 100
SHARE_MIN, SHARE_MAX = config.MICRO_SHARE
STOP_PTS = 25
TARGETS = (60, 90)
PLACEBO_PTS = 60
EXPIRY_SESSIONS = 5
CHUNK = 250_000

con = duckdb.connect(str(config.DB_PATH))
tables = {t[0] for t in con.execute("SHOW TABLES").fetchall()}
if "bars_1s" not in tables or "profile_levels" not in tables:
    raise SystemExit("Needs 1-second bars and profiles: run load.py and build_profiles.py first.")

# ---- 1) find the setups -------------------------------------------------------
dates, profiles, gaps, contracts = vp.load_daily(con)
value = {r[0]: (r[1], r[2]) for r in con.execute(
    "SELECT session_date, val, vah FROM profile_levels WHERE window_days = 1").fetchall()}
day_stats = {r[0]: r[1:] for r in con.execute(
    "SELECT session_date, rth_high, rth_low, rth_close, full_day FROM sessions").fetchall()}
gap_on = dict(con.execute("SELECT session_date, roll_gap_total FROM session_contract").fetchall())

counts = dict(expansions=0, with_micro_balance=0, closed_back=0)
setups = []
for i in range(1, len(dates)):
    today, before = dates[i], dates[i - 1]
    high, low, close, full_day = day_stats[today]
    if not full_day:
        continue
    move = gap_on[today] - gap_on[before]                 # roll adjustment
    prev_val, prev_vah = value[before][0] + move, value[before][1] + move
    prices, vol = vp.composite([today], profiles, gaps)
    for end in ("high", "low"):
        expanded = high >= prev_vah + EXPAND_PTS if end == "high" else low <= prev_val - EXPAND_PTS
        if not expanded:
            continue
        counts["expansions"] += 1
        node = vp.end_node(prices, vol, 1, end)
        if node is None or not SHARE_MIN <= node["share"] <= SHARE_MAX:
            continue
        outside = node["low"] >= prev_vah if end == "high" else node["high"] <= prev_val
        if not outside:
            continue
        counts["with_micro_balance"] += 1
        closed_back = close < node["low"] if end == "high" else close > node["high"]
        if not closed_back:
            continue
        counts["closed_back"] += 1
        setups.append(dict(session_date=today, end=end, low=node["low"], high=node["high"],
                           value_mid=(value[today][0] + value[today][1]) / 2,
                           share=round(node["share"], 3), thinnest=node["thinnest"],
                           day_high=high, day_low=low, close=close))

# ---- 2) follow each one on 1-second bars ------------------------------------------
b = con.execute("""
    SELECT epoch_ns(ts_event) AS t, open, high, low, s.roll_gap_total AS gap,
           CAST(ts_ny AS DATE) AS session_date
    FROM (SELECT *, ts_event AT TIME ZONE 'America/New_York' AS ts_ny FROM bars_1s) x
    JOIN session_contract s ON s.session_date = CAST(x.ts_ny AS DATE)
    WHERE CAST(ts_ny AS TIME) >= TIME '09:30' AND CAST(ts_ny AS TIME) < TIME '16:00'
    ORDER BY ts_event
""").fetchnumpy()
T, OPEN, HIGH, LOW, GAP, DAY = b["t"], b["open"], b["high"], b["low"], b["gap"], b["session_date"]
FIRST = np.r_[True, DAY[1:] != DAY[:-1]]
day_index = pd.DatetimeIndex(DAY).date if DAY.dtype.kind == "M" else DAY
last_bar = {}                                             # session date -> index of its last bar
for idx in np.flatnonzero(np.r_[DAY[1:] != DAY[:-1], True]):
    last_bar[pd.Timestamp(DAY[idx]).date()] = int(idx)
first_bar = {pd.Timestamp(DAY[idx]).date(): int(idx) for idx in np.flatnonzero(FIRST)}
session_number = {d: n for n, d in enumerate(dates)}
range_5d = {r[0]: (r[1], r[2]) for r in con.execute(
    "SELECT session_date, low, high FROM profile_levels WHERE window_days = 5").fetchall()}


def first_true(mask_fn, start):
    i = start
    while i < len(T):
        j = min(i + CHUNK, len(T))
        hit = mask_fn(i, j)
        if hit.any():
            return i + int(hit.argmax())
        i = j
    return None


def trade(sell, level, priced_on, start, value_mid):
    """Sell (or buy) at `level` the first time price reaches it from bar `start` on."""
    sign = -1.0 if sell else 1.0          # work in terms where bigger = better for the trade
    base = gap_on[priced_on]

    def best(i, j):
        return sign * ((HIGH[i:j] if sign > 0 else LOW[i:j]) - (GAP[i:j] - base))

    def worst(i, j):
        return sign * ((LOW[i:j] if sign > 0 else HIGH[i:j]) - (GAP[i:j] - base))

    entry = sign * level
    k = first_true(lambda i, j: worst(i, j) <= entry, start)
    if k is None:
        return dict(status="not retested")
    retest_day = pd.Timestamp(DAY[k]).date()
    age = session_number[retest_day] - session_number[priced_on]

    # expiry rule: too old, and the 5-day profile has moved completely away from it
    day_before = dates[session_number[retest_day] - 1]
    if age > EXPIRY_SESSIONS and day_before in range_5d:
        shift = gap_on[day_before] - base
        low_5d, high_5d = range_5d[day_before][0] - shift, range_5d[day_before][1] - shift
        if not low_5d <= level <= high_5d:
            return dict(status="expired")

    # open rule: the session must open on the far half of the micro balance day's value
    o = first_bar[retest_day]
    if sign * (OPEN[o] - (GAP[o] - base)) < sign * value_mid:
        return dict(status="wrong open")
    stop_at = first_true(lambda i, j: worst(i, j) <= entry - STOP_PTS, k + 1)
    out = dict(status="trade", entry_ns=int(T[k]),
               sessions_to_retest=len(np.unique(DAY[start:k + 1])))
    for pts in TARGETS:
        hit = first_true(lambda i, j: best(i, j) >= entry + pts, k + 1)
        if hit is None and stop_at is None:
            out[f"outcome_{pts}"], out[f"r_{pts}"] = "open", np.nan
        elif hit is not None and (stop_at is None or hit < stop_at):
            out[f"outcome_{pts}"], out[f"r_{pts}"] = "win", pts / STOP_PTS
        else:
            out[f"outcome_{pts}"], out[f"r_{pts}"] = "loss", -1.0
    last = stop_at if stop_at is not None else len(T) - 1
    fav = max(float(best(i, min(i + CHUNK, last + 1)).max())
              for i in range(k + 1, last + 1, CHUNK)) - entry if last > k else 0.0
    out["best_r"] = max(fav, 0.0) / STOP_PTS             # furthest it ran before the stop, in R
    return out


rows = []
for s in setups:
    sell = s["end"] == "high"                             # micro balance at the high: sell the retest
    level = s["low"] if sell else s["high"]               # near edge
    start = last_bar[s["session_date"]] + 1               # later sessions only
    for kind, shift in (("micro balance", 0.0), ("placebo", -PLACEBO_PTS if sell else PLACEBO_PTS)):
        rows.append(dict(kind=kind, **s, level=level + shift,
                         **trade(sell, level + shift, s["session_date"], start, s["value_mid"])))

results = pd.DataFrame(rows)
if "entry_ns" in results:
    results["entry_time"] = pd.to_datetime(results.pop("entry_ns"), utc=True)
for name, frame in (("setups_003", pd.DataFrame(setups)), ("results_003", results)):
    con.register("new_rows", frame)
    con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM new_rows")
    con.unregister("new_rows")

print("How many days pass each step")
print(f"  expanded {EXPAND_PTS}+ points beyond the previous day's value:  {counts['expansions']}")
print(f"  ...and left a micro balance at the extreme:            {counts['with_micro_balance']}")
print(f"  ...and closed back out of it (the setups):             {counts['closed_back']}")
print(con.sql("""
    SELECT kind, count(*) FILTER (WHERE status = 'trade') AS trades,
           count(*) FILTER (WHERE status = 'wrong open') AS wrong_open,
           count(*) FILTER (WHERE status = 'expired') AS expired,
           count(*) FILTER (WHERE status = 'not retested') AS never_retested
    FROM results_003 GROUP BY kind ORDER BY kind
"""))
summary = """
    SELECT {group} AS "group", count(*) AS trades,
           round(100 * avg(CASE WHEN outcome_{pts} = 'win' THEN 1 ELSE 0 END), 1) AS win_pct,
           {be} AS breakeven_pct,
           round(avg(r_{pts}), 2) AS avg_r,
           round(stddev(r_{pts}) / sqrt(count(*)), 2) AS plus_minus,
           round(sum(r_{pts}), 1) AS total_r
    FROM results_003 WHERE status = 'trade' AND outcome_{pts} <> 'open' AND {where}
    GROUP BY 1 ORDER BY 1
"""
for pts in TARGETS:
    be = round(100 * STOP_PTS / (STOP_PTS + pts), 1)
    print(f"\n=== {pts}-point target ({pts / STOP_PTS:.1f}R), {STOP_PTS}-point stop ===")
    print(con.sql(summary.format(group="kind", pts=pts, be=be, where="true")))
    print(con.sql(summary.format(
        group="""CASE WHEN "end" = 'high' THEN 'at the high (sell)' ELSE 'at the low (buy)' END""",
        pts=pts, be=be, where="kind = 'micro balance'")))
# Thin-volume idea: was the range between the micro balance and the day's value thin?
thin = f"CASE WHEN thinnest <= {config.MICRO_THIN_MAX} THEN 'thin between' ELSE 'not thin' END"
for pts in TARGETS:
    be = round(100 * STOP_PTS / (STOP_PTS + pts), 1)
    print(f"\n=== Thin volume between micro balance and value, {pts}-point target ===")
    print(con.sql(summary.format(group=thin, pts=pts, be=be, where="kind = 'micro balance'")))

# Fresh data: setups from before config.START were never used to choose the rules.
fresh = f"session_date < DATE '{config.START}'"
if con.execute(f"SELECT count(*) FROM results_003 WHERE {fresh}").fetchone()[0]:
    for pts in TARGETS:
        be = round(100 * STOP_PTS / (STOP_PTS + pts), 1)
        print(f"\n=== FRESH DATA against the original period, {pts}-point target ===")
        print(con.sql(summary.format(
            group=f"kind || CASE WHEN {fresh} THEN ': FRESH (before {config.START})' ELSE ': original period' END",
            pts=pts, be=be, where="true")))
        print(con.sql(summary.format(
            group=f"{thin} || CASE WHEN {fresh} THEN ': FRESH' ELSE ': original period' END",
            pts=pts, be=be, where="kind = 'micro balance'")))
print("avg_r = average result per trade in R, before costs. plus_minus = its standard error:")
print("an avg_r smaller than about twice plus_minus is not distinguishable from zero.")
con.close()
