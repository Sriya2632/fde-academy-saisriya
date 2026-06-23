import pandas as pd

API_RESPONSE = {
    "meta": {"request_id": "REQ-2024-001", "total_records": 3, "page": 1},
    "shipments": [
        {
            "id": "SH-001",
            "reference": "PO-AFB-2024-441",
            "status": {"code": "IN_TRANSIT", "description": "Package in transit", "updated_at": "2024-01-20T08:15:00Z"},
            "carrier": {"name": "DHL Express", "code": "DHL", "service_type": "EXPRESS", "contact": {"email": "ops@dhl.in", "phone": "+91-22-12345678"}},
            "route": {"origin": {"city": "Mumbai", "state": "MH", "pin": "400001"}, "destination": {"city": "Delhi", "state": "DL", "pin": "110001"}, "estimated_delivery": "2024-01-22", "distance_km": 1450},
            "events": [
                {"ts": "2024-01-18T10:00:00Z", "location": "Mumbai Warehouse", "type": "PICKUP"},
                {"ts": "2024-01-19T06:30:00Z", "location": "Nagpur Hub", "type": "IN_TRANSIT"},
                {"ts": "2024-01-20T08:15:00Z", "location": "Delhi Hub", "type": "ARRIVED"},
            ],
            "charges": {"base": 850.0, "fuel_surcharge": 127.5, "gst": 177.75, "total": 1155.25},
            "delay_days": 0,
        },
        {
            "id": "SH-002",
            "reference": "PO-AFB-2024-442",
            "status": {"code": "DELAYED", "description": "Delayed due to customs clearance", "updated_at": "2024-01-20T07:00:00Z"},
            "carrier": {"name": "FedEx India", "code": "FEDEX", "service_type": "STANDARD", "contact": {"email": "support@fedex.in"}},
            "route": {"origin": {"city": "Chennai", "state": "TN", "pin": "600001"}, "destination": {"city": "Bangalore", "state": "KA", "pin": "560001"}, "estimated_delivery": "2024-01-21", "distance_km": 346},
            "events": [
                {"ts": "2024-01-18T14:00:00Z", "location": "Chennai Port", "type": "PICKUP"},
                {"ts": "2024-01-20T07:00:00Z", "location": "Customs Delhi", "type": "HELD"},
            ],
            "charges": {"base": 320.0, "fuel_surcharge": 48.0, "gst": 66.24, "total": 434.24},
            "delay_days": 3,
        },
        {
            "id": "SH-003",
            "reference": None,
            "status": {"code": "DELIVERED", "updated_at": "2024-01-19T16:00:00Z"},
            "carrier": {"name": "BlueDart", "code": "BLUEDART", "service_type": "ECONOMY"},
            "route": {"origin": {"city": "Pune"}, "destination": {"city": "Hyderabad", "state": "TS", "pin": "500001"}, "estimated_delivery": "2024-01-19", "distance_km": 559},
            "events": [
                {"ts": "2024-01-17T09:00:00Z", "location": "Pune Depot", "type": "PICKUP"},
                {"ts": "2024-01-19T16:00:00Z", "location": "Hyderabad Depot", "type": "DELIVERED"},
            ],
            "charges": {"base": 180.0, "gst": 32.4, "total": 212.4},
            "delay_days": 0,
        },
    ],
}


def extract_shipment_record(shipment: dict) -> dict:
    """Flatten a single shipment dict into a flat record."""
    events = shipment.get("events", [])
    last_event = events[-1] if events else {}

    return {
        "shipment_id": shipment.get("id"),
        "reference": shipment.get("reference"),
        "status_code": shipment.get("status", {}).get("code"),
        "status_desc": shipment.get("status", {}).get("description"),
        "carrier_name": shipment.get("carrier", {}).get("name"),
        "carrier_code": shipment.get("carrier", {}).get("code"),
        "service_type": shipment.get("carrier", {}).get("service_type"),
        "carrier_email": shipment.get("carrier", {}).get("contact", {}).get("email"),
        "origin_city": shipment.get("route", {}).get("origin", {}).get("city"),
        "origin_state": shipment.get("route", {}).get("origin", {}).get("state"),
        "dest_city": shipment.get("route", {}).get("destination", {}).get("city"),
        "dest_state": shipment.get("route", {}).get("destination", {}).get("state"),
        "est_delivery": shipment.get("route", {}).get("estimated_delivery"),
        "distance_km": shipment.get("route", {}).get("distance_km"),
        "event_count": len(events),
        "latest_event_type": last_event.get("type"),
        "latest_event_loc": last_event.get("location"),
        "charge_base": shipment.get("charges", {}).get("base"),
        "charge_gst": shipment.get("charges", {}).get("gst"),
        "charge_total": shipment.get("charges", {}).get("total"),
        "delay_days": shipment.get("delay_days", 0),
    }


def parse_api_response(response: dict) -> list:
    """Extract all shipment records from the full API response."""
    return [extract_shipment_record(s) for s in response.get("shipments", [])]


def compute_carrier_summary(records: list) -> list:
    """Group records by carrier and compute stats."""
    stats = {}
    for r in records:
        code = r["carrier_code"]
        if code not in stats:
            stats[code] = {
                "carrier_code": code,
                "carrier_name": r["carrier_name"],
                "shipment_count": 0,
                "total_revenue": 0.0,
                "delayed_count": 0,
                "delay_days_total": 0.0,
            }
        stats[code]["shipment_count"] += 1
        stats[code]["total_revenue"] += r["charge_total"] or 0
        if r["delay_days"] > 0:
            stats[code]["delayed_count"] += 1
        stats[code]["delay_days_total"] += r["delay_days"]

    summary = []
    for s in stats.values():
        s["avg_delay_days"] = round(s["delay_days_total"] / s["shipment_count"], 1)
        del s["delay_days_total"]
        summary.append(s)

    return sorted(summary, key=lambda x: x["total_revenue"], reverse=True)


if __name__ == "__main__":
    records = parse_api_response(API_RESPONSE)
    print(f"Parsed {len(records)} shipment records")

    df = pd.DataFrame(records)
    df.to_csv("shipments_parsed.csv", index=False)
    print("Saved: shipments_parsed.csv")

    summary = compute_carrier_summary(records)
    print("\n=== Carrier Summary ===")
    for row in summary:
        print(
            f"  {row['carrier_name']:<15} shipments={row['shipment_count']}",
            f"revenue=₹{row['total_revenue']:,.2f}",
            f"delayed={row['delayed_count']}",
            f"avg_delay={row['avg_delay_days']}d",
        )
