# 003: Micro balance after a failed expansion

**Status:** two runs on 14 November 2026. Run 1 (no context rules): break-even.
Run 2 (open rule and expiry rule added): +0.38R per trade at the 60-point
target over 42 trades, which is too few to rely on. Needs confirming on data
the rules have never seen.

## Question

Price expands out of the previous day's value, builds a small balance at the
extreme, then reverses back. When price later returns to that micro balance,
does it act as resistance (at a high) or support (at a low)?

Market logic: value started to build at the extreme but not enough
participants accepted it, so the side that pushed there could not hold it.

## Definitions (fixed before the run)

| Term | Definition |
|---|---|
| Expansion | The day's high is 100+ points above the previous day's VAH (mirror for lows) |
| Micro balance | A separate node at the day's extreme: split from the rest of the daily profile by an LVN, holding 5-25% of the day's volume, entirely outside the previous day's value area. Its zone is where its volume is at least half its peak |
| Reversal | The day closes back out of the micro balance |
| Retest | The first time a later RTH session trades back to the near edge. Sessions that open at or past it are left out |
| Trade | Enter at the near edge, stop 25 points from entry, targets 60 and 90 points from entry (2.4R and 3.6R), each reported separately |
| Placebo | The same trade 60 points before the micro balance |

1-second RTH bars. 477 sessions. Before costs.

## Counts

| Step | Count |
|---|---|
| Day-ends that expanded 100+ points beyond the previous value | 424 |
| ...with a micro balance at the extreme | 238 |
| ...that closed back out of it (setups) | 194 |
| Session opened at or past the level (left out) | 74 |
| Never retested | 9 |
| Trades | 111 |

## Results (`python src/test_003.py`)

| Group | Trades | Win % | Break-even % | Avg R | +/- |
|---|---|---|---|---|---|
| Micro balance, 60-point target | 111 | 31.5 | 29.4 | +0.07 | 0.15 |
| Placebo, 60-point target | 94 | 31.9 | 29.4 | +0.09 | 0.16 |
| Micro balance, 90-point target | 111 | 21.6 | 21.7 | -0.01 | 0.18 |
| Placebo, 90-point target | 94 | 27.7 | 21.7 | +0.27 | 0.21 |
| At the high (sell), 60 | 61 | 36.1 | 29.4 | +0.23 | 0.21 |
| At the low (buy), 60 | 50 | 26.0 | 29.4 | -0.12 | 0.21 |

## Reading

- Break-even at both targets, and no better than the placebo.
- Selling micro balances at highs did better than buying them at lows, but
  neither is distinguishable from zero at this sample size.

## Limits

- The detector finds a "micro balance" on roughly 40% of sessions, which is
  probably far more often than one would be marked by hand. The test may be
  measuring ordinary end-of-profile nodes, not the pattern in the hypothesis.
- 100 points beyond the previous value is not selective on NQ: almost every
  day does it on one side.
- No order-flow trigger; costs not included.

## Run 2: context rules added (14 November 2026)

After run 1, two of the engine's candidates (3 and 4 September 2026) were
checked by eye: they are real micro balances, but not ones that would be
traded. Two rules were added from how the level is actually traded, not from
the outcomes:

| Rule | Definition |
|---|---|
| Open rule | The retest is only traded if that session opens in the far half of the micro balance day's value area, or beyond it (for a short at a high: the lower half or below) |
| Expiry rule | A micro balance more than 5 sessions old is ruled out once it lies outside the 5-day profile's high-to-low range |
| Main balance | The node containing the day's POC (not yet used by the test) |

The first return still consumes the level whether or not it is traded.

Of the 194 setups: 107 had the wrong open, 36 had expired, 9 were never
retested, 42 were traded.

| Group | Trades | Win % | Break-even % | Avg R | +/- |
|---|---|---|---|---|---|
| Micro balance, 60-point target | 42 | 40.5 | 29.4 | +0.38 | 0.26 |
| Placebo, 60-point target | 59 | 25.4 | 29.4 | -0.14 | 0.19 |
| Micro balance, 90-point target | 42 | 23.8 | 21.7 | +0.10 | 0.31 |
| Placebo, 90-point target | 59 | 20.3 | 21.7 | -0.06 | 0.24 |
| At the high (sell), 60 | 21 | 38.1 | 29.4 | +0.30 | 0.37 |
| At the low (buy), 60 | 21 | 42.9 | 29.4 | +0.46 | 0.38 |

### Reading

- First positive result in the project, and it beats the placebo at both
  targets and in both directions.
- It is about 1.5 times its own uncertainty. A result this size would appear
  by luck roughly 1 time in 7 with no edge at all, and this is the third
  idea tested with several variants, which makes a lucky one more likely.
- The rules were added after run 1. They came from trading logic, not from
  the results, but the only clean confirmation is data never used so far.

### Next step

Freeze these rules. Run them once on earlier history (before January 2025)
and treat that as the real test.
