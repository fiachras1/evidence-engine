-- Step 4: one row per trading day.
-- All session times are New York time, so the weeks when Irish and US clocks
-- change on different dates are handled automatically.
--   RTH       09:30-16:00 ET
--   IB        09:30-10:30 ET (first hour of RTH)
--   Overnight 18:00 ET the evening before, up to 09:30 ET

CREATE OR REPLACE TABLE sessions AS
WITH bars AS (
    SELECT
        ts_event,
        ts_event AT TIME ZONE 'America/New_York' AS ts_ny,   -- NY wall-clock time
        open, high, low, close, volume
    FROM bars_1m
),
tagged AS (
    SELECT
        *,
        CAST(ts_ny AS TIME) AS t,
        CASE
            WHEN CAST(ts_ny AS TIME) >= TIME '09:30' AND CAST(ts_ny AS TIME) < TIME '16:00' THEN 'RTH'
            WHEN CAST(ts_ny AS TIME) >= TIME '18:00' OR  CAST(ts_ny AS TIME) < TIME '09:30' THEN 'ON'
        END AS segment,
        -- bars from 18:00 onward belong to the NEXT day's session
        CASE
            WHEN CAST(ts_ny AS TIME) >= TIME '18:00' THEN CAST(ts_ny AS DATE) + 1
            ELSE CAST(ts_ny AS DATE)
        END AS session_date
    FROM bars
),
rth AS (
    SELECT
        session_date,
        arg_min(open, ts_event)  AS rth_open,
        max(high)                AS rth_high,
        min(low)                 AS rth_low,
        arg_max(close, ts_event) AS rth_close,
        sum(volume)              AS rth_volume,
        max(high) FILTER (WHERE t < TIME '10:30') AS ib_high,
        min(low)  FILTER (WHERE t < TIME '10:30') AS ib_low,
        count(*)                 AS rth_bars
    FROM tagged
    WHERE segment = 'RTH'
    GROUP BY session_date
),
overnight AS (
    SELECT session_date, max(high) AS on_high, min(low) AS on_low
    FROM tagged
    WHERE segment = 'ON'
    GROUP BY session_date
)
SELECT
    r.session_date,
    r.rth_open, r.rth_high, r.rth_low, r.rth_close,
    round(r.rth_high - r.rth_low, 2)          AS rth_range,
    r.ib_high, r.ib_low,
    round(r.ib_high - r.ib_low, 2)            AS ib_range,
    round(greatest(r.rth_high - r.ib_high, 0), 2) AS ext_up_pts,
    round(greatest(r.ib_low - r.rth_low, 0), 2)   AS ext_down_pts,
    CASE
        WHEN r.rth_high > r.ib_high AND r.rth_low < r.ib_low THEN 'both'
        WHEN r.rth_high > r.ib_high THEN 'up'
        WHEN r.rth_low  < r.ib_low  THEN 'down'
        ELSE 'none'
    END                                       AS ib_extension,
    round(100 * (r.ib_high - r.ib_low) / nullif(r.rth_high - r.rth_low, 0), 1) AS ib_pct_of_range,
    o.on_high, o.on_low,
    r.rth_volume,
    r.rth_bars            -- a full day is about 390; far fewer means a half day
FROM rth r
LEFT JOIN overnight o USING (session_date)
ORDER BY r.session_date;
