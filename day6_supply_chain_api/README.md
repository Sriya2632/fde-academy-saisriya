# Day 6 — Supply Chain Status API (completed)

All three exercises implemented in one service, as the lab intends.

## Setup

```bash
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn main:app --reload
```

Then open http://127.0.0.1:8000/docs for Swagger UI.

## Run tests + coverage

```bash
pytest test_main.py --cov=main --cov-report=term-missing
```

Result: **21 passed, 89% coverage** (target was 80%+).

## Formatting / type checks

```bash
black main.py test_main.py
mypy main.py --ignore-missing-imports
```

Both are clean.

## What was filled in

**Exercise 1 — FastAPI Foundations**
- `ShipmentResponse`, `ShipmentCreateRequest`, `CarrierResponse` Pydantic models
- `list_shipments` — filters by `status` and case-insensitive `carrier`
- `get_shipment` — 404 if not found
- `create_shipment` — 409 on duplicate `shipment_id`, stamps `created_at`
- `list_carriers` — returns the mock carrier directory

**Exercise 2 — Supply Chain Status API**
- `normalise_vendor_b` — maps `trackingState` (UPPER_CASE) to the unified status vocabulary, defaulting unrecognised values to `"unknown"`
- `normalise_vendor_c` — safely walks the deepest nesting (`shipment.state.code`) with `.get()` chains so missing keys never raise
- `call_vendor_a/b/c` — mock "network calls" with simulated latency and occasional simulated outages, added so the aggregation endpoint has real async work and real failures to be resilient against
- `get_supply_chain_status` — calls all three vendors concurrently with `asyncio.gather(..., return_exceptions=True)`, drops any vendor that raised, and only 503s if **all three** failed

**Exercise 3 — Securing & Testing**
- `verify_api_key` dependency — 401 if the header is missing, 403 if it's present but wrong
- `Depends(verify_api_key)` added to every endpoint from Ex 1 and Ex 2
- Full `test_main.py`: auth tests, CRUD tests, and — the trickiest part — deterministic aggregation tests that patch `call_vendor_a/b/c` with `AsyncMock` to test the success / partial-failure / total-failure paths without relying on real randomness

## One implementation note worth reading

The aggregation endpoint calls vendor functions through `main.call_vendor_a(...)`
(via the module namespace) rather than a variable bound at import time. That
matters for testability: if you build a list like
`_CALLS = [call_vendor_a, call_vendor_b, call_vendor_c]` at module load time,
`unittest.mock.patch('main.call_vendor_a', ...)` in your tests will rebind the
*module attribute* but the list still holds the original function reference —
so the patch silently does nothing and tests become flaky (pass/fail based on
real randomness). This is a common gotcha worth knowing for any code you mock.