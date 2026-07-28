import copy

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app, MOCK_SHIPMENTS

client = TestClient(app)

AUTH_HEADERS = {"X-API-Key": "techstar-fde-key-001"}

# Snapshot the original mock DB so each test starts from a clean, known state
# (create_shipment mutates MOCK_SHIPMENTS in place).
_ORIGINAL_SHIPMENTS = copy.deepcopy(MOCK_SHIPMENTS)


@pytest.fixture(autouse=True)
def reset_mock_db():
    MOCK_SHIPMENTS.clear()
    MOCK_SHIPMENTS.update(copy.deepcopy(_ORIGINAL_SHIPMENTS))
    yield
    MOCK_SHIPMENTS.clear()
    MOCK_SHIPMENTS.update(copy.deepcopy(_ORIGINAL_SHIPMENTS))


# ---------------------------------------------------------------------------
# TASK 1: Auth tests
# ---------------------------------------------------------------------------


def test_missing_api_key_returns_401():
    response = client.get("/shipments")  # No headers at all
    assert response.status_code == 401


def test_invalid_api_key_returns_403():
    response = client.get("/shipments", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403


def test_valid_api_key_allows_access():
    response = client.get("/shipments", headers=AUTH_HEADERS)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# TASK 2: Shipment CRUD tests
# ---------------------------------------------------------------------------


def test_list_shipments_returns_all():
    response = client.get("/shipments", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == len(MOCK_SHIPMENTS)


def test_list_shipments_filters_by_status():
    response = client.get("/shipments?status=delayed", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(item["status"] == "delayed" for item in body)


def test_list_shipments_filters_by_carrier_case_insensitive():
    response = client.get("/shipments?carrier=dhl", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(item["carrier"] == "DHL" for item in body)


def test_get_shipment_success():
    response = client.get("/shipments/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["shipment_id"] == "SH001"


def test_get_shipment_not_found_returns_404():
    response = client.get("/shipments/SH999", headers=AUTH_HEADERS)
    assert response.status_code == 404


def test_create_shipment_success():
    new_shipment = {
        "shipment_id": "SH010",
        "carrier": "DHL",
        "status": "in_transit",
        "origin": "Delhi",
        "destination": "Mumbai",
        "cost_usd": 99.99,
    }
    response = client.post("/shipments", json=new_shipment, headers=AUTH_HEADERS)
    assert response.status_code == 201
    body = response.json()
    assert body["shipment_id"] == "SH010"
    assert "created_at" in body
    assert "SH010" in MOCK_SHIPMENTS


def test_create_shipment_conflict_returns_409():
    duplicate = {
        "shipment_id": "SH001",
        "carrier": "DHL",
        "status": "in_transit",
        "origin": "Delhi",
        "destination": "Mumbai",
        "cost_usd": 99.99,
    }
    response = client.post("/shipments", json=duplicate, headers=AUTH_HEADERS)
    assert response.status_code == 409


def test_create_shipment_requires_auth():
    new_shipment = {
        "shipment_id": "SH011",
        "carrier": "FEDEX",
        "status": "in_transit",
        "origin": "Delhi",
        "destination": "Mumbai",
        "cost_usd": 50.0,
    }
    response = client.post("/shipments", json=new_shipment)
    assert response.status_code == 401


def test_list_carriers_returns_all():
    response = client.get("/carriers", headers=AUTH_HEADERS)
    assert response.status_code == 200
    carriers = {c["carrier"] for c in response.json()}
    assert carriers == {"DHL", "FEDEX", "BLUEDART"}


# ---------------------------------------------------------------------------
# TASK 3: Supply-chain aggregation tests
#
# This is the most important part of the suite: making Exercise 2's
# RANDOM vendor behaviour completely deterministic for testing by
# patching the three call_vendor_X functions with AsyncMock.
# ---------------------------------------------------------------------------


def test_supply_chain_status_all_vendors_succeed():
    with (
        patch(
            "main.call_vendor_a",
            new=AsyncMock(
                return_value={
                    "id": "SH001",
                    "current_status": "in_transit",
                }
            ),
        ),
        patch(
            "main.call_vendor_b",
            new=AsyncMock(
                return_value={
                    "shipmentRef": "SH001",
                    "trackingState": "DELAYED",
                }
            ),
        ),
        patch(
            "main.call_vendor_c",
            new=AsyncMock(
                return_value={
                    "shipment": {"id": "SH001", "state": {"code": "complete"}},
                }
            ),
        ),
    ):
        response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    statuses_by_vendor = {
        item["source_vendor"]: item["normalised_status"] for item in body
    }
    assert statuses_by_vendor == {
        "vendor_a": "in_transit",
        "vendor_b": "delayed",
        "vendor_c": "delivered",
    }


def test_supply_chain_status_partial_failure_is_omitted_not_fatal():
    with (
        patch(
            "main.call_vendor_a",
            new=AsyncMock(
                return_value={
                    "id": "SH001",
                    "current_status": "in_transit",
                }
            ),
        ),
        patch(
            "main.call_vendor_b", new=AsyncMock(side_effect=Exception("vendor b down"))
        ),
        patch(
            "main.call_vendor_c",
            new=AsyncMock(
                return_value={
                    "shipment": {"id": "SH001", "state": {"code": "complete"}},
                }
            ),
        ),
    ):
        response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    vendors = {item["source_vendor"] for item in body}
    assert vendors == {"vendor_a", "vendor_c"}


def test_supply_chain_status_all_vendors_fail_returns_503():
    with (
        patch("main.call_vendor_a", new=AsyncMock(side_effect=Exception("down"))),
        patch("main.call_vendor_b", new=AsyncMock(side_effect=Exception("down"))),
        patch("main.call_vendor_c", new=AsyncMock(side_effect=Exception("down"))),
    ):
        response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)

    assert response.status_code == 503


def test_supply_chain_status_requires_auth():
    response = client.get("/supply-chain-status/SH001")
    assert response.status_code == 401


def test_supply_chain_status_unrecognised_vendor_b_value_maps_to_unknown():
    # Vendor B has an explicit status_map -- any value it doesn't recognise
    # (e.g. a new status the vendor introduces) must fall back to 'unknown'
    # rather than leaking the raw vendor-specific string.
    with (
        patch("main.call_vendor_a", new=AsyncMock(side_effect=Exception("down"))),
        patch(
            "main.call_vendor_b",
            new=AsyncMock(
                return_value={
                    "shipmentRef": "SH001",
                    "trackingState": "SOME_NEW_STATE",
                }
            ),
        ),
        patch("main.call_vendor_c", new=AsyncMock(side_effect=Exception("down"))),
    ):
        response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json()[0]["normalised_status"] == "unknown"


# ---------------------------------------------------------------------------
# Unit tests for normaliser functions (fast, no HTTP layer -- good for coverage)
# ---------------------------------------------------------------------------


def test_normalise_vendor_a_direct():
    from main import normalise_vendor_a

    result = normalise_vendor_a({"id": "SH005", "current_status": "delivered"})
    assert result.shipment_id == "SH005"
    assert result.normalised_status == "delivered"


def test_normalise_vendor_b_direct():
    from main import normalise_vendor_b

    result = normalise_vendor_b({"shipmentRef": "SH005", "trackingState": "IN_TRANSIT"})
    assert result.normalised_status == "in_transit"


def test_normalise_vendor_c_direct_deep_nesting():
    from main import normalise_vendor_c

    result = normalise_vendor_c(
        {"shipment": {"id": "SH005", "state": {"code": "transit"}}}
    )
    assert result.normalised_status == "in_transit"


def test_normalise_vendor_c_handles_missing_keys_safely():
    from main import normalise_vendor_c

    result = normalise_vendor_c({})
    assert result.normalised_status == "unknown"
    assert result.shipment_id == "unknown"