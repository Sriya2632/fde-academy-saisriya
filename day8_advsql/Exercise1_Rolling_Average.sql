/* ============================================================================
   EXERCISE 1 — 30-Day Rolling Average Shipment Delay
   Intermediate · 50 minutes
   TechStar Group FDE Academy — Day 8: Advanced SQL

   Goal: compute a TRUE 30-calendar-day rolling average of delay_days,
   suitable for a Contour trend-line dashboard.

   Schema assumed:
     logistics_shipments (shipment_id, carrier_code, destination_region_id,
                           cost_usd, delay_days, shipped_date, status)
============================================================================ */


/* ----------------------------------------------------------------------
   STEP 1 + 2: Daily aggregation CTE + window function with RANGE
   ---------------------------------------------------------------------- */

-- STEP 1: Aggregate to daily level first.
-- Why: a rolling calendar-day window only makes sense on one row per day.
-- If you skip this and run the window function directly on raw shipment
-- rows, RANGE BETWEEN INTERVAL will treat MULTIPLE shipments on the same
-- day as separate points, which is not what "daily average" means.
WITH daily_delays AS (
    SELECT
        shipped_date,
        AVG(delay_days) AS avg_delay_that_day
    FROM logistics_shipments
    GROUP BY shipped_date
)

-- STEP 2: Apply the window function with RANGE (not ROWS).
-- RANGE BETWEEN INTERVAL '29 days' PRECEDING AND CURRENT ROW means:
-- "look back 29 calendar days from today's date, plus today = 30 days total"
-- This correctly handles days with NO shipments (gap days) because RANGE
-- looks at the VALUE of shipped_date, not the number of physical rows.
SELECT
    shipped_date,
    avg_delay_that_day,
    AVG(avg_delay_that_day) OVER (
        ORDER BY shipped_date
        RANGE BETWEEN INTERVAL '29 days' PRECEDING AND CURRENT ROW
    ) AS rolling_30day_avg_delay
FROM daily_delays
ORDER BY shipped_date;


/* ----------------------------------------------------------------------
   STEP 3: ROWS vs RANGE comparison on the same data (required deliverable)
   This shows WHY the two frame types can disagree whenever there are gap
   days (a date with zero shipments, so no row exists for it).
   ---------------------------------------------------------------------- */

WITH daily_delays AS (
    SELECT
        shipped_date,
        AVG(delay_days) AS avg_delay_that_day
    FROM logistics_shipments
    GROUP BY shipped_date
)
SELECT
    shipped_date,
    avg_delay_that_day,

    -- ROWS: counts the last 30 PHYSICAL ROWS, regardless of date gaps
    AVG(avg_delay_that_day) OVER (
        ORDER BY shipped_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS rolling_avg_rows_based,

    -- RANGE: counts the last 30 CALENDAR DAYS by value, gap-safe
    AVG(avg_delay_that_day) OVER (
        ORDER BY shipped_date
        RANGE BETWEEN INTERVAL '29 days' PRECEDING AND CURRENT ROW
    ) AS rolling_avg_range_based

FROM daily_delays
ORDER BY shipped_date;


/* ----------------------------------------------------------------------
   STEP 4: Validate output
   Sanity checks to run manually against the result sets above:
     a) rolling_30day_avg_delay for the FIRST date should equal
        avg_delay_that_day for that same date (window of 1 day).
     b) Find any date where rolling_avg_rows_based != rolling_avg_range_based
        -- every such date should correspond to a gap in shipped_date nearby.
     c) rolling_30day_avg_delay should never be NULL once at least one row
        exists on or before that date.
   ---------------------------------------------------------------------- */
