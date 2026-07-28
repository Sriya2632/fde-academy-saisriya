/* ============================================================================
   EXERCISE 3 — Top-3 Underperforming Regions — Multi-Join
   Intermediate · 50 minutes
   TechStar Group FDE Academy — Day 8: Advanced SQL

   Goal: identify the 3 worst regions by avg delay, filtered for statistical
   significance, using a defensible/auditable selection method.

   Schema assumed:
     logistics_shipments (shipment_id, carrier_code, destination_region_id,
                           cost_usd, delay_days, shipped_date, status)
     regions             (region_id, region_name, country)
============================================================================ */

WITH

-- ----------------------------------------------------------------------
-- Step 1: region_stats
-- Region-level aggregates via an INNER JOIN — every shipment here must
-- have a valid region, since we're producing a ranked, client-facing
-- deliverable.
-- ----------------------------------------------------------------------
region_stats AS (
    SELECT
        r.region_name,
        COUNT(*)               AS shipment_count,
        AVG(s.delay_days)      AS avg_delay,
        SUM(s.cost_usd)        AS total_cost
    FROM logistics_shipments s
    INNER JOIN regions r
        ON s.destination_region_id = r.region_id
    GROUP BY r.region_name
    -- HAVING filters on the AGGREGATE, after GROUP BY — this is the
    -- statistical-significance guard: don't rank a region with only
    -- 3 shipments as "worst," since its average is noise, not signal.
    HAVING COUNT(*) >= 500
),

-- ----------------------------------------------------------------------
-- Step 2: region_ranked
-- Rank regions by average delay, worst first.
-- ROW_NUMBER() is used instead of a plain ORDER BY + LIMIT 3, because:
--   1. You CANNOT filter a window function directly in WHERE
--      (WHERE ROW_NUMBER() OVER (...) <= 3 is illegal SQL) — it must be
--      computed in one CTE/subquery and filtered in the query that wraps it.
--   2. ROW_NUMBER + WHERE rank <= 3 makes the exact tie-breaking rule
--      explicit and auditable for a client deliverable, rather than
--      relying on LIMIT's implicit, engine-dependent row order.
-- ----------------------------------------------------------------------
region_ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY avg_delay DESC) AS underperformance_rank
    FROM region_stats
)

SELECT
    region_name,
    shipment_count,
    avg_delay,
    total_cost
FROM region_ranked
WHERE underperformance_rank <= 3
ORDER BY underperformance_rank;
