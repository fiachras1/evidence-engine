# Evidence Engine

A Python and SQL pipeline that rebuilds my hand-logged NQ session stats from
historical data, then tests the beliefs in my trading framework against them.

## Pipeline

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `src/download.py` | Downloads NQ 1-minute bars from Databento |
| 2 | `src/load.py` | Loads them into DuckDB as `bars_1m` |
| 3 | `src/build_sessions.py` | Runs `sql/sessions.sql` to build one row per trading day |
| 4 | `src/build_profiles.py` | Builds daily, 5-day and 20-day volume profiles: POC, value area, HVNs, LVNs, ledges |

`sessions` columns: RTH open/high/low/close, IB high/low, IB extension
direction and size, IB as % of RTH range, overnight high/low, RTH volume.

## Setup (once)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then paste your Databento API key into .env
```

## Run

```bash
source .venv/bin/activate
python src/download.py          # shows the cost only
python src/download.py --yes    # downloads
python src/load.py
python src/build_sessions.py
python src/build_profiles.py
```

Look at results:

```bash
python src/show_day.py 2026-08-19          # session stats
python src/show_profile.py 2026-11-06 5    # 5-day profile ending that day, with chart
```

The date range and symbol are set in `src/config.py`.

## Notes

- Session times are defined in New York time: RTH 09:30-16:00, IB 09:30-10:30,
  overnight from 18:00 the evening before.
- `NQ.v.0` is the front-month contract rolled by volume. Prices are the real
  traded prices and are not back-adjusted, so there is a price jump at each
  quarterly roll. Daily stats are unaffected; multi-day composites that span
  a roll are.
- `full_day` is FALSE on US holidays and half days (CME trades a short session
  while stocks are closed). Filter these out when testing beliefs.
- `data/` and `.env` are git-ignored.

## Volume profiles

- Built from 1-second bars when downloaded (`python src/download.py 1s`),
  otherwise from 1-minute bars. A bar's volume is spread evenly from its low
  to its high: a few ticks for 1-second bars, about 24 points on average for
  1-minute bars, which is only good for coarse structure.
- Ticks are grouped into rows of `ROW_TICKS` (5 ticks = 1.25 points).
- A profile row dated D covers the N sessions ending on D, D included. The
  levels available going into a trading day are the previous session's row.
- Composites that span a quarterly roll shift the older contract's prices by
  the roll gap, and are marked `spans_roll`.
- HVN / LVN / ledge detection settings are in `src/config.py`.

## Findings

One short note per tested belief goes in `findings/`: question, method,
result, sample size.
