/* ============================================================================
   DAY 8 FIX — Correct the region/carrier assignment bug
   TechStar Group FDE Academy

   PROBLEM: Day8_Setup.sql used uncorrelated scalar subqueries like
     (SELECT carrier_code FROM carriers ORDER BY random() LIMIT 1)
   to assign a random carrier/region per row. Postgres hoists this kind
   of subquery into a single InitPlan and evaluates it ONCE for the
   whole statement, then reuses that one result for every row -- so
   every row ended up with the SAME carrier and SAME region instead of
   a random spread. That's why your last run showed only 2 regions and
   2 carriers with any shipments at all.

   FIX: build the list of valid carrier_codes / region_ids ONCE into an
   array, then pick a random INDEX into that array using an inline
   volatile expression (floor(random() * n)). Because the random() call
   is now a plain expression evaluated per row -- not buried inside a
   cached scalar subquery -- it re-evaluates correctly for every row.

   Run with:
     psql -d logistics_practice -f Day8_Fix.sql
============================================================================ */


-- ----------------------------------------------------------------------
-- 0. Sanity check first: confirm regions has exactly 5 rows, no dupes
--    (an earlier version of the setup script had no unique constraint
--    on region_name, so if you ran it more than once before the fixed
--    version, duplicates may have snuck in)
-- ----------------------------------------------------------------------
SELECT COUNT(*) AS total_rows, COUNT(DISTINCT region_name) AS distinct_names
FROM regions;

-- If total_rows != distinct_names, dedupe by keeping the lowest region_id
-- per name and remapping any shipments pointing at the removed duplicates:
WITH keep AS (
    SELECT MIN(region_id) AS keep_id, region_name
    FROM regions
    GROUP BY region_name
),
remap AS (
    SELECT r.region_id AS dup_id, k.keep_id
    FROM regions r
    JOIN keep k ON k.region_name = r.region_name
    WHERE r.region_id != k.keep_id
)
UPDATE logistics_shipments s
SET destination_region_id = remap.keep_id
FROM remap
WHERE s.destination_region_id = remap.dup_id;

DELETE FROM regions r
WHERE EXISTS (
    SELECT 1 FROM regions r2
    WHERE r2.region_name = r.region_name AND r2.region_id < r.region_id
);


-- ----------------------------------------------------------------------
-- 1. Re-randomize destination_region_id across ALL rows
--
--    IMPORTANT FIX: no outer SELECT wrapper this time. Wrapping the
--    array-index expression in "SET col = (SELECT ...)" recreates the
--    exact same InitPlan-caching bug -- Postgres hoists ANY bare
--    scalar-subquery SET clause and evaluates it once for the whole
--    statement. The fix is to assign the array-index expression
--    DIRECTLY, with no SELECT wrapper around it, so random() is a
--    plain per-row function call rather than something buried inside
--    a cacheable subquery boundary.
-- ----------------------------------------------------------------------
UPDATE logistics_shipments
SET destination_region_id =
    (ARRAY(SELECT region_id FROM regions ORDER BY region_id))
    [1 + floor(random() * (SELECT COUNT(*) FROM regions))::int];

-- ----------------------------------------------------------------------
-- 2. Re-randomize carrier_code across ALL rows
--    (DTDC stays excluded from the pool so it keeps zero shipments --
--    that's the intentional test case for Exercise 2's LEFT JOIN)
--    Same fix: no outer SELECT wrapper.
-- ----------------------------------------------------------------------
UPDATE logistics_shipments
SET carrier_code =
    (ARRAY(SELECT carrier_code FROM carriers WHERE carrier_code != 'DTDC' ORDER BY carrier_code))
    [1 + floor(random() * (SELECT COUNT(*) FROM carriers WHERE carrier_code != 'DTDC'))::int];


-- ----------------------------------------------------------------------
-- 3. Re-run sanity checks -- should now show all 5 regions and all 5
--    active carriers with a healthy, roughly-even spread, and DTDC
--    still at 0
-- ----------------------------------------------------------------------
SELECT COUNT(*), MIN(shipped_date), MAX(shipped_date) FROM logistics_shipments;

SELECT r.region_name, COUNT(*)
FROM logistics_shipments s
JOIN regions r ON s.destination_region_id = r.region_id
GROUP BY r.region_name
ORDER BY 2 DESC;

SELECT c.carrier_name, COUNT(s.shipment_id)
FROM carriers c
LEFT JOIN logistics_shipments s ON s.carrier_code = c.carrier_code
GROUP BY c.carrier_name
ORDER BY 2;