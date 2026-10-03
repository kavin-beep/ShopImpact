import unittest
from decimal import Decimal
from insights import shift_month, monthly_trend, month_insights, filter_purchases
from logic import make_purchase


class InsightsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [make_purchase("Repair services", "99.99", "Local repair", "2025-12-12", "repair"),
                     make_purchase("Repair services", "100.01", "Local repair", "2026-01-05", "repair2"),
                     make_purchase("New clothing", "9.00", "Other shop", "2026-01-07", "clothes")]

    def test_months_cross_year_boundary(self):
        self.assertEqual(shift_month("2026-01", -1), "2025-12")
        self.assertEqual(shift_month("2025-12", 1), "2026-01")
        self.assertEqual(shift_month("2026-01", -13), "2024-12")

    def test_trend_keeps_empty_months_and_uses_exact_totals(self):
        trend = monthly_trend(self.rows, "2026-01")
        self.assertEqual([r["month"] for r in trend], ["2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01"])
        self.assertEqual(trend[0]["count"], 0)
        self.assertEqual(trend[-1]["spend"], Decimal("109.01"))

    def test_insights_average_balance_and_previous_calendar_month(self):
        detail = month_insights(self.rows, "2026-01", 100)
        self.assertEqual(detail["remaining"], Decimal("-9.01"))
        self.assertEqual(detail["average"], Decimal("54.51"))
        self.assertEqual(detail["spend_change"], Decimal("9.02"))
        self.assertEqual(detail["top_category"], "Repair services")

    def test_empty_or_missing_baseline_is_not_presented_as_a_change(self):
        empty = month_insights([], "2026-01", 100)
        self.assertIsNone(empty["average"])
        self.assertIsNone(empty["spend_change"])
        self.assertIsNone(empty["top_category"])
        self.assertIsNone(month_insights(self.rows, "2025-12", 100)["spend_change"])

    def test_free_prior_purchase_is_a_valid_baseline(self):
        free = make_purchase("Repair services", 0, "Gift", "2025-12-01", "gift")
        detail = month_insights([free, self.rows[1]], "2026-01", 100)
        self.assertEqual(detail["spend_change"], Decimal("100.01"))

    def test_filters_combine_without_mutating_records(self):
        original = list(self.rows)
        result = filter_purchases(self.rows, " LOCAL ", "2026-01", "Repair services")
        self.assertEqual([p["id"] for p in result], ["repair2"])
        self.assertEqual(self.rows, original)
        self.assertEqual(filter_purchases(self.rows, "absent"), [])

    def test_price_and_impact_sorts_use_numbers(self):
        self.assertEqual([p["id"] for p in filter_purchases(self.rows, order="Highest price")], ["repair2", "repair", "clothes"])
        result = filter_purchases(self.rows, order="Highest estimated impact")
        self.assertEqual([Decimal(p["estimated_co2"]) for p in result], sorted([Decimal(p["estimated_co2"]) for p in self.rows], reverse=True))
        self.assertEqual(filter_purchases(self.rows, order="Oldest first")[0]["id"], "repair")


if __name__ == "__main__":
    unittest.main()
