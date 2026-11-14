"""Test 002: ledge retest with a stop behind the turn.

    python src/find_setups.py      (first: finds the setups)
    python src/test_002.py

Same setups as test 001. The trade, on the first return to a graded ledge:
  turn     the extreme price makes at the ledge. It counts as made once price
           has moved TURN_PTS away from that extreme
  entry    at that moment, TURN_PTS away from the turn
  stop     STOP_PTS beyond the turn, so the risk is always TURN_PTS + STOP_PTS
  targets  each of TARGETS, in points from the entry, reported separately
  no trade if price goes THROUGH_PTS past the far edge of the ledge before turning

Comparison ("placebo"): the same trade at a price PLACEBO_PTS before the ledge.

Also measured, for every trade: after the first turn, how far beyond it price
went (a second high or low) before reaching the first target or giving up on
the ledge.

1-second RTH bars. A trade not decided by the close carries into later
sessions. If one bar reaches both the target and the stop it counts as a loss.
Sessions that open already at or past the ledge are left out.
Results go in the table results_002, one row per setup.
"""
import duckdb
import numpy as np
import pandas as pd

import config

TURN_PTS = 10
STOP_PTS = 5
TARGETS = (60, 90)
THROUGH_PTS = 25
PLACEBO_PTS = 60
RISK = TURN_PTS + STOP_PTS
CHUNK = 250_000            # 1-second bars looked at per step (roughly 10 sessions)

con = duckdb.connect(str(config.DB_PATH))
tables = {t[0] for t in con.execute("SHOW TABLES").fetchall()}
if "bars_1s" not in tables or "setups_001" not in tables:
    raise SystemExit("Needs 1-second bars and the setups: run load.py and find_setups.py first.")

b = con.execute("""
    SELECT epoch_ns(ts_event) AS t, open, high, low, s.roll_gap_total AS gap,
           CAST(ts_ny AS DATE) AS session_date
    FROM (SELECT *, ts_event AT TIME ZONE 'America/New_York' AS ts_ny FROM bars_1s) x
    JOIN session_contract s ON s.session_date = CAST(x.ts_ny AS DATE)
    WHERE CAST(ts_ny AS TIME) >= TIME '09:30' AND CAST(ts_ny AS TIME) < TIME '16:00'
    ORDER BY ts_event
""").fetchnumpy()
T, OPEN, HIGH, LOW, GAP = b["t"], b["open"], b["high"], b["low"], b["gap"]
DAY = b["session_date"]
FIRST = np.r_[True, DAY[1:] != DAY[:-1]]                 # first RTH bar of each session
gap_on = dict(con.execute("SELECT session_date, roll_gap_total FROM session_contract").fetchall())
setups = con.execute("SELECT *, epoch_ns(left_at) AS left_ns FROM setups_001 ORDER BY returned_at").fetchdf()


def first_true(mask_fn, start):
    """Index of the first bar at or after `start` where mask_fn(lo_index, hi_index) is True."""
    i = start
    while i < len(T):
        j = min(i + CHUNK, len(T))
        hit = mask_fn(i, j)
        if hit.any():
            return i + int(hit.argmax())
        i = j
    return None


def trade(side, zone_low, zone_high, priced_on, after_ns):
    """Follow one setup. Works in 'favourable' terms so buys and sells share the code:
    up() is price measured so that bigger = better for the trade."""
    sign = 1.0 if side == "top" else -1.0                # top: retest from above, buy
    base = gap_on[priced_on]

    def best(i, j):       # most favourable price of each bar, in the zone's own prices
        return sign * ((HIGH[i:j] if sign > 0 else LOW[i:j]) - (GAP[i:j] - base))

    def worst(i, j):      # least favourable price of each bar
        return sign * ((LOW[i:j] if sign > 0 else HIGH[i:j]) - (GAP[i:j] - base))

    near = sign * (zone_high if sign > 0 else zone_low)
    far = sign * (zone_low if sign > 0 else zone_high)
    start = int(np.searchsorted(T, after_ns, side="right"))

    k = first_true(lambda i, j: worst(i, j) <= near, start)          # first touch of the ledge
    if k is None:
        return None
    open_price = sign * (OPEN[k] - (GAP[k] - base))
    if FIRST[k] and open_price <= near:
        return dict(status="gapped")

    # the turn: running extreme, confirmed when price moves TURN_PTS away from it
    i, extreme = k, np.inf
    while True:
        j = min(i + CHUNK, len(T))
        if i >= j:
            return dict(status="open")
        w, bst = worst(i, j), best(i, j)
        run = np.minimum(np.minimum.accumulate(w), extreme)          # extreme so far, per bar
        before = np.r_[extreme, run[:-1]]                            # extreme before each bar
        made = bst >= before + TURN_PTS
        if made.any():
            m = int(made.argmax())
            turn, e = float(before[m]), i + m
            break
        extreme, i = float(run[-1]), j
    if turn <= far - THROUGH_PTS:
        return dict(status="through")                                # went through before turning

    entry, stop = turn + TURN_PTS, turn - STOP_PTS
    stop_at = first_true(lambda i, j: worst(i, j) <= stop, e + 1)
    out = dict(status="trade", entry_ns=int(T[e]), turn=sign * turn, entry=sign * entry,
               sessions_to_stop=None)
    for pts in TARGETS:
        hit = first_true(lambda i, j: best(i, j) >= entry + pts, e + 1)
        if hit is None and stop_at is None:
            out[f"outcome_{pts}"], out[f"r_{pts}"] = "open", np.nan
        elif hit is not None and (stop_at is None or hit < stop_at):
            out[f"outcome_{pts}"], out[f"r_{pts}"] = "win", pts / RISK
        else:
            out[f"outcome_{pts}"], out[f"r_{pts}"] = "loss", -1.0

    # second high/low: how far beyond the first turn did price go before the first
    # target level was reached, or before the ledge was given up on (THROUGH_PTS past it)?
    reached = first_true(lambda i, j: best(i, j) >= entry + TARGETS[0], e + 1)
    gave_up = first_true(lambda i, j: worst(i, j) <= far - THROUGH_PTS, e + 1)
    if reached is None and gave_up is None:
        out["path"], end = "open", len(T)
    elif reached is not None and (gave_up is None or reached < gave_up):
        out["path"], end = "reached target", reached
    else:
        out["path"], end = "gave up", gave_up
    lowest = min(float(worst(i, min(i + CHUNK, end + 1)).min())
                 for i in range(e + 1, end + 1, CHUNK)) if end > e else turn
    out["beyond_turn_pts"] = max(turn - lowest, 0.0)
    return out


