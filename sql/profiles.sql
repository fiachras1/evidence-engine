-- Volume profile building blocks (RTH only, 09:30-16:00 New York time).
--
-- profile_daily      volume at every price for every session
-- session_contract   which futures contract each session traded, and the
--                    price gap at each quarterly roll

-- A bar only tells us its high, low and volume, not where inside the bar the
-- volume traded. So each bar's volume is spread evenly across every tick from
-- its low to its high. With 1-second bars that range is usually a few ticks,
-- so very little is estimated. With 1-minute bars it averages about 24 points.
-- profile_bars is set by build_profiles.py: bars_1s if downloaded, else bars_1m.
CREATE OR REPLACE TABLE profile_daily AS
WITH rth AS (
    SELECT CAST(ts_ny AS DATE) AS session_date, low, high, volume
    FROM (SELECT *, ts_event AT TIME ZONE 'America/New_York' AS ts_ny FROM profile_bars)
    WHERE CAST(ts_ny AS TIME) >= TIME '09:30' AND CAST(ts_ny AS TIME) < TIME '16:00'
),
spread AS (
    SELECT
        session_date,
        -- one row per tick between the bar's low and high (prices x4 = whole ticks)
        unnest(range(CAST(round(low * 4) AS BIGINT), CAST(round(high * 4) AS BIGINT) + 1)) AS tick,
        volume / (round((high - low) * 4) + 1) AS vol
    FROM rth
)
SELECT session_date, tick / 4.0 AS price, sum(vol) AS volume
FROM spread
GROUP BY session_date, tick
ORDER BY session_date, tick;

-- The data is the front-month contract with real prices, so price jumps by
-- 200-300 points at each quarterly roll. roll_gap_total is the running sum of
-- those jumps; composites use it to line older sessions up with newer ones.
CREATE OR REPLACE TABLE session_contract AS
WITH bars AS (
    SELECT
        ts_event, instrument_id, open,
        lag(instrument_id) OVER (ORDER BY ts_event) AS prev_id,
        lag(close)         OVER (ORDER BY ts_event) AS prev_close
    FROM bars_1m
),
running AS (
    SELECT
        ts_event, instrument_id,
        sum(CASE WHEN instrument_id <> prev_id THEN open - prev_close ELSE 0 END)
            OVER (ORDER BY ts_event) AS roll_gap_total
    FROM bars
),
rth AS (
    SELECT *, ts_event AT TIME ZONE 'America/New_York' AS ts_ny FROM running
)
SELECT
    CAST(ts_ny AS DATE)                  AS session_date,
    arg_min(instrument_id, ts_event)     AS instrument_id,
    arg_min(roll_gap_total, ts_event)    AS roll_gap_total
FROM rth
WHERE CAST(ts_ny AS TIME) >= TIME '09:30' AND CAST(ts_ny AS TIME) < TIME '16:00'
GROUP BY CAST(ts_ny AS DATE)
ORDER BY session_date;
