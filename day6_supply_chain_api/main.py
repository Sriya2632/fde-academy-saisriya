from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(
    title="TechStar Group -- Supply Chain Status API",
    description=(
        "Internal utility API for AutoFinance Bank discovery phase "
        "data validation. Built by FDE Academy Cohort."
    ),
    version="1.0.0",
)

MOCK_SHIPMENTS: dict[str, dict] = {
    "SH001": {
        "shipment_id": "SH001",
        "carrier": "DHL",
        "status": "in_transit",
        "origin": "Mumbai",
        "destination": "Delhi",
        "cost_usd": 250.0,
        "created_at": "2024-01-18T10:00:00",
    },
    "SH002": {
        "shipment_id": "SH002",
        "carrier": "FEDEX",
        "status": "delivered",
        "origin": "Chennai",
        "destination": "Bangalore",
        "cost_usd": 180.5,
        "created_at": "2024-01-17T09:30:00",
    },
    "SH003": {
        "shipment_id": "SH003",
        "carrier": "BLUEDART",
        "status": "delayed",
        "origin": "Pune",
        "destination": "Hyderabad",
        "cost_usd": 320.0,
        "created_at": "2024-01-16T14:15:00",
    },
}

MOCK_CARRIERS: dict[str, dict] = {
    "DHL": {
        "carrier": "DHL",
        "full_name": "DHL Express",
        "tracking_url": "https://www.dhl.com/track",
    },
    "FEDEX": {
        "carrier": "FEDEX",
        "full_name": "FedEx Corporation",
        "tracking_url": "https://www.fedex.com/track",
    },
    "BLUEDART": {
        "carrier": "BLUEDART",
        "full_name": "Blue Dart Express",
        "tracking_url": "https://www.bluedart.com/track",
    },
}


class ShipmentResponse(BaseModel):
    shipment_id: str
    carrier: str
    status: str
    origin: str
    destination: str
    cost_usd: float
    created_at: str


class ShipmentCreateRequest(BaseModel):
    shipment_id: str
    carrier: str
    status: str = Field(default="in_transit")
    origin: str
    destination: str
    cost_usd: float = Field(gt=0)


class CarrierResponse(BaseModel):
    carrier: str
    full_name: str
    tracking_url: str

VALID_API_KEYS = {"techstar-fde-key-001", "techstar-fde-key-002"}


def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> str:
    """
    FastAPI dependency -- validates the X-API-Key header.
    Raises 401 if missing, 403 if present but invalid.
    """
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


# ---------------------------------------------------------------------------
# Exercise 1 endpoints
# ---------------------------------------------------------------------------


@app.get("/shipments", response_model=list[ShipmentResponse])
def list_shipments(
    status: Optional[str] = None,
    carrier: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
) -> list[dict]:
    """
    GET /shipments
    GET /shipments?status=delayed
    GET /shipments?carrier=DHL&status=in_transit
    """
    results = list(MOCK_SHIPMENTS.values())

    if status is not None:
        results = [s for s in results if s["status"] == status]

    if carrier is not None:
        results = [s for s in results if s["carrier"].upper() == carrier.upper()]

    return results


@app.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(shipment_id: str, api_key: str = Depends(verify_api_key)) -> dict:
    """GET /shipments/SH001 -- 404 if shipment_id not found."""
    if shipment_id not in MOCK_SHIPMENTS:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return MOCK_SHIPMENTS[shipment_id]


@app.post("/shipments", response_model=ShipmentResponse, status_code=201)
def create_shipment(
    payload: ShipmentCreateRequest,
    api_key: str = Depends(verify_api_key),
) -> dict:
    """POST /shipments -- 409 Conflict if shipment_id already exists."""
    if payload.shipment_id in MOCK_SHIPMENTS:
        raise HTTPException(
            status_code=409,
            detail=f"Shipment {payload.shipment_id} already exists",
        )

    record = payload.model_dump()
    record["created_at"] = datetime.utcnow().isoformat()
    MOCK_SHIPMENTS[payload.shipment_id] = record
    return record


@app.get("/carriers", response_model=list[CarrierResponse])
def list_carriers(api_key: str = Depends(verify_api_key)) -> list[dict]:
    """GET /carriers -- returns all known carrier configs."""
    return list(MOCK_CARRIERS.values())


# ---------------------------------------------------------------------------
# Exercise 2 -- 3-vendor aggregation
# ---------------------------------------------------------------------------


class VendorStatus(BaseModel):
    """Unified shape -- every vendor response gets normalised to this."""

    shipment_id: str
    source_vendor: str
    normalised_status: str  # one of: in_transit, delayed, delivered, unknown
    raw: dict  # original vendor payload, kept for debugging