rows = []
for s in setups.itertuples():
    on = s.return_date.date()
    shift = PLACEBO_PTS if s.side == "top" else -PLACEBO_PTS
    for kind, move in (("ledge", 0.0), ("placebo", shift)):
        result = trade(s.side, s.low + move, s.high + move, on, s.left_ns)
        if result:
            rows.append(dict(kind=kind, grade=s.grade, side=s.side, zone_low=s.low + move,
                             zone_high=s.high + move,
                             same_session=s.sessions_to_return == 0, **result))

results = pd.DataFrame(rows)
results["entry_time"] = pd.to_datetime(results.pop("entry_ns"), utc=True)
con.register("new_rows", results)
con.execute("CREATE OR REPLACE TABLE results_002 AS SELECT * FROM new_rows")

print(f"Stop {RISK} points on every trade (turn {TURN_PTS} + {STOP_PTS} beyond it).\n")
print("What happened to each setup")
print(con.sql("""
    SELECT kind,
           count(*) FILTER (WHERE status = 'trade') AS trades,
           count(*) FILTER (WHERE status = 'through') AS went_through_no_turn,
           count(*) FILTER (WHERE status = 'gapped') AS opened_past_ledge
    FROM results_002 GROUP BY kind ORDER BY kind
"""))

summary = """
    SELECT {group} AS "group", count(*) AS trades,
           round(100 * avg(CASE WHEN outcome_{pts} = 'win' THEN 1 ELSE 0 END), 1) AS win_pct,
           {be} AS breakeven_pct,
           round(avg(r_{pts}), 2) AS avg_r,
           round(stddev(r_{pts}) / sqrt(count(*)), 2) AS plus_minus,
           round(sum(r_{pts}), 1) AS total_r
    FROM results_002 WHERE status = 'trade' AND outcome_{pts} <> 'open' AND {where}
    GROUP BY 1 ORDER BY 1
"""
for pts in TARGETS:
    be = round(100 * RISK / (RISK + pts), 1)
    print(f"\\n=== {pts}-point target ({pts / RISK:.0f}R) ===".replace("\\n", "\n"))
    print(con.sql(summary.format(group="kind", pts=pts, be=be, where="true")))
    print(con.sql(summary.format(
        group="CASE WHEN grade = 'C' THEN 'ledge: C' ELSE 'ledge: B and better' END",
        pts=pts, be=be, where="kind = 'ledge'")))
    print(con.sql(summary.format(
        group="CASE WHEN same_session THEN 'ledge: same session' ELSE 'ledge: later session' END",
        pts=pts, be=be, where="kind = 'ledge'")))

print(f"\nSecond highs/lows: after the first turn, before price reached the {TARGETS[0]}-point target")
print(con.sql(f"""
    SELECT CASE WHEN path = 'gave up' THEN '4 never got there: ledge failed'
                WHEN beyond_turn_pts = 0 THEN '1 no second high/low: turn held exactly'
                WHEN beyond_turn_pts <= {STOP_PTS} THEN '2 second high/low within the {STOP_PTS}-pt stop'
                ELSE '3 second high/low BEYOND the stop, then reached target' END AS what_happened,
           count(*) AS trades,
           round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct,
           round(median(beyond_turn_pts), 2) AS median_pts_beyond_turn,
           round(max(beyond_turn_pts), 2) AS max_pts_beyond_turn
    FROM results_002 WHERE kind = 'ledge' AND status = 'trade' AND path <> 'open'
    GROUP BY 1 ORDER BY 1
"""))
print("avg_r = average result per trade in R, before costs. plus_minus = its standard error:")
print("an avg_r smaller than about twice plus_minus is not distinguishable from zero.")
con.close()
