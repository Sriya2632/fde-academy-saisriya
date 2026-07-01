from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ── TASK 1A: Carrier config using @dataclass ──────────────────────────────
@dataclass
class CarrierConfig:
    """Immutable carrier SLA configuration."""

    code: str
    name: str
    sla_days: int
    region: str
    active: bool = True

    def __post_init__(self) -> None:
        # Normalise code to UPPER and validate sla_days > 0
        self.code = self.code.strip().upper()
        if self.sla_days <= 0:
            raise ValueError("sla_days must be > 0")


# ── TASK 1B: ShipmentTracker class ─────────────────────────────────────────
class ShipmentTracker:
    """Tracks a single shipment through its delivery lifecycle.

    Valid status transitions:
        pending -> in_transit
        in_transit -> delivered | exception
        exception -> in_transit (after resolution)
        delivered -> (terminal - no further transitions)

    Attributes:
        shipment_id: Unique identifier.
        carrier: CarrierConfig for this shipment.
        origin: Origin city.
        destination: Destination city.
        delay_days: Days late (>0 = delayed).
        cost_usd: Shipment cost.
    """

    # Class attribute: valid transitions map
    TRANSITIONS: dict[str, set[str]] = {
        "pending": {"in_transit"},
        "in_transit": {"delivered", "exception"},
        "exception": {"in_transit"},
        "delivered": set(),  # Terminal state
    }

    PENALTY_RATE_PER_DAY: float = 150.0  # USD per delayed day

    def __init__(
        self,
        shipment_id: str,
        carrier: CarrierConfig,
        origin: str,
        destination: str,
        delay_days: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        # Validate inputs
        if not shipment_id.strip():
            raise ValueError("shipment_id must not be empty")
        if origin == destination:
            raise ValueError("origin and destination must differ")
        self.shipment_id = shipment_id.strip().upper()
        self.carrier = carrier
        self.origin = origin.strip().title()
        self.destination = destination.strip().title()
        self.cost_usd = cost_usd
        self._delay_days = 0
        self.delay_days = delay_days  # Use the property setter
        self._status = "pending"
        self._history: list[tuple[str, str, datetime]] = (
            []
        )  # (from_status, to_status, timestamp)

    # ── TASK 1C: Properties ────────────────────────────────────────────────
    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, new_status: str) -> None:
        """
        Validate the transition and update _status. Rules:
        1. new_status must be a valid key in TRANSITIONS
        2. The transition from current status to new_status must be allowed
        3. On success: append (old, new, datetime.utcnow()) to _history
        4. On failure: raise ValueError with a descriptive message
        """
        if new_status not in self.TRANSITIONS:
            raise ValueError(f"Invalid status: {new_status!r}")
        allowed = self.TRANSITIONS[self._status]
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {self._status} -> {new_status}. "
                f"Allowed from {self._status!r}: {allowed}"
            )
        old_status = self._status
        self._status = new_status
        self._history.append((old_status, new_status, datetime.utcnow()))

    @property
    def delay_days(self) -> int:
        return self._delay_days

    @delay_days.setter
    def delay_days(self, value: int) -> None:
        # Must be >= 0; raise ValueError otherwise
        if value < 0:
            raise ValueError("delay_days must be >= 0")
        self._delay_days = value

    @property
    def is_delayed(self) -> bool:
        return self._delay_days > 0

    @property
    def breached_sla(self) -> bool:
        # True if delay_days > carrier.sla_days
        return self._delay_days > self.carrier.sla_days

    # ── TASK 1D: Methods ───────────────────────────────────────────────────
    def delay_penalty(self, rate: Optional[float] = None) -> float:
        """Return penalty in USD. Uses PENALTY_RATE_PER_DAY if rate not given."""
        effective_rate = rate if rate is not None else self.PENALTY_RATE_PER_DAY
        return self._delay_days * effective_rate

    def transition_to(self, new_status: str) -> None:
        """Public method to change status. Delegates to the property setter."""
        self.status = new_status

    def status_history(self) -> list[str]:
        """Return list of human-readable transition strings.
        Format: 'pending -> in_transit @ 2024-01-20T09:30:00'
        """
        return [f"{old} -> {new} @ {ts.isoformat()}" for old, new, ts in self._history]

    def to_dict(self) -> dict:
        """Return a flat dict suitable for Foundry dataset ingestion.

        Include: shipment_id, carrier_code, carrier_name, origin, destination,
        status, delay_days, cost_usd, penalty_usd, is_delayed, breached_sla,
        transition_count
        """
        return {
            "shipment_id": self.shipment_id,
            "carrier_code": self.carrier.code,
            "carrier_name": self.carrier.name,
            "origin": self.origin,
            "destination": self.destination,
            "status": self.status,
            "delay_days": self.delay_days,
            "cost_usd": self.cost_usd,
            "penalty_usd": self.delay_penalty(),
            "is_delayed": self.is_delayed,
            "breached_sla": self.breached_sla,
            "transition_count": len(self._history),
        }

    def __repr__(self) -> str:
        return (
            f"ShipmentTracker(id={self.shipment_id!r}, "
            f"carrier={self.carrier.code!r}, "
            f"status={self.status!r}, delay={self.delay_days}d)"
        )


# ── Task 2: Test script ─────────────────────────────────────────────────
if __name__ == "__main__":
    # Define carriers
    dhl = CarrierConfig(code="dhl", name="DHL Express", sla_days=2, region="APAC")
    fedex = CarrierConfig(code="fedex", name="FedEx India", sla_days=3, region="APAC")

    # Create a shipment
    s = ShipmentTracker("sh-001", dhl, "Mumbai", "Delhi", delay_days=3, cost_usd=250.0)
    print(s)

    # Transition through valid states
    s.transition_to("in_transit")
    s.transition_to("delivered")
    print("History:", s.status_history())
    print("Penalty: $", s.delay_penalty())
    print("Breached SLA:", s.breached_sla)
    print("Foundry record:", s.to_dict())

    # Test invalid transition
    try:
        s.transition_to("pending")  # delivered is terminal
    except ValueError as e:
        print("Expected error:", e)

    # Test exception -> in_transit -> delivered path
    s2 = ShipmentTracker("sh-002", fedex, "Chennai", "Bangalore")
    s2.transition_to("in_transit")
    s2.transition_to("exception")  # Delayed at customs
    s2.delay_days = 5
    s2.transition_to("in_transit")  # Resolved
    s2.transition_to("delivered")

    print("\ns2 history:")
    for entry in s2.status_history():
        print(" ", entry)

    # Test batch summary
    shipments = [
        s,
        s2,
        ShipmentTracker("sh-003", dhl, "Pune", "Hyderabad", delay_days=0),
    ]
    records = [sh.to_dict() for sh in shipments]
    print(f"\nBatch: {len(records)} records ready for Foundry ingestion")
    delayed = [r for r in records if r["is_delayed"]]
    print(
        f"Delayed: {len(delayed)} | Avg penalty: $"
        f"{sum(r['penalty_usd'] for r in delayed) / max(len(delayed), 1):.2f}"
    )