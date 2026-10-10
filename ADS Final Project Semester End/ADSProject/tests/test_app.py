import unittest
import json
from pathlib import Path

from app import app


class AppRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app.test_client()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_root_redirects_when_signed_out(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_guide_requires_authentication(self):
        response = self.client.get("/guide")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_invalid_similarity_is_rejected(self):
        response = self.client.get("/api/insights?min_similarity=invalid")
        self.assertEqual(response.status_code, 400)

    def test_model_benchmark_requires_authentication(self):
        response = self.client.get("/api/model-benchmark")
        self.assertEqual(response.status_code, 401)

    def test_model_benchmark_contains_both_targets(self):
        report_path = Path(__file__).parents[1] / "data" / "processed" / "model_validation_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(set(report["targets"]), {"monthly_orders", "monthly_revenue_inr"})
    def test_analysis_page_accessible(self):
        response = self.client.get("/analysis")
        self.assertEqual(response.status_code, 200)

    def test_analysis_areas_api(self):
        response = self.client.get("/api/analysis/areas")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 20)
        first = data[0]
        self.assertIn("city", first)
        self.assertIn("area", first)
        self.assertIn("osm_competitors", first)
        self.assertIn("avg_similarity", first)

    def test_analysis_dishes_api(self):
        response = self.client.get("/api/analysis/dishes")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 100)
        first = data[0]
        self.assertIn("dish", first)
        self.assertIn("category", first)
        self.assertIn("coverage_pct", first)
        self.assertIn("avg_price_inr", first)


    def test_predict_concept_with_typos_and_price(self):
        payload = {
            "city": "Bangalore",
            "location": "Indiranagar",
            "menu_items": ["paner butter masla", "Truffle Ramen"],
            "price": 280,
        }
        response = self.client.post("/api/predict-concept", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("typo_corrections", data)
        self.assertIn("novel_dishes", data)
        self.assertTrue(any(c["original"] == "paner butter masla" for c in data["typo_corrections"]))
        self.assertTrue(any(n["dish"] == "Truffle Ramen" for n in data["novel_dishes"]))
        self.assertIsNotNone(data["price_analysis"])
        self.assertIsNotNone(data["ml_performance_prediction"])
        self.assertGreater(data["ml_performance_prediction"]["estimated_monthly_orders"], 0)
        self.assertGreater(data["ml_performance_prediction"]["estimated_monthly_revenue_inr"], 0)


if __name__ == "__main__":
    unittest.main()
