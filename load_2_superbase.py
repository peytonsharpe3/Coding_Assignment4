#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, date, timezone
from dotenv import load_dotenv
load_dotenv()


# If you use pandas anywhere, we detect Timestamp by name without importing pandas
try:
    import pandas as pd  # optional
    _HAS_PD = True
except Exception:
    _HAS_PD = False

from supabase import create_client, Client  # pip install supabase


def to_rfc3339_utc(dt: datetime) -> str:
    """
    Convert datetime (naive or tz-aware) to RFC3339 UTC string with 'Z'.
    """
    if dt.tzinfo is None:
        # assume local -> convert to UTC by attaching local time as UTC (safer to assume UTC)
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    # keep microseconds if you like; many schemas use seconds precision
    return dt.isoformat().replace("+00:00", "Z")


def serialize_value(v):
    """
    Return a JSON-serializable value.
    - datetime/date -> RFC3339 strings
    - pandas.Timestamp -> RFC3339 strings
    - other non-serializable objects -> str()
    """
    # pandas.Timestamp by type name to avoid hard dep on pandas
    if v is None:
        return None

    tname = type(v).__name__
    if tname == "Timestamp":
        # works even if pd not imported; but if it is, convert robustly
        if _HAS_PD and isinstance(v, pd.Timestamp):
            return to_rfc3339_utc(v.to_pydatetime())
        else:
            # best-effort
            return to_rfc3339_utc(datetime.fromisoformat(str(v)))
    if isinstance(v, datetime):
        return to_rfc3339_utc(v)
    if isinstance(v, date):
        # store midnight UTC for plain dates
        return f"{v.isoformat()}T00:00:00Z"

    # primitives pass through
    if isinstance(v, (str, int, float, bool, list, dict)):
        return v

    # fallback
    return str(v)


def sanitize_row(row: dict) -> dict:
    """
    Make a copy of row where all values are JSON serializable.
    Ensures `updated_at` exists and is RFC3339 UTC (TIMESTAMPTZ).
    """
    out = {}
    for k, v in row.items():
        out[k] = serialize_value(v)

    # Ensure updated_at is present and valid
    if "updated_at" not in out or out["updated_at"] in ("", None):
        out["updated_at"] = to_rfc3339_utc(datetime.now(timezone.utc))

    return out


def load_json_rows(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # if it's a dict of id->row, convert to list
        if all(isinstance(v, dict) for v in data.values()):
            data = list(data.values())
        else:
            data = [data]
    if not isinstance(data, list):
        raise ValueError("structured.json must be a list or a dict of rows")
    return data


def main():
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_KEY env vars.", file=sys.stderr)
        sys.exit(1)

    print("load_to_supabase: creating supabase_client…")
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"load_to_supabase: created supabase_client -> {supabase_client}")

    json_path = os.path.join(os.path.dirname(__file__), "structured.json")
    rows = load_json_rows(json_path)
    print(f"Loaded {len(rows)} records from structured.json")

    if rows:
        print(f"Sample row keys: {list(rows[0].keys())}")

    safe_rows = [sanitize_row(r) for r in rows]

    # OPTIONAL: If your DB has a DEFAULT trigger for updated_at, you could remove it from payload:
    # for r in safe_rows:
    #     r.pop("updated_at", None)

    try:
        response = supabase_client.table("quotes").upsert(safe_rows).execute()
        print("Upsert OK")
        print(response)  # optional
    except Exception as e:
        print(f"ERROR during upsert: {repr(e)}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()