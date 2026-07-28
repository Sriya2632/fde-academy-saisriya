/* ============================================================================
   DAY 8 SETUP SCRIPT (v2 — matches your actual logistics_shipments schema)
   TechStar Group FDE Academy

   Confirmed real schema via \d logistics_shipments:
     shipment_id            character varying(12)   PRIMARY KEY, NOT NULL
     carrier                character varying(20)
     origin_city            character varying(50)
     destination_city       character varying(50)
     status                 character varying(20)
     delay_days             integer
     cost_usd               numeric(10,2)
     weight_kg              numeric(8,2)
     shipped_date           date
     delivered_date         date
     carrier_code           character varying(10)   -- already added, already backfilled
     destination_region_id  integer                 -- already added, already backfilled

   Since carrier_code and destination_region_id already exist and are
   already backfilled on all 100,000 Day 7 rows (confirmed by your last
   run — both UPDATEs succeeded), this version SKIPS the ALTER TABLE /
   UPDATE steps and only does what's still needed:
     1. Creates carriers + regions reference tables (safe no-op if they
        already exist from your last run)
     2. Re-seeds them (safe no-op via ON CONFLICT DO NOTHING)
     3. Inserts a fresh batch of sample shipments with a correctly
        generated shipment_id (varchar, not auto-increment)

   Run with:
     psql -d logistics_practice -f Day8_Setup.sql
============================================================================ */


-- ----------------------------------------------------------------------
-- 1. Reference tables (no-op if they already exist)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS carriers (
    carrier_code   VARCHAR(10) PRIMARY KEY,
    carrier_name   VARCHAR(100) NOT NULL,
    sla_days       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS regions (
    region_id      SERIAL PRIMARY KEY,
    region_name    VARCHAR(100) NOT NULL,
    country        VARCHAR(100) NOT NULL
);

-- ----------------------------------------------------------------------
-- 2. Seed carriers (DTDC intentionally has ZERO shipments — needed for
--    Exercise 2's LEFT JOIN test case). Safe to re-run.
-- ----------------------------------------------------------------------
INSERT INTO carriers (carrier_code, carrier_name, sla_days) VALUES
    ('DHL',     'DHL Express',        3),
    ('FEDEX',   'FedEx',              4),
    ('BLUEDART','BlueDart',           3),
    ('DTDC',    'DTDC Logistics',     5),
    ('UPS',     'UPS Freight',        4),
    ('ARAMEX',  'Aramex',             5)
ON CONFLICT (carrier_code) DO NOTHING;

-- ----------------------------------------------------------------------
-- 3. Seed regions. Safe to re-run (won't duplicate if already seeded --
--    note: since region_name has no UNIQUE constraint, ON CONFLICT DO
--    NOTHING has nothing to key off; if you already ran the old script
--    once, check for dupes with:  SELECT region_name, COUNT(*) FROM
--    regions GROUP BY region_name HAVING COUNT(*) > 1;
--    and DELETE the extras before continuing, or just skip this insert.
-- ----------------------------------------------------------------------
INSERT INTO regions (region_name, country)
SELECT v.region_name, v.country
FROM (VALUES
    ('Midwest',      'USA'),
    ('Northeast',    'USA'),
    ('West Coast',   'USA'),
    ('South',        'USA'),
    ('Southwest',    'USA')
) AS v(region_name, country)
WHERE NOT EXISTS (
    SELECT 1 FROM regions r WHERE r.region_name = v.region_name
);

-- ----------------------------------------------------------------------
-- 4. Insert fresh sample shipments — shipment_id generated explicitly
--    since it's varchar(12) with no default. Prefix 'D8-' + zero-padded
--    number keeps these clearly distinct from your Day 7 IDs and fits
--    comfortably in 12 chars (D8- + 6 digits = 9 chars).
--
--    Volume: ~119 days (skipping every 7th day as an intentional gap
--    for Exercise 1's ROWS vs RANGE comparison) x 60 shipments/day
--    = ~6,100 new rows, spread across 5 regions and 5 active carriers
--    -- comfortably clears Exercise 3's HAVING COUNT(*) >= 500 filter.
-- ----------------------------------------------------------------------
INSERT INTO logistics_shipments
    (shipment_id, shipped_date, cost_usd, delay_days, status, carrier, carrier_code, destination_region_id)
SELECT
    'D8-' || LPAD(row_number() OVER ()::text, 6, '0')                AS shipment_id,
    shipped_date,
    cost_usd,
    delay_days,
    status,
    carrier_code                                                     AS carrier,
    carrier_code,
    destination_region_id
FROM (
    SELECT
        d.shipped_date,
        ROUND((50 + random() * 950)::numeric, 2)                        AS cost_usd,
        (random() * 10)::int                                             AS delay_days,
        CASE WHEN random() < 0.85 THEN 'delivered' ELSE 'in_transit' END AS status,
        (SELECT carrier_code FROM carriers
         WHERE carrier_code != 'DTDC'
         ORDER BY random() LIMIT 1)                                      AS carrier_code,
        (SELECT region_id FROM regions ORDER BY random() LIMIT 1)        AS destination_region_id
    FROM (
        -- ~119 dates over the last 120 days, skipping every 7th day to
        -- create intentional gap days for Exercise 1
        SELECT (CURRENT_DATE - (n || ' days')::interval)::date AS shipped_date
        FROM generate_series(0, 119) AS n
        WHERE n % 7 != 0
    ) d
    CROSS JOIN generate_series(1, 60) AS shipments_per_day   -- ~60 shipments per active day
) sub
ON CONFLICT (shipment_id) DO NOTHING;


-- ----------------------------------------------------------------------
-- 5. Sanity checks — run these to confirm everything's ready before
--    moving to the exercise files
-- ----------------------------------------------------------------------

-- Total row count and date range:
SELECT COUNT(*), MIN(shipped_date), MAX(shipped_date) FROM logistics_shipments;

-- Shipments per region (Exercise 3 needs >= 500 per region to survive HAVING):
SELECT r.region_name, COUNT(*)
FROM logistics_shipments s
JOIN regions r ON s.destination_region_id = r.region_id
GROUP BY r.region_name
ORDER BY 2 DESC;

-- Confirm DTDC has zero shipments (Exercise 2's LEFT JOIN test case):
SELECT c.carrier_name, COUNT(s.shipment_id)
FROM carriers c
LEFT JOIN logistics_shipments s ON s.carrier_code = c.carrier_code
GROUP BY c.carrier_name
ORDER BY 2;
