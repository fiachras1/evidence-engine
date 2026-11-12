"""Test 001, step 2: what happens when price returns to a graded ledge?

    python src/find_setups.py      (first: finds the setups)
    python src/test_001.py

The trade, taken the first time price returns to the ledge:
  entry    at the near edge of the ledge zone
  hold     price moves HOLD_PTS away from the near edge          -> win
  fail     price trades FAIL_PTS beyond the far edge of the zone -> loss of 1R
  risk     zone width + FAIL_PTS, so a win pays HOLD_PTS / risk in R

Comparison ("placebo"): the same trade at a price PLACEBO_PTS before the
ledge, which price reaches first on its way back. If ledges mean something,
they should do better than an arbitrary price nearby.

RTH bars only. A trade not decided by the close carries into later sessions.
Setups where the session opens already at or past the ledge are left out.
If one bar reaches both the hold and the fail level it counts as a fail.
Results go in the table results_001, one row per trade.
"""
import duckdb
import numpy as np
import pandas as pd

import config

HOLD_PTS = 50
FAIL_PTS = 25
PLACEBO_PTS = 60

con = duckdb.connect(str(config.DB_PATH))
bars = con.execute("""
    SELECT CAST(ts_ny AS DATE) AS session_date, ts_event, open, high, low
    FROM (SELECT *, ts_event AT TIME ZONE 'America/New_York' AS ts_ny FROM bars_1m)
    WHERE CAST(ts_ny AS TIME) >= TIME '09:30' AND CAST(ts_ny AS TIME) < TIME '16:00'
    ORDER BY ts_event
""").fetchdf()
gap = dict(con.execute("SELECT session_date, roll_gap_total FROM session_contract").fetchall())
bars["gap"] = bars["session_date"].dt.date.map(gap)


def plain(ts):
    """A timestamp as plain UTC, so pandas and numpy versions all compare it the same way."""
    ts = pd.Timestamp(ts)
    return (ts.tz_convert("UTC").tz_localize(None) if ts.tzinfo else ts).to_datetime64()


times = bars["ts_event"].map(plain).to_numpy(dtype="datetime64[ns]")
highs, lows, gaps = bars["high"].to_numpy(), bars["low"].to_numpy(), bars["gap"].to_numpy()
opens = bars["open"].to_numpy()
days = bars["session_date"].to_numpy()
first_bar = np.r_[True, days[1:] != days[:-1]]         # first RTH bar of each session
setups = con.execute("SELECT * FROM setups_001 ORDER BY returned_at").fetchdf()


def trade(side, zone_low, zone_high, priced_on, after):
    """Follow one trade. Zone prices are on the contract of the date `priced_on`.

    Returns None if price never reaches the zone, otherwise a dict.
    """
    start = int(np.searchsorted(times, plain(after), side="right"))
    move = gaps[start:] - gap[priced_on]                 # roll adjustment per bar
    hi, lo = highs[start:] - move, lows[start:] - move   # bars in the zone's own prices
    if side == "top":                                    # retest from above: buy
        near, far = zone_high, zone_low
        touched, target, stop = lo <= near, hi >= near + HOLD_PTS, lo <= far - FAIL_PTS
        favourable = hi - near
    else:                                                # retest from below: sell
        near, far = zone_low, zone_high
        touched, target, stop = hi >= near, lo <= near - HOLD_PTS, hi >= far + FAIL_PTS
        favourable = near - lo
    if not touched.any():
        return None
    k = int(touched.argmax())
    risk = abs(near - far) + FAIL_PTS
    # Gapped: the session OPENED already at or past the ledge, so price got there
    # overnight and there was no retest to trade. These are left out of the results.
    open_price = opens[start + k] - move[k]
    gapped = bool(first_bar[start + k] and
                  (open_price <= near if side == "top" else open_price >= near))

    stop_at = k + int(stop[k:].argmax()) if stop[k:].any() else None
    target_at = k + 1 + int(target[k + 1:].argmax()) if target[k + 1:].any() else None
    if stop_at is None and target_at is None:
        outcome, r, end = "open", np.nan, len(hi) - 1
    elif target_at is not None and (stop_at is None or target_at < stop_at):
        outcome, r, end = "hold", HOLD_PTS / risk, target_at
    else:
        outcome, r, end = "fail", -1.0, stop_at

    # best move in our favour after entry, up to when the stop was finally hit
    last = stop_at if stop_at is not None else len(hi) - 1
    best = float(favourable[k + 1:last + 1].max()) if last > k else 0.0
    return dict(
        entry_time=times[start + k], gapped=gapped, width=abs(near - far), risk_pts=risk,
        outcome=outcome, r=r, best_move_pts=max(best, 0.0), best_r=max(best, 0.0) / risk,
        sessions_to_decide=len(np.unique(days[start + k:start + end + 1])) - 1)


rows = []
for s in setups.itertuples():
    on = s.return_date.date()
    real = trade(s.side, s.low, s.high, on, s.left_at)
    shift = PLACEBO_PTS if s.side == "top" else -PLACEBO_PTS
    fake = trade(s.side, s.low + shift, s.high + shift, on, s.left_at)
    for kind, result in (("ledge", real), ("placebo", fake)):
        if result:
            rows.append(dict(kind=kind, grade=s.grade, side=s.side, zone_low=s.low,
                             zone_high=s.high, same_session=s.sessions_to_return == 0, **result))

results = pd.DataFrame(rows)
con.register("new_rows", results)
con.execute("CREATE OR REPLACE TABLE results_001 AS SELECT * FROM new_rows")

summary = """
    SELECT {group} AS "group", count(*) AS trades,
           round(100 * avg(CASE WHEN outcome = 'hold' THEN 1 ELSE 0 END), 1) AS hold_pct,
           round(100 * avg(risk_pts / (risk_pts + {hold})), 1) AS breakeven_pct,
           round(avg(r), 2) AS avg_r,
           round(stddev(r) / sqrt(count(*)), 2) AS plus_minus,
           round(sum(r), 1) AS total_r,
           round(median(best_r), 2) AS median_best_r
    FROM results_001 WHERE outcome <> 'open' AND NOT gapped AND {where}
    GROUP BY 1 ORDER BY 1
"""
def show(title, group, where="true"):
    print(title)
    print(con.sql(summary.format(group=group, where=where, hold=HOLD_PTS)))

left_out = con.execute("SELECT count(*) FROM results_001 WHERE kind = 'ledge' AND gapped").fetchone()[0]
print(f"Left out: {left_out} ledge setups where the session opened already at or past the ledge.\n")
show("Ledges against the placebo", "kind")
show("Ledges by grade", "CASE WHEN grade = 'C' THEN 'C' ELSE 'B and better' END", "kind = 'ledge'")
show("Ledges: same-session return or later", "CASE WHEN same_session THEN 'same session' ELSE 'later session' END", "kind = 'ledge'")
show("Ledges by direction", "CASE WHEN side = 'top' THEN 'from above (buy)' ELSE 'from below (sell)' END", "kind = 'ledge'")
print("avg_r = average result per trade in R. plus_minus = its standard error:")
print("an avg_r smaller than about twice plus_minus is not distinguishable from zone.".replace("zone", "zero"))
con.close()
