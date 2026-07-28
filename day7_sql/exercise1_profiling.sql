-- ============================================================================
-- Day 7 -- Exercise 1: Profiling a 100K-Row Logistics Dataset
-- ============================================================================

-- ---------------------------------------------------------------------------
-- TASK 1: Volume & Structure
-- ---------------------------------------------------------------------------

-- Q1.1: Total row count
SELECT COUNT(*) AS total_rows
FROM logistics_shipments;

-- Q1.2: Look at 10 real rows -- never skip this step
SELECT * FROM logistics_shipments LIMIT 10;

-- Q1.3: Date range covered by the data
SELECT
    MIN(shipped_date) AS earliest_date,
    MAX(shipped_date) AS latest_date
FROM logistics_shipments;

-- ---------------------------------------------------------------------------
-- TASK 2: Categorical Column Profiling
-- ---------------------------------------------------------------------------

-- Q2.1: What are all the distinct carrier values?
SELECT DISTINCT carrier
FROM logistics_shipments;

-- Q2.2: How many shipments does each carrier have? (most to least)
SELECT carrier, COUNT(*) AS shipment_count
FROM logistics_shipments
GROUP BY carrier
ORDER BY COUNT(*) DESC;

-- Q2.3: What are all the distinct status values, and how common is each?
SELECT status, COUNT(*) AS status_count
FROM logistics_shipments
GROUP BY status
ORDER BY COUNT(*) DESC;

-- Q2.4: Which origin_city appears most frequently?
SELECT origin_city, COUNT(*) AS shipment_count
FROM logistics_shipments
GROUP BY origin_city
ORDER BY COUNT(*) DESC
LIMIT 1;

-- Bonus, following the same pattern for destination_city (mentioned in the
-- task instructions as "repeat the pattern for ... destination_city")
SELECT destination_city, COUNT(*) AS shipment_count
FROM logistics_shipments
GROUP BY destination_city
ORDER BY COUNT(*) DESC;

-- ---------------------------------------------------------------------------
-- TASK 3: NULL Audit & Numeric Range Check
-- ---------------------------------------------------------------------------

-- Q3.1: NULL audit across all business-critical columns in ONE query
SELECT
    COUNT(*)                         AS total_rows,
    COUNT(*) - COUNT(carrier)        AS null_carrier,
    COUNT(*) - COUNT(status)         AS null_status,
    COUNT(*) - COUNT(cost_usd)       AS null_cost,
    COUNT(*) - COUNT(delay_days)     AS null_delay,
    COUNT(*) - COUNT(delivered_date) AS null_delivered_date
FROM logistics_shipments;

-- Q3.2: Numeric range check -- min/max/avg for cost_usd, delay_days, weight_kg
-- Look closely at the minimum values -- do any look implausible?
SELECT
    MIN(cost_usd)    AS min_cost,   MAX(cost_usd)    AS max_cost,   AVG(cost_usd)    AS avg_cost,
    MIN(delay_days)  AS min_delay,  MAX(delay_days)  AS max_delay,  AVG(delay_days)  AS avg_delay,
    MIN(weight_kg)   AS min_weight, MAX(weight_kg)   AS max_weight, AVG(weight_kg)   AS avg_weight
FROM logistics_shipments;

-- Q3.3: Round the average cost to 2 decimal places for clean reporting
SELECT ROUND(AVG(cost_usd), 2) AS avg_cost_usd
FROM logistics_shipments;
