-- ============================================================================
-- Day 7 -- Exercise 2: 10 Business Queries -- Operational KPIs
-- ============================================================================

-- Q1: How many total shipments are currently delayed?
SELECT COUNT(*) AS delayed_count
FROM logistics_shipments
WHERE status = 'delayed';

-- Q2: What is the total shipment cost handled by each carrier?
SELECT carrier, SUM(cost_usd) AS total_cost
FROM logistics_shipments
GROUP BY carrier
ORDER BY total_cost DESC;

-- Q3: Which carrier has the highest average delay in days?
SELECT carrier, AVG(delay_days) AS avg_delay
FROM logistics_shipments
GROUP BY carrier
ORDER BY avg_delay DESC
LIMIT 1;

-- Q4: List the top 5 most expensive shipments, with shipment_id, carrier, and cost.
SELECT shipment_id, carrier, cost_usd
FROM logistics_shipments
ORDER BY cost_usd DESC
LIMIT 5;

-- Q5: What percentage of all shipments are delivered on time
--     (status='delivered' AND delay_days=0)?
-- This is the OTIF (On Time In Full) percentage -- a core logistics KPI.
SELECT
    ROUND(
        100.0 * SUM(CASE WHEN status = 'delivered' AND delay_days = 0 THEN 1 ELSE 0 END)
        / COUNT(*),
        1
    ) AS otif_pct
FROM logistics_shipments;

-- Q6: Which origin-destination route has the highest shipment volume?
SELECT origin_city, destination_city, COUNT(*) AS shipment_count
FROM logistics_shipments
GROUP BY origin_city, destination_city
ORDER BY shipment_count DESC
LIMIT 1;

-- Q7: Find all carriers whose average shipment cost exceeds $300.
-- HAVING question -- filtering happens AFTER aggregation.
SELECT carrier, AVG(cost_usd) AS avg_cost
FROM logistics_shipments
GROUP BY carrier
HAVING AVG(cost_usd) > 300;

-- Q8: How many shipments per status category, sorted from most to least common?
SELECT status, COUNT(*) AS shipment_count
FROM logistics_shipments
GROUP BY status
ORDER BY shipment_count DESC;

-- Q9: What is the total weight (kg) shipped by DHL specifically?
SELECT SUM(weight_kg) AS total_weight_kg
FROM logistics_shipments
WHERE carrier = 'DHL';

-- Q10: Which 3 destination cities receive the most delayed shipments?
SELECT destination_city, COUNT(*) AS delayed_count
FROM logistics_shipments
WHERE status = 'delayed'
GROUP BY destination_city
ORDER BY delayed_count DESC
LIMIT 3;

-- ---------------------------------------------------------------------------
-- Bonus (from Reflection Question 2): OTIF% PER CARRIER instead of overall
-- ---------------------------------------------------------------------------
SELECT
    carrier,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'delivered' AND delay_days = 0 THEN 1 ELSE 0 END)
        / COUNT(*),
        1
    ) AS otif_pct
FROM logistics_shipments
GROUP BY carrier
ORDER BY otif_pct DESC;
