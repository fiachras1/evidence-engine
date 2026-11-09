# Evidence Engine

A Python and SQL pipeline that rebuilds my hand-logged NQ session stats from
historical data, then tests the beliefs in my trading framework against them.

## Pipeline

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `src/download.py` | Downloads NQ 1-minute bars from Databento |
| 2 | `src/load.py` | Loads them into DuckDB as `bars_1m` |
| 3 | `src/build_sessions.py` | Runs `sql/sessions.sql` to build one row per trading day |

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
```

The date range and symbol are set in `src/config.py`.

## Notes

- Session times are defined in New York time: RTH 09:30-16:00, IB 09:30-10:30,
  overnight from 18:00 the evening before.
- `NQ.v.0` is the front-month contract rolled by volume. Prices are the real
  traded prices and are not back-adjusted, so there is a price jump at each
  quarterly roll. Daily stats are unaffected; multi-day composites that span
  a roll are.
- `rth_bars` far below 390 marks a half day.
- `data/` and `.env` are git-ignored.

## Findings

One short note per tested belief goes in `findings/`: question, method,
result, sample size.
