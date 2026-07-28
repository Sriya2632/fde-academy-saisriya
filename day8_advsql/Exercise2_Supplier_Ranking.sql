/* ============================================================================
   EXERCISE 2 — Supplier Performance Ranking via 3-CTE Chain
   Advanced · 60 minutes
   TechStar Group FDE Academy — Day 8: Advanced SQL

   Goal: rank ALL contracted carriers — including ones with zero shipments —
   on OTIF%, average delay, and total revenue.

   Schema assumed:
     logistics_shipments (shipment_id, carrier_code, destination_region_id,
                           cost_usd, delay_days, shipped_date, status)
     carriers            (carrier_code, carrier_name, sla_days)
============================================================================ */

WITH

-- ----------------------------------------------------------------------
-- CTE 1: carrier_raw_stats
-- LEFT JOIN carriers -> shipments (carriers is the LEFT/base table here).
-- This is the critical design choice: if we used INNER JOIN, any carrier
-- with zero shipments (e.g. a newly onboarded or idle carrier like DTDC)
-- would silently disappear from the scorecard. A procurement/ops report
-- must show ALL contracted carriers, active or not.
-- ----------------------------------------------------------------------
carrier_raw_stats AS (
    SELECT
        c.carrier_code,
        c.carrier_name,
        COUNT(s.shipment_id)                                   AS total_shipments,
        AVG(s.delay_days)                                      AS avg_delay,
        SUM(s.cost_usd)                                        AS total_revenue,
        SUM(CASE WHEN s.status = 'delivered' AND s.delay_days = 0
                 THEN 1 ELSE 0 END)                             AS otif_shipments
    FROM carriers c
    LEFT JOIN logistics_shipments s
        ON s.carrier_code = c.carrier_code
    GROUP BY c.carrier_code, c.carrier_name
),

-- ----------------------------------------------------------------------
-- CTE 2: carrier_otif
-- NULL-safe percentage calculation. A carrier with total_shipments = 0
-- would cause a divide-by-zero error with a plain division, so we use
-- NULLIF to turn a 0 denominator into NULL instead of erroring, which
-- makes otif_pct NULL (correctly "not applicable") for idle carriers
-- rather than crashing the whole query.
-- ----------------------------------------------------------------------
carrier_otif AS (
    SELECT
        carrier_code,
        carrier_name,
        total_shipments,
        avg_delay,
        total_revenue,
        ROUND(
            100.0 * otif_shipments / NULLIF(total_shipments, 0),
        1) AS otif_pct
    FROM carrier_raw_stats
),

-- ----------------------------------------------------------------------
-- CTE 3: carrier_ranked
-- Rank across three dimensions. NULLS LAST ensures idle carriers (whose
-- otif_pct/avg_delay are NULL) sink to the bottom of each ranking instead
-- of sorting unpredictably to the top (Postgres default is NULLS LAST for
-- ASC and NULLS FIRST for DESC, so we make it explicit rather than rely
-- on that default).
-- ----------------------------------------------------------------------
carrier_ranked AS (
    SELECT
        carrier_code,
        carrier_name,
        total_shipments,
        otif_pct,
        avg_delay,
        total_revenue,
        RANK() OVER (ORDER BY otif_pct DESC NULLS LAST)       AS otif_rank,
        RANK() OVER (ORDER BY avg_delay ASC NULLS LAST)       AS delay_rank,
        RANK() OVER (ORDER BY total_revenue DESC NULLS LAST)  AS revenue_rank
    FROM carrier_otif
)

SELECT
    carrier_name,
    total_shipments,
    otif_pct,      otif_rank,
    avg_delay,     delay_rank,
    total_revenue, revenue_rank
FROM carrier_ranked
ORDER BY otif_rank;
