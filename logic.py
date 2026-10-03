"""Pure Python rules: no interface code, so calculations are easy to test."""
import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / "data/product_catalog.json").read_text(encoding="utf-8"))
VERSION = "epa-2022-inr-reference-v2"


def money(value):
    """Validate and round monetary input with decimal arithmetic."""
    try:
        number = Decimal(str(value))
        if not number.is_finite() or not 0 <= number <= 10000000:
            raise ValueError("Price must be between INR 0 and INR 10,000,000.")
        return number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        raise ValueError("Enter a valid price.") from None


def impact(price, product_type):
    if product_type not in CATALOG:
        raise ValueError("Choose a recognised product type.")
    return (money(price) * Decimal(CATALOG[product_type]["multiplier"])).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)


def make_purchase(product_type, price, brand, purchased_on, record_id=None):
    if not isinstance(brand, str) or not brand.strip() or len(brand.strip()) > 80:
        raise ValueError("Enter a brand or shop name between 1 and 80 characters.")
    try:
        purchase_date = date.fromisoformat(str(purchased_on))
    except (ValueError, TypeError):
        raise ValueError("Choose a valid purchase date.") from None
    if not date(2000, 1, 1) <= purchase_date <= date(2100, 12, 31):
        raise ValueError("Choose a date between 2000 and 2100.")
    estimate = impact(price, product_type)
    return {"id": record_id or str(uuid4()), "product_type": product_type,
            "price": str(money(price)), "brand": brand.strip(),
            "purchase_date": purchase_date.isoformat(),
            "multiplier": CATALOG[product_type]["multiplier"],
            "estimated_co2": str(estimate), "methodology": VERSION,
            "source_code": CATALOG[product_type]["source_code"]}


def month_records(records, month):
    return [p for p in records if p["purchase_date"][:7] == month]


def summary(records):
    spend = sum((Decimal(p["price"]) for p in records), Decimal("0"))
    co2 = sum((Decimal(p["estimated_co2"]) for p in records), Decimal("0"))
    lower = sum(CATALOG[p["product_type"]]["lower_impact"] for p in records)
    return {"spend": spend, "co2": co2, "count": len(records), "lower": lower}


def badges(records):
    """Fixed monthly rules; empty histories cannot earn rewards."""
    totals = summary(records)
    earned = []
    if totals["count"] >= 3 and totals["co2"] <= Decimal("50"):
        earned.append("Eco Saver")
    if totals["lower"] >= 3 and totals["lower"] / totals["count"] >= 0.6:
        earned.append("Low Impact Shopper")
    if any(p["product_type"] == "Repair services" for p in records):
        earned.append("Repair Champion")
    return earned


def update_purchase(records, replacement):
    if not any(p["id"] == replacement["id"] for p in records):
        raise ValueError("That purchase no longer exists.")
    return [replacement if p["id"] == replacement["id"] else p for p in records]


def demo_records(today=None):
    """15 synthetic records across this and the previous month; never personal data."""
    today = today or date.today()
    previous = date(today.year - (today.month == 1), today.month - 1 or 12, 1)
    prices = [300, 650, 4500, 12000, 150, 750, 1000, 200, 250, 500, 2500, 18000, 90, 450, 800]
    types = list(CATALOG)
    return [make_purchase(types[i % len(types)], price, f"Demo shop {i + 1}",
                          date(today.year, today.month, min(i + 1, today.day)) if i < 10 else previous,
                          f"demo-{i + 1}") for i, price in enumerate(prices)]
