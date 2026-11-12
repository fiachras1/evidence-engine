# 001: Balance-edge flip

**Status:** first run complete (12 November 2026). No edge found with these rules.
**Defined:** 11 November 2026

## Question

After price leaves a balance and extends away from it, does the balance's
edge act as support (or resistance) the first time price comes back to it?

Market logic: buyers and sellers agreed on value inside the balance. An
extension with acceptance outside means one side could not hold it. On the
return, the side that won should defend the edge it broke through.

## Definitions (fixed before any results are seen)

| Term | Definition |
|---|---|
| Balance | 2 or more consecutive sessions where each day's VAH is within 25 points of the other days' VAHs, and each VAL within 25 points of the other VALs |
| Edge | The ledge on the side of the balance price left. Not necessarily the VAH/VAL. A ledge is where a volume node falls by 40% or more into a thin area, in a zone no wider than 15 points, from a node holding at least 10% of the profile's volume |
| Ledge grade | A = on 2+ daily profiles, the 5-day and the 20-day. B+ = 2+ daily and the 20-day. B = 2+ daily and the 5-day. C = 2+ daily only. Daily profiles compared: the last 5 sessions, plus earlier ones while price stayed in the same range. Results are reported per grade |
| Active ledge | A ledge only counts once price has left it: the latest RTH session did not trade through it |
| Leaving | Price extends 100 points or more beyond the edge |
| Retest | The first return to the edge after leaving. No session limit: the number of sessions until the retest is recorded |
| Hold | Price moves 75 points away from the edge before trading 25 points through it |
| Fail | Price trades 25 points through the edge before moving 75 points away |

Bullish case: balance left to the upside, retest from above, hold = support.
Bearish case: the mirror image.

## Still to decide

- How close price must come to the edge to count as a return (touch, or within about 5 points)
- What happens when neither 75 nor 25 points is reached by the end of the session

## Comparison

Hold rate at balance edges against the hold rate at ordinary prices that are
not edges, using the same 75/25 test. 75 points before 25 is a 3:1 payoff, so
the break-even hold rate is 25% before costs.

## Prerequisites

1. 1-second bars downloaded and loaded
2. Ledge detector checked against hand-marked ledges from screenshots (one screenshot checked so far, 7 Sep 2026: main ledge matched)
3. Count how often the setup occurs before running the full test

## Step 1: setup count (12 November 2026)

Counted before measuring any outcomes (`python src/find_setups.py`).
A setup = graded ledge, price leaves it by 100+ points on the thin side, then
returns to it for the first time. RTH bars only. 477 sessions.

| Grade | Setups | Return in a later session |
|---|---|---|
| A | 5 | 4 |
| B+ | 5 | 2 |
| B | 43 | 22 |
| C | 116 | 60 |
| All | 169 | 88 |

- Only 9 of the 169 came from a balance as defined above (VAH and VAL each
  within 25 points of the day before). That definition is too strict to use
  as a requirement.
- 81 of the 169 returned in the same session they left.
- 10 more ledges were left and had not been retested by the end of the data.

## Changes to the definitions before the outcome run (12 November 2026)

Made after the setup count and before any outcome was seen:

- Balance requirement dropped (too rare; the ledge grade does the same job)
- Hold changed from 75 to 50 points
- Entry at the near edge of the ledge zone; hold measured from the near edge;
  fail = 25 points beyond the far edge. Risk = zone width + 25 points
- Same-session returns count (every graded ledge comes from earlier sessions)
- The result of every trade is saved in R (table `results_001`)

Made after the first outcome run, to fix an artefact: setups where the
session opened already at or past the ledge are left out (24 of 169). Price
got there overnight, so there was no RTH retest to trade, and 19 of them
opened beyond the stop.

## Results (`python src/test_001.py`)

145 trades. Average zone width 20 points, average risk 45 points.

| Group | Trades | Hold % | Break-even % | Avg R | +/- |
|---|---|---|---|---|---|
| Ledges | 145 | 46.2 | 47.1 | +0.01 | 0.09 |
| Placebo (same trade 60 pts before the ledge) | 153 | 42.5 | 47.1 | -0.10 | 0.09 |
| Ledges, B and better | 45 | 48.9 | 45.7 | +0.09 | 0.17 |
| Ledges, C | 100 | 45.0 | 47.7 | -0.03 | 0.11 |
| Ledges, same-session return | 81 | 50.6 | 47.4 | +0.10 | 0.12 |
| Ledges, later-session return | 64 | 40.6 | 46.7 | -0.11 | 0.14 |

## Reading

- Traded mechanically with these rules, graded ledges break even: +0.01R per
  trade, and the uncertainty (0.09) is far larger than the result.
- Ledges did slightly better than the placebo, but the gap (0.11R) is within
  the noise for samples this size.
- No subgroup is distinguishable from zero. The grade ordering (B and better
  ahead of C) points the expected way but is not reliable at 45 trades.

## Limits

- The ledge detector has been checked against one hand-marked screenshot
- A fixed 50/25 trade with no order-flow confirmation is not how the level is
  actually traded
- Average risk (45 points) is wider than the 30-point maximum stop
- 145 trades can only detect a large edge (roughly 0.2R per trade or more)