# --- Mock vendor "network calls" -------------------------------------------
# Each simulates network latency and occasionally simulates an outage so the
# aggregation endpoint has something real to be resilient against. Tests
# patch these functions directly with AsyncMock for deterministic behaviour.


async def call_vendor_a(shipment_id: str) -> dict:
    """Vendor A: flat shape, snake-ish keys."""
    await asyncio.sleep(0.05)
    if random.random() < 0.05:
        raise httpx.HTTPError(f"Vendor A timeout for {shipment_id}")
    return {
        "id": shipment_id,
        "current_status": random.choice(["in_transit", "delayed", "delivered"]),
    }


async def call_vendor_b(shipment_id: str) -> dict:
    """Vendor B: camelCase keys, UPPER_CASE status values."""
    await asyncio.sleep(0.05)
    if random.random() < 0.05:
        raise httpx.HTTPError(f"Vendor B unavailable for {shipment_id}")
    return {
        "shipmentRef": shipment_id,
        "trackingState": random.choice(["IN_TRANSIT", "DELAYED", "DELIVERED"]),
    }


async def call_vendor_c(shipment_id: str) -> dict:
    """Vendor C: deeply nested payload."""
    await asyncio.sleep(0.05)
    if random.random() < 0.05:
        raise httpx.HTTPError(f"Vendor C error for {shipment_id}")
    return {
        "shipment": {
            "id": shipment_id,
            "state": {
                "code": random.choice(["transit", "delayed", "complete"]),
            },
        }
    }


# --- Normaliser functions -- one per vendor shape ---------------------------


def normalise_vendor_a(raw: dict) -> VendorStatus:
    return VendorStatus(
        shipment_id=raw["id"],
        source_vendor="vendor_a",
        normalised_status=raw.get("current_status", "unknown"),
        raw=raw,
    )


def normalise_vendor_b(raw: dict) -> VendorStatus:
    """
    Vendor B uses 'shipmentRef' and 'trackingState' (UPPER_CASE values).
    Map trackingState values: 'DELAYED' -> 'delayed', etc.
    """
    status_map = {
        "IN_TRANSIT": "in_transit",
        "DELAYED": "delayed",
        "DELIVERED": "delivered",
    }
    tracking_state = raw.get("trackingState", "")
    return VendorStatus(
        shipment_id=raw["shipmentRef"],
        source_vendor="vendor_b",
        normalised_status=status_map.get(tracking_state, "unknown"),
        raw=raw,
    )


def normalise_vendor_c(raw: dict) -> VendorStatus:
    """
    Vendor C nests everything under raw['shipment']['state']['code'].
    Use safe .get() chains -- this is the deepest nesting of the three.
    """
    status_map = {
        "transit": "in_transit",
        "delayed": "delayed",
        "complete": "delivered",
    }
    shipment = raw.get("shipment", {})
    code = shipment.get("state", {}).get("code", "")
    return VendorStatus(
        shipment_id=shipment.get("id", "unknown"),
        source_vendor="vendor_c",
        normalised_status=status_map.get(code, "unknown"),
        raw=raw,
    )


@app.get("/supply-chain-status/{shipment_id}", response_model=list[VendorStatus])
async def get_supply_chain_status(
    shipment_id: str,
    api_key: str = Depends(verify_api_key),
) -> list[VendorStatus]:
    """
    Call all 3 vendors CONCURRENTLY for the given shipment_id.

    A failing vendor should be omitted from the result, not crash the
    request. Raise HTTPException(503) only if ALL THREE vendors fail.
    """
    # NOTE: call through the module namespace (not pre-bound local
    # references) so that `unittest.mock.patch('main.call_vendor_a', ...)`
    # in tests actually takes effect -- a list captured at import time
    # would keep pointing at the original, un-mocked functions.
    import main as _self

    normalisers = [normalise_vendor_a, normalise_vendor_b, normalise_vendor_c]
    calls = [
        _self.call_vendor_a(shipment_id),
        _self.call_vendor_b(shipment_id),
        _self.call_vendor_c(shipment_id),
    ]
    results = await asyncio.gather(*calls, return_exceptions=True)

    statuses: list[VendorStatus] = []
    for raw, normalise in zip(results, normalisers):
        if isinstance(raw, BaseException):
            continue
        statuses.append(normalise(raw))  # type: ignore[arg-type]

    if not statuses:
        raise HTTPException(
            status_code=503, detail="All vendor systems are currently unavailable"
        )

    return statuses