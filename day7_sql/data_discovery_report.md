# Data Discovery Report — Logistics Shipments Table
**Engagement:** TechStar Group / AutoFinance Bank | **Table:** `logistics_shipments` | **Date:** Day 1–2 Discovery

---

## 1. Volume & Structure (Exercise 1)

- **Total rows:** 100,000
- **Date coverage:** 2024-01-01 → 2024-06-29 (~6 months)
- **Columns:** `shipment_id` (PK), `carrier`, `origin_city`, `destination_city`, `status`, `delay_days`, `cost_usd`, `weight_kg`, `shipped_date`, `delivered_date`
- **NULLs:** none found across any business-critical column (0/0/0/0/0 on the audit query)
- **Carriers (3):** DHL (37,724), FEDEX (37,291), BLUEDART (24,985)
- **Status (4):** delayed (33,455), in_transit (33,190), delivered (16,774), pending (16,581)
- **Numeric ranges:** `cost_usd` 0.00–500.00 (avg 269.04) · `delay_days` -1–10 (avg 4.82) · `weight_kg` 1.00–501.00 (avg 250.65)
- ⚠️ The numeric minimums (`cost_usd = 0.00`, `delay_days = -1`) are the first sign of data quality issues — flagged and quantified in Exercise 3.

## 2. Key Operational KPIs (Exercise 2)

| Metric | Result |
|---|---|
| Currently delayed shipments | 33,455 |
| Total cost by carrier | DHL $10.20M · FEDEX $9.99M · BLUEDART $6.72M |
| Highest avg delay | FEDEX (4.83 days) |
| OTIF % (on-time-in-full, overall) | 0.9% |
| OTIF % by carrier | BLUEDART 0.9% · DHL 0.9% · FEDEX 0.8% |
| Highest-volume route | Chennai → Chennai (4,172 shipments) — itself a data quality flag, see below |
| Carriers with avg cost > $300 | None (all three average $250–$275) |
| Total weight shipped by DHL | 9,458,016.86 kg |
| Top 3 delayed destinations | Chennai (6,750) · Mumbai (6,708) · Bangalore (6,650) |

⚠️ **OTIF of ~0.9% is extremely low** for a real operation and should be flagged to the client — with `delay_days` uniformly distributed 0–10, only shipments landing exactly on `delay_days = 0` count as on-time, which is a property of this synthetic dataset rather than a realistic KPI. Worth confirming the real data's delay distribution during the next discovery session.

## 3. Data Quality Findings (Exercise 3)

| Issue | Count | Severity |
|---|---|---|
| Duplicate `shipment_id` (PK violation) | 0 | ✅ Clean |
| Unexpected carrier values | 0 | ✅ Clean |
| Unexpected status values | 0 | ✅ Clean |
| Carrier casing/whitespace issues | 0 | ✅ Clean |
| **Negative `delay_days`** | **3,098** | 🔴 Impossible value — flag for client |
| **Zero/negative `cost_usd`** | **2,039** | 🔴 Impossible value — flag for client |
| **`delivered_date` before `shipped_date`** | **47,095** | 🔴 Impossible ("time travel") — flag for client |
| **`origin_city` = `destination_city`** | **16,117** | 🟡 Suspicious — likely valid for local same-city transfers, but worth confirming with client |

### Recommendation
The negative-delay and zero-cost rows (~3% and ~2% of the table respectively, matching known injection rates) should be **flagged, not silently dropped** — an FDE should never unilaterally delete client data. Route them to the engagement lead as a documented exception list so the client's data owner can confirm whether these reflect a source-system bug (e.g. a nullable field defaulting to 0) or genuine edge cases.

The `delivered_date < shipped_date` count (47,095 — nearly half the table) is unusually high and is a byproduct of how this **practice** dataset generates the two date columns independently at random, rather than `delivered_date` being derived from `shipped_date + delay_days`. On a real client table this pattern would be a serious red flag; here it's worth noting as a known limitation of the synthetic generator rather than a genuine anomaly rate to expect in production.

---
*Generated as the Day 7 lab's Final Step deliverable — the same one-page format a TechStar Group FDE would hand to an engagement lead on Day 1–2 of a real client engagement.*
