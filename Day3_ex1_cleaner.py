import pandas as pd
from pathlib import Path

VALID_STATUSES = {"in_transit", "delivered", "pending", "exception"}
VALID_CARRIERS = {"DHL", "FEDEX", "BLUEDART"}


def load_shipments(file_path: str) -> pd.DataFrame:
    """Load a shipments CSV file. Drop completely empty rows."""
    df = pd.read_csv(file_path, dtype=str)
    df = df.dropna(how="all")
    return df


def normalise_row(row: pd.Series) -> dict:
    """Normalise string fields in a single row. Returns a dict."""
    def safe_str(val, transform):
        if pd.isna(val) or str(val).strip() == "":
            return None
        return transform(str(val).strip())

    raw_delay = pd.to_numeric(str(row["delay_days"]).strip(), errors="coerce")
    raw_cost = pd.to_numeric(str(row["cost_usd"]).strip(), errors="coerce")

    return {
        "shipment_id": safe_str(row["shipment_id"], lambda x: x),
        "carrier": safe_str(row["carrier"], lambda x: x.upper()),
        "status": safe_str(row["status"], lambda x: x.lower()),
        "origin": safe_str(row["origin"], lambda x: x.title()),
        "destination": safe_str(row["destination"], lambda x: x.title()),
        "delay_days": None if pd.isna(raw_delay) else float(raw_delay),
        "cost_usd": None if pd.isna(raw_cost) else float(raw_cost),
    }


def validate_row(row: dict) -> list:
    """Validate a normalised row. Returns list of error strings."""
    errors = []

    if not row["shipment_id"] or str(row["shipment_id"]).strip() == "":
        errors.append("shipment_id must not be empty")

    if row["carrier"] not in VALID_CARRIERS:
        errors.append("carrier must be in VALID_CARRIERS")

    if row["status"] not in VALID_STATUSES:
        errors.append("status must be in VALID_STATUSES")

    if row["delay_days"] is None or row["delay_days"] < 0:
        errors.append("delay_days must be >= 0")

    if row["cost_usd"] is None or row["cost_usd"] <= 0:
        errors.append("cost_usd must not be None and must be > 0")

    return errors


def clean_shipments(df: pd.DataFrame) -> tuple:
    """Run full cleaning pipeline. Returns (clean_df, failed_df)."""
    clean_rows = []
    failed_rows = []

    for _, row in df.iterrows():
        normalised = normalise_row(row)
        errors = validate_row(normalised)

        if errors:
            normalised["errors"] = "; ".join(errors)
            failed_rows.append(normalised)
        else:
            clean_rows.append(normalised)

    clean_df = pd.DataFrame(clean_rows).reset_index(drop=True)
    failed_df = pd.DataFrame(failed_rows).reset_index(drop=True)
    return clean_df, failed_df


def save_outputs(clean_df, failed_df, clean_path, failed_path):
    """Save clean and failed DataFrames to CSV files."""
    clean_df.to_csv(clean_path, index=False)
    failed_df.to_csv(failed_path, index=False)
    print(f"Clean rows saved:  {len(clean_df)} → {clean_path}")
    print(f"Failed rows saved: {len(failed_df)} → {failed_path}")


def main():
    raw_path = "shipments_raw.csv"
    clean_path = "shipments_clean.csv"
    failed_path = "shipments_failed.csv"

    print("Loading data...")
    df = load_shipments(raw_path)
    print(f"Loaded {len(df)} rows.")

    print("Cleaning data...")
    clean_df, failed_df = clean_shipments(df)

    print("Saving outputs...")
    save_outputs(clean_df, failed_df, clean_path, failed_path)
    print("\nDone.")


if __name__ == "__main__":
    main()
