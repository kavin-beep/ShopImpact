"""Portable purchase backups; account persistence lives in accounts.py."""
import csv
import io
import json
from logic import VERSION, make_purchase


def export_json(records):
    return json.dumps({"version": VERSION, "currency": "INR", "purchases": records}, indent=2)


def import_json(raw, allow_legacy=False):
    if len(raw) > 2_000_000:
        raise ValueError("Backup must be smaller than 2 MB.")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("This file is not valid JSON.") from None
    versions = [VERSION, "epa-2022-inr-reference-v2", "illustrative-inr-v1"] if allow_legacy else [VERSION]
    if not isinstance(data, dict) or data.get("version") not in versions or data.get("currency") != "INR":
        raise ValueError("Choose a ShopImpact INR backup using the current methodology.")
    rows = data.get("purchases")
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValueError("Backup must contain a list of at most 1,000 purchases.")
    result, ids = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Every purchase must be a record.")
        if row.get("methodology", VERSION) != VERSION and not allow_legacy:
            raise ValueError("This backup includes older estimates. Allow an older backup to recalculate them using the latest reference data.")
        try:
            record_id = row["id"]
            if not isinstance(record_id, str) or not record_id or len(record_id) > 100 or record_id in ids:
                raise ValueError("Purchase IDs must be unique, non-empty text.")
            # Recompute derived fields instead of trusting uploaded impact values.
            record = make_purchase(row["product_type"], row["price"], row["brand"], row["purchase_date"], record_id)
        except (KeyError, TypeError):
            raise ValueError("A purchase has missing or invalid fields.") from None
        ids.add(record_id)
        result.append(record)
    return result


def export_csv(records):
    buffer = io.StringIO(newline="")
    fields = ["purchase_date", "product_type", "brand", "price", "estimated_co2", "multiplier", "methodology", "source_code"]
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        # Prevent spreadsheet formula interpretation of user-entered text.
        safe = {k: ("'" + str(v) if str(v).lstrip().startswith(("=", "+", "-", "@")) else v)
                for k, v in record.items()}
        writer.writerow(safe)
    return buffer.getvalue()
