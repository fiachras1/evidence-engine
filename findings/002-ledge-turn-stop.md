# 002: Ledge retest with a stop behind the turn

**Status:** run on 14 November 2026. No edge found; the tight stop did worse than the wide one.
**Defined:** 12 November 2026

## Question

Test 001 traded graded ledges with a wide fixed stop (zone width + 25 points,
45 points on average) and broke even. Does the same setup pay with a tight
stop placed behind the turn that price makes at the ledge?

## Plan (fixed before any results are seen)

Same setups as test 001: graded ledge, price leaves by 100+ points, first
return, RTH only, sessions that open at or past the ledge left out.

| Term | Definition |
|---|---|
| Turn | The extreme price makes at the ledge before it first moves away |
| Stop | 5 points beyond the turn |
| Maximum stop | 20 points |
| Targets | 60 points and 90 points, each reported separately |
| Result | Saved per trade in R |

Also measured: how often price makes a second high (or low) beyond the first
turn before reversing, and by how many points.

## Decided before the run (14 November 2026)

- The turn counts as made once price has moved 10 points away from its extreme
- Entry at that moment, so the stop is always 15 points (10 + 5 beyond the turn)
- No trade if price goes 25 points past the far edge of the ledge before turning
- Targets are measured from the entry: 60 points = 4R, 90 points = 6R
- 1-second RTH bars

## Note

Two targets are declared here in advance. Picking the better of the two
afterwards would overstate the result, so both are reported.

## Results (`python src/test_002.py`)

169 setups: 24 opened at or past the ledge (left out), 3 went through without
turning, 142 trades. Before costs.

| Group | Trades | Win % | Break-even % | Avg R | +/- |
|---|---|---|---|---|---|
| Ledges, 60-point target | 142 | 16.2 | 20.0 | -0.19 | 0.16 |
| Placebo, 60-point target | 145 | 18.6 | 20.0 | -0.07 | 0.16 |
| Ledges, 90-point target | 142 | 12.7 | 14.3 | -0.11 | 0.20 |
| Placebo, 90-point target | 145 | 9.7 | 14.3 | -0.32 | 0.17 |
| Ledges B and better, 60 | 44 | 18.2 | 20.0 | -0.09 | 0.29 |
| Ledges B and better, 90 | 44 | 15.9 | 14.3 | +0.11 | 0.39 |

### Second highs and lows

After the first turn, before price reached 60 points from the entry:

| What happened | Trades | % | Median points beyond the turn |
|---|---|---|---|
| Turn held exactly, reached 60 | 16 | 11.3 | 0 |
| Second high/low within the 5-point stop, reached 60 | 8 | 5.6 | 3.0 |
| Second high/low beyond the stop, then reached 60 | 31 | 21.8 | 21.25 |
| Never reached 60: ledge failed (25 past the far edge) | 87 | 61.3 | 39.0 |

## Reading

- Nothing here is distinguishable from zero, and ledges did not beat the
  placebo consistently (worse at 60, better at 90).
- 55 of the 142 ledges (39%) did go on to reach 60 points. The 15-point stop
  survived only 24 of those 55. In the other 31 the first turn was not the
  real one: price went a median 21 points beyond it first (45.75 at most).
- So the first 10-point turn is usually not the turn. A 10-point move on NQ
  is small enough to happen in seconds as noise.
- A buffer wide enough to survive most second highs/lows (20 to 45 points) is
  the wide stop of test 001 again, which broke even.

## Limits

- Same as test 001: detector checked against one screenshot, no order-flow
  trigger, sample only large enough to see an edge of roughly 0.3R or more
  at these payoffs
- Costs are not included. At a 15-point stop, 1 point of commission and
  slippage per trade is about 0.07R
