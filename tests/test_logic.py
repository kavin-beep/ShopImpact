import json
import unittest
from datetime import date
from decimal import Decimal
from logic import CATALOG, badges, demo_records, impact, make_purchase, money, month_records, summary, update_purchase
from storage import export_csv, export_json, import_json


class LogicTests(unittest.TestCase):
    def purchase(self, category="Repair services", price=100, day="2026-10-01"):
        return make_purchase(category, price, "Test shop", day)

    def test_formula_and_decimal_rounding(self):
        self.assertEqual(impact("650", "Second-hand clothing"), Decimal("0.81"))
        self.assertEqual(money("10.005"), Decimal("10.01"))

    def test_invalid_prices(self):
        for price in [-1, "NaN", "Infinity", "oops", None, True, 10000001]:
            with self.subTest(price=price), self.assertRaises(ValueError):
                money(price)

    def test_empty_brand_and_invalid_dates(self):
        for brand, day in [(" ", "2026-10-01"), ("a" * 81, "2026-10-01"), ("Shop", "2026-02-30"), ("Shop", "1999-01-01")]:
            with self.subTest(brand=brand, day=day), self.assertRaises(ValueError):
                make_purchase("Repair services", 100, brand, day)

    def test_unknown_category(self):
        with self.assertRaises(ValueError):
            impact(10, "Unknown")

    def test_zero_price_allowed(self):
        self.assertEqual(impact(0, "New electronics"), Decimal("0.00"))

    def test_year_and_month_filter(self):
        rows = [self.purchase(day=d) for d in ["2025-12-31", "2026-01-01", "2026-12-31"]]
        self.assertEqual(len(month_records(rows, "2025-12")), 1)
        self.assertEqual(month_records(rows, "2026-01")[0]["purchase_date"], "2026-01-01")

    def test_summary_known_values(self):
        rows = [self.purchase("New clothing", 1000), self.purchase("Second-hand clothing", 500)]
        self.assertEqual(summary(rows), {"spend": Decimal("1500"), "co2": Decimal("1.86"), "count": 2, "lower": 1})

    def test_empty_no_badges(self):
        self.assertEqual(badges([]), [])

    def test_eco_saver_boundary(self):
        for estimate, eligible in [("29.99", True), ("30.00", True), ("30.01", False)]:
            rows = [self.purchase() for _ in range(3)]
            for row, value in zip(rows, ["10.00", "10.00", estimate]):
                row["estimated_co2"] = value
            self.assertEqual("Eco Saver" in badges(rows), eligible)
        self.assertNotIn("Eco Saver", badges([self.purchase()]))

    def test_lower_factor_badge_boundary(self):
        rows = [self.purchase() for _ in range(3)] + [self.purchase("New clothing") for _ in range(2)]
        self.assertIn("Low Impact Shopper", badges(rows))
        rows.append(self.purchase("New clothing"))
        self.assertNotIn("Low Impact Shopper", badges(rows))

    def test_edit_recalculates_and_keeps_id(self):
        old = self.purchase()
        new = make_purchase("New electronics", 1000, "New shop", "2026-11-01", old["id"])
        updated = update_purchase([old], new)
        self.assertEqual(updated[0]["estimated_co2"], "0.67")
        self.assertEqual(month_records(updated, "2026-10"), [])
        self.assertEqual(old["price"], "100.00")

    def test_demo_has_15_and_handles_january(self):
        rows = demo_records(date(2026, 1, 1))
        self.assertEqual(len(rows), 15)
        self.assertEqual(len(month_records(rows, "2025-12")), 5)
        self.assertEqual(len({p["id"] for p in rows}), 15)

    def test_all_categories_have_alternatives(self):
        self.assertTrue(all(len(item["alternatives"]) >= 3 for item in CATALOG.values()))
        from logic import ROOT
        links = json.loads((ROOT / "data/alternative_links.json").read_text())
        self.assertEqual(set(links), set(CATALOG))
        self.assertTrue(all(options and all(item["url"].startswith("https://") for item in options) for options in links.values()))

    def test_backup_roundtrip(self):
        rows = demo_records(date(2026, 10, 1))
        self.assertEqual(import_json(export_json(rows)), rows)

    def test_backup_does_not_trust_estimate(self):
        row = self.purchase()
        row["estimated_co2"] = "999999"
        self.assertEqual(import_json(export_json([row]))[0]["estimated_co2"], "0.12")

    def test_legacy_backup_requires_explicit_migration(self):
        backup = json.loads(export_json([self.purchase()]))
        backup["version"] = "illustrative-inr-v1"
        with self.assertRaises(ValueError):
            import_json(json.dumps(backup))
        self.assertEqual(import_json(json.dumps(backup), allow_legacy=True)[0]["estimated_co2"], "0.12")

    def test_factor_provenance_and_no_invented_reuse_discount(self):
        from logic import ROOT
        source = json.loads((ROOT / "data/emission_sources.json").read_text())
        rows = {r["2017 NAICS Code"]: r for r in source["rows"]}
        fx = Decimal(source["fx_inr_per_usd"])
        for item in CATALOG.values():
            official = Decimal(rows[item["source_code"]]["Supply Chain Emission Factors with Margins"])
            expected = (official / fx).quantize(Decimal("0.000000000001"))
            self.assertEqual(Decimal(item["multiplier"]), expected)
        self.assertEqual(impact(500, "New clothing"), impact(500, "Second-hand clothing"))

    def test_duplicate_ids_rejected(self):
        row = self.purchase()
        with self.assertRaises(ValueError):
            import_json(export_json([row, row]))

    def test_previous_reference_backup_requires_opt_in(self):
        from logic import ROOT, VERSION
        old = json.loads((ROOT / "tests/sample_purchases.json").read_text())
        with self.assertRaises(ValueError):
            import_json(json.dumps(old))
        migrated = import_json(json.dumps(old), allow_legacy=True)
        self.assertEqual(len(migrated), 15)
        self.assertEqual(migrated[0]["id"], old["purchases"][0]["id"])
        self.assertTrue(all(p["methodology"] == VERSION for p in migrated))
        # Even a current-format backup may contain purchases saved under older data.
        old["version"] = VERSION
        with self.assertRaises(ValueError):
            import_json(json.dumps(old))

    def test_recalculation_preserves_purchase_details_and_original(self):
        from logic import VERSION, recalculate_purchases
        old = self.purchase("New clothing", 1000)
        old.update(methodology="epa-2022-inr-reference-v2", estimated_co2="1.53")
        updated = recalculate_purchases([old])[0]
        self.assertEqual(old["estimated_co2"], "1.53")
        self.assertEqual(updated["estimated_co2"], "1.24")
        self.assertEqual(updated["methodology"], VERSION)
        for field in ("id", "brand", "price", "purchase_date", "product_type"):
            self.assertEqual(updated[field], old[field])

    def test_malformed_backup(self):
        for raw in ["{", "[]", '{"version":"wrong"}', export_json([{}]), "x" * 2000001]:
            with self.subTest(raw=raw[:60]), self.assertRaises(ValueError):
                import_json(raw)

    def test_csv_formula_neutralized(self):
        row = self.purchase()
        row["brand"] = "=1+1"
        self.assertIn("'=1+1", export_csv([row]))


if __name__ == "__main__":
    unittest.main()
