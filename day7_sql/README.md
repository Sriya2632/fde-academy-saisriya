# Day 7 — SQL Basics: Logistics Discovery Lab

## Files

| File | Purpose |
|---|---|
| `00_setup.sql` | Creates `logistics_shipments` and loads 100,000 rows (with ~3% negative delay, ~2% zero cost, deliberately injected) |
| `exercise1_profiling.sql` | Volume/structure, categorical profiling, NULL audit, numeric ranges |
| `exercise2_business_queries.sql` | The 10 operational KPI queries + a bonus (OTIF% per carrier) |
| `exercise3_anomaly_detection.sql` | Duplicate/referential checks, impossible values, categorical/text quality, final summary query |
| `data_discovery_report.md` | The one-page Final Step deliverable, compiled from real query output |

All four `.sql` files were run end-to-end against a live PostgreSQL 16 instance with the exact 100K-row dataset the setup script generates — every query is verified working, not just written.

## How to run it yourself

1. **Make sure PostgreSQL is running** and you have a database to point at (DBeaver, `psql`, or any PostgreSQL client works).

2. **Run the setup script once** to create and populate the table:
   ```bash
   psql -h <host> -U <user> -d <database> -f 00_setup.sql
   ```
   This should print `100000` at the end, confirming the row count.

3. **Run each exercise file** in order:
   ```bash
   psql -h <host> -U <user> -d <database> -f exercise1_profiling.sql
   psql -h <host> -U <user> -d <database> -f exercise2_business_queries.sql
   psql -h <host> -U <user> -d <database> -f exercise3_anomaly_detection.sql
   ```
   Or open each file directly in DBeaver / your SQL client and run query-by-query to inspect each result set individually (recommended while learning — the file runs all queries back-to-back with no pause).

## Notes on the data

- Every run of `00_setup.sql` generates fresh **random** data, so your exact row counts (e.g. how many negative-delay rows) will differ slightly from the numbers in `data_discovery_report.md` — but they should land close to the same ~3% / ~2% injection rates.
- `carrier`, `status` are drawn from fixed known sets by design, so Exercise 3's "unexpected value" checks (Q3.1, Q3.2, Q3.3) will always return 0 rows on this practice dataset. That's expected — the value of those queries is the *pattern*, which you'll reuse as-is against real (messier) client data.
- `origin_city = destination_city` is not flagged as "dirty" by the generator (both are drawn independently), so seeing ~16% of rows with matching origin/destination is a byproduct of the random generation, not a client-realistic anomaly rate — worth understanding for Exercise 3's reflection questions, which is why the discovery report calls it out as 🟡 "worth confirming with client" rather than a hard error.
