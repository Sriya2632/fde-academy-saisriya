-- ============================================================================
-- Day 7 -- SQL Basics: Practice Database Setup
-- Run this once to create the logistics_shipments table used across all
-- three exercises. Generates 100,000 rows with realistic data AND
-- deliberately injected quality issues for Exercise 3.
-- ============================================================================

DROP TABLE IF EXISTS logistics_shipments;

CREATE TABLE logistics_shipments (
    shipment_id       VARCHAR(12) PRIMARY KEY,
    carrier           VARCHAR(20),
    origin_city       VARCHAR(50),
    destination_city  VARCHAR(50),
    status            VARCHAR(20),
    delay_days        INTEGER,
    cost_usd          NUMERIC(10,2),
    weight_kg         NUMERIC(8,2),
    shipped_date      DATE,
    delivered_date    DATE
);

-- Generate 100,000 rows with realistic distributions
-- (including ~3% negative delay_days and ~2% zero/negative cost_usd,
--  deliberately injected dirty data for Exercise 3)
INSERT INTO logistics_shipments
SELECT
    'SH' || LPAD(g::text, 6, '0')                                            AS shipment_id,
    (ARRAY['DHL', 'FEDEX', 'BLUEDART', 'DHL', 'FEDEX'])[1 + (random() * 4)::int]           AS carrier,
    (ARRAY['Mumbai', 'Chennai', 'Pune', 'Delhi', 'Hyderabad', 'Bangalore'])[1 + (random() * 5)::int] AS origin_city,
    (ARRAY['Delhi', 'Bangalore', 'Mumbai', 'Chennai', 'Pune', 'Hyderabad'])[1 + (random() * 5)::int] AS destination_city,
    (ARRAY['delivered', 'in_transit', 'delayed', 'pending'])[1 + (random() * 3)::int]      AS status,
    CASE
        WHEN random() < 0.03 THEN -1                     -- ~3% dirty: negative delay
        ELSE (random() * 10)::int
    END                                                                        AS delay_days,
    CASE
        WHEN random() < 0.02 THEN 0                       -- ~2% dirty: zero cost
        ELSE ROUND((50 + random() * 450)::numeric, 2)
    END                                                                        AS cost_usd,
    ROUND((1 + random() * 500)::numeric, 2)                                    AS weight_kg,
    DATE '2024-01-01' + (random() * 180)::int                                  AS shipped_date,
    DATE '2024-01-01' + (random() * 180)::int + (random() * 10)::int           AS delivered_date
FROM generate_series(1, 100000) AS g;

-- Verify the load
SELECT COUNT(*) FROM logistics_shipments;  -- Should return 100000
