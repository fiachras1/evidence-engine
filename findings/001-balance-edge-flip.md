# 001: Balance-edge flip

**Status:** defined, not yet run. Waiting on 1-second data and the ledge-detector check.
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

## Results

Not yet run.
