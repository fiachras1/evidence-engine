# 002: Ledge retest with a stop behind the turn

**Status:** planned, not yet run.
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

## Still to decide

- How far price must move away from the ledge for the turn to count as made
- Where the entry is: at the near edge as in test 001, or once the turn is made
- What happens when the stop would be wider than 20 points: skip the trade, or cap it

## Note

Two targets are declared here in advance. Picking the better of the two
afterwards would overstate the result, so both are reported.

## Results

Not yet run.
