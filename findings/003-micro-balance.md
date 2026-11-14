# 003: Micro balance after a failed expansion

**Status:** two runs on 14 November 2026. Run 1 (no context rules): break-even.
Run 2 (open rule and expiry rule added): +0.38R per trade at the 60-point
target over 42 trades. Fresh-data run (May to December 2024): +0.05R over 13
trades. Unconfirmed lead; see the end of this note.

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

## Thin-volume idea, tested on the original period (14 November 2026)

Idea: a micro balance is more worth trading when the range between it and the
day's value was built on thin volume, showing the move back was aggressive
and the other side was not willing to participate.

Measure: volume at the thinnest point between the micro balance and the day's
POC, as a share of the POC's volume (whole-day profile, so it does not
separate the move up from the move back). "Thin" = 17% or less, which is the
middle value across all 194 setups, fixed before looking at results.

| Group | Trades | Win % (60) | Avg R (60) | +/- | Avg R (90) | +/- |
|---|---|---|---|---|---|---|
| Thin between | 17 | 47.1 | +0.60 | 0.42 | +0.35 | 0.52 |
| Not thin | 25 | 36.0 | +0.22 | 0.33 | -0.08 | 0.38 |

The direction supports the idea at both targets. 17 trades cannot confirm it.

By year, all 42 trades at the 60-point target: 2025 was -0.15R (16 trades),
2026 was +0.70R (26 trades). The result is not steady across the period.

## Fresh-data run

Two tests, both declared in advance, rules frozen as above:

1. All micro balance trades (run 2 rules)
2. Only the "thin between" ones (17% threshold unchanged)

Earlier history (`EARLY_START` in `src/config.py` up to January 2025) is
downloaded with `python src/download.py early`, and `python src/test_003.py`
then reports the fresh period separately for both.

### Result (14 November 2026)

Fresh period: 1 May 2024 to 31 December 2024, 174 sessions, never used to
choose any rule. Before costs. 60-point target unless stated.

| Group | Trades | Win % | Avg R | +/- | Avg R (90) |
|---|---|---|---|---|---|
| Test 1: all micro balances, FRESH | 13 | 30.8 | +0.05 | 0.45 | +0.06 |
| All micro balances, original period | 42 | 40.5 | +0.38 | 0.26 | +0.10 |
| Placebo, FRESH | 18 | 27.8 | -0.06 | 0.37 | +0.02 |
| Test 2: thin between, FRESH | 7 | 42.9 | +0.46 | 0.69 | +0.31 |
| Not thin, FRESH | 6 | 16.7 | -0.43 | 0.57 | -0.23 |

Both periods together (31 months):

| Group | Trades | Win % | Avg R | +/- | Avg R (90) |
|---|---|---|---|---|---|
| All micro balances | 55 | 38.2 | +0.30 | 0.22 | +0.09 |
| Thin between | 24 | 45.8 | +0.56 | 0.35 | +0.34 |
| Not thin | 31 | 32.3 | +0.10 | 0.29 | -0.11 |
| Placebo | 77 | 26.0 | -0.12 | 0.17 | -0.04 |

### Reading

- Test 1 did not confirm the original +0.38R: on fresh data the rules were
  about break-even (+0.05R). With 13 trades it does not refute it either.
- Test 2 kept its direction on fresh data: thin ahead of not thin at both
  targets. 7 and 6 trades are far too few to count as confirmation.
- Over 55 trades the setup is +0.30R at the 60-point target, about 1.4 times
  its uncertainty, and ahead of the placebo. Still not distinguishable from
  zero. The 90-point target shows nothing.
- Status: an unconfirmed lead. The cheapest further evidence is logging each
  new setup as it happens.

## Time-based versions of the thin idea (14 November 2026)

The whole-day measure above mixes the move out with the move back. These two
look only at bars after price last traded inside the micro balance, and only
at the range between the micro balance and the main balance (the stretch
around the POC with at least half the POC's volume).

| Measure | Definition | "Thin" |
|---|---|---|
| Volume per point | Volume traded in that range on the way back, per point, divided by the day's average volume per point | 0.30 or less |
| TPO count | Average number of 30-minute periods that traded at each row of that range on the way back (1 = single prints) | 1.61 or less |

Thresholds are the middle value across all 249 setups, so they use no
outcomes. All 55 trades (both periods), before costs:

| Group | Trades | Win % (60) | Avg R (60) | +/- | Avg R (90) |
|---|---|---|---|---|---|
| Volume per point: thin | 24 | 41.7 | +0.42 | 0.35 | -0.04 |
| Volume per point: not thin | 24 | 41.7 | +0.42 | 0.35 | +0.34 |
| TPO: thin | 21 | 52.4 | +0.78 | 0.38 | +0.10 |
| TPO: not thin | 27 | 33.3 | +0.13 | 0.31 | +0.19 |
| No range between micro balance and main balance | 7 | 14.3 | -0.51 | 0.49 | -0.34 |

### Reading

- Volume per point separates nothing: both halves are identical at 60 points.
- TPO count separates the trades at the 60-point target (+0.78R against
  +0.13R) but not at 90 points.
- This is the third "thin" measure tried on the same trades, with no unused
  data left. One of three looking good is what chance alone would often give.
- The TPO-thin trades and the whole-day-thin trades are mostly different
  trades (8 in common out of 21 and 24), so the two measures are not
  capturing the same thing.
- When the micro balance touches the main balance (no range between them),
  the trade lost 6 times out of 7. Small sample, but it fits the idea that a
  micro balance needs to be separate from value.

### Candidate rule for forward testing

Micro balance (run 2 rules) with a TPO-thin return leg, 60-point target.
To be judged only on setups that occur after 14 November 2026.
