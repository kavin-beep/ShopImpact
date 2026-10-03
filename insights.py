"""Trends and history views calculated only from the user's logged purchases."""
from decimal import Decimal, ROUND_HALF_UP
from logic import month_records, summary


def shift_month(month, offset):
    year, number = map(int, month.split("-"))
    if not 1 <= number <= 12:
        raise ValueError("Choose a valid month.")
    year, number = divmod(year * 12 + number - 1 + offset, 12)
    return f"{year:04d}-{number + 1:02d}"


def monthly_trend(records, month):
    """Six calendar months ending at the selected month, including empty months."""
    return [{"month": period, **summary(month_records(records, period))}
            for period in (shift_month(month, offset) for offset in range(-5, 1))]


def month_insights(records, month, budget):
    current = summary(month_records(records, month))
    previous = summary(month_records(records, shift_month(month, -1)))
    categories = {}
    for purchase in month_records(records, month):
        category = purchase["product_type"]
        categories[category] = categories.get(category, Decimal("0")) + Decimal(purchase["price"])
    top = max(categories, key=categories.get) if categories else None
    return {"current": current, "previous": previous,
            "average": (current["spend"] / current["count"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if current["count"] else None,
            "remaining": Decimal(str(budget)) - current["spend"],
            "spend_change": current["spend"] - previous["spend"] if previous["count"] else None,
            "top_category": top, "top_spend": categories.get(top, Decimal("0"))}


def filter_purchases(records, query="", month=None, category=None, order="Newest first"):
    """Return a new ordered list; keep original records intact for persistence."""
    query = query.strip().casefold()
    result = [p for p in records
              if (not month or p["purchase_date"][:7] == month)
              and (not category or p["product_type"] == category)
              and query in " ".join(str(p[field]) for field in
                                   ("brand", "product_type", "purchase_date", "price", "estimated_co2")).casefold()]
    if order == "Highest price":
        return sorted(result, key=lambda p: (Decimal(p["price"]), p["purchase_date"], p["id"]), reverse=True)
    if order == "Highest estimated impact":
        return sorted(result, key=lambda p: (Decimal(p["estimated_co2"]), p["purchase_date"], p["id"]), reverse=True)
    return sorted(result, key=lambda p: (p["purchase_date"], p["id"]), reverse=order != "Oldest first")
