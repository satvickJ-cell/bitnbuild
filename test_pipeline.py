import unittest
import json
import os
from fastapi.testclient import TestClient

from schema import WardBudgetData, EvaluationResult, ProcessPDFResponse
from evaluator import evaluate_ward_data, load_rules
from action_agent import load_rti_template, draft_rti
from main import app

class TestCivicBackend(unittest.TestCase):
    
    def setUp(self):
        self.client = TestClient(app)

    def test_schema_instantiation(self):
        data = WardBudgetData(
            ward_number=14,
            budget_head="2217-01-101 Drainage Infrastructure",
            amount_this_year=2500000.0,
            amount_last_year=3500000.0,
            drain_length_km=15.5,
            zone_new="Commercial Central",
            stated_road_width=14.0
        )
        self.assertEqual(data.ward_number, 14)
        self.assertEqual(data.drain_length_km, 15.5)

    def test_evaluator_flag_triggered(self):
        data = WardBudgetData(
            ward_number=42,
            budget_head="2217-01-101 Drainage",
            amount_this_year=1000000.0,
            amount_last_year=4000000.0,
            drain_length_km=10.0,
            zone_new="Commercial Zone",
            stated_road_width=8.0
        )
        res = evaluate_ward_data(data)
        self.assertTrue(res["flag_triggered"])
        self.assertIn("Violation 1", res["plain_english_reason"])
        self.assertIn("Violation 3", res["plain_english_reason"])
        self.assertIn("negligence_score", res)
        self.assertIn("risk_level", res)

    def test_evaluator_risk_score_calculation(self):
        data = WardBudgetData(
            ward_number=150,
            budget_head="Drainage Works",
            amount_this_year=1200000.0,
            amount_last_year=4500000.0,
            drain_length_km=18.5,
            zone_new="Mahadevapura",
            stated_road_width=9.0
        )
        res = evaluate_ward_data(data)
        self.assertEqual(res["negligence_score"], 66.7)
        self.assertEqual(res["risk_level"], "CRITICAL RISK")
        self.assertEqual(res["risk_color"], "#ef4444")
        self.assertEqual(res["cost_per_km"], 64864.86)
        self.assertEqual(res["cost_per_km_formatted"], "₹64,864/km")
        self.assertEqual(res["statutory_norm_formatted"], "₹1,50,000/km")
        self.assertEqual(res["yoy_cut_percentage"], "-73.3%")



    def test_evaluator_json_string_input_and_type_safety(self):
        # Test string JSON input with string numeric values
        json_input = json.dumps({
            "ward_number": "42",
            "budget_head": "2217-01-101",
            "amount_this_year": "1000000",
            "amount_last_year": "4000000",
            "drain_length_km": "10",
            "zone_new": "Commercial Zone",
            "stated_road_width": "8"
        })
        res = evaluate_ward_data(json_input)
        self.assertTrue(res["flag_triggered"])

    def test_evaluator_compliant(self):
        data = WardBudgetData(
            ward_number=7,
            budget_head="2217-01-101 Storm Drains",
            amount_this_year=5000000.0,
            amount_last_year=4800000.0,
            drain_length_km=10.0,
            zone_new="Commercial Zone",
            stated_road_width=15.0
        )
        res = evaluate_ward_data(data)
        self.assertFalse(res["flag_triggered"])
        self.assertIn("complies with all civic rules", res["plain_english_reason"])

    def test_template_loading(self):
        template = load_rti_template()
        self.assertIn("[WARD_NUMBER]", template)
        self.assertIn("[BUDGET_HEAD]", template)
        self.assertIn("[DISCREPANCY_DETAILS]", template)

    def test_fastapi_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_fastapi_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_fastapi_process_json_endpoint(self):
        payload = {
            "ward_number": 7,
            "budget_head": "2217-01-101 Storm Drains",
            "amount_this_year": 5000000.0,
            "amount_last_year": 4800000.0,
            "drain_length_km": 10.0,
            "zone_new": "Commercial Zone",
            "stated_road_width": 15.0
        }
        response = self.client.post("/process_json", json=payload)
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertFalse(res_data["evaluation"]["flag_triggered"])
        self.assertEqual(res_data["extracted_data"]["ward_number"], 7)
        self.assertIn("dashboard_metrics", res_data)
        self.assertEqual(res_data["dashboard_metrics"]["risk_level"], "COMPLIANT")
        self.assertEqual(res_data["dashboard_metrics"]["risk_color"], "#22c55e")


if __name__ == "__main__":
    unittest.main()
