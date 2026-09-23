import unittest

import pandas as pd
from fastapi.testclient import TestClient

from main import app
from test_calculation import sample_data


class ApiTests(unittest.TestCase):
    def test_upload_calculate_and_contract_endpoints(self) -> None:
        client = TestClient(app)
        primary = sample_data(include_outlier=True)
        secondary = sample_data(include_outlier=False).assign(
            sku="XYZ-900",
            quantity=10,
            stock=2,
            in_transit=1,
            name="Кабель силовой",
            category="Кабели",
            supplier="ООО Поставщик-2",
            lead_time_days=21,
        )
        secondary["client_id"] = "second-" + secondary["client_id"]
        csv_content = pd.concat([primary, secondary], ignore_index=True).to_csv(index=False).encode("utf-8")

        upload = client.post(
            "/upload",
            data={"mode": "custom"},
            files={"file": ("sales.csv", csv_content, "text/csv")},
        )
        self.assertEqual(upload.status_code, 200, upload.text)

        calculation = client.post("/calculate")
        self.assertEqual(calculation.status_code, 200, calculation.text)

        orders = client.get("/orders")
        anomalies = client.get("/anomalies")
        self.assertEqual(orders.status_code, 200)
        self.assertEqual(set(orders.json()), {"orders", "excluded_anomalies"})
        self.assertEqual(orders.json(), calculation.json()["result"])
        self.assertEqual(anomalies.json(), orders.json()["excluded_anomalies"])
        self.assertEqual(anomalies.json()[0]["client_id"], "anon-outlier")
        orders_by_sku = {order["sku"]: order for order in orders.json()["orders"]}
        self.assertEqual(orders_by_sku["ABC-123"]["lead_time_days"], 10)
        self.assertEqual(orders_by_sku["XYZ-900"]["lead_time_days"], 21)
        self.assertIn("peak_season_start", orders_by_sku["ABC-123"])

        adjustment = client.post(
            "/orders/ABC-123/adjust",
            json={"quantity": 60, "reason": "Менеджер подтвердил ожидаемую поставку"},
        )
        self.assertEqual(adjustment.status_code, 200, adjustment.text)
        self.assertEqual(adjustment.json()["quantity"], 60)
        self.assertEqual(adjustment.json()["previous_quantity"], 75)

        approval = client.post(
            "/orders/approve",
            json={"comment": "Подготовить к экспорту"},
        )
        self.assertEqual(approval.status_code, 200, approval.text)
        self.assertFalse(approval.json()["sent_to_supplier"])
        self.assertEqual(approval.json()["status"], "approved_for_export")
        self.assertEqual(len(approval.json()["suppliers"]), 2)
        supplier_group = next(
            group for group in approval.json()["suppliers"] if group["supplier"] == "ООО Поставщик-1"
        )
        self.assertEqual(supplier_group["supplier"], "ООО Поставщик-1")
        self.assertEqual(supplier_group["total_quantity"], 60)
        self.assertEqual(
            supplier_group["items"][0]["adjustment_reason"],
            "Менеджер подтвердил ожидаемую поставку",
        )


if __name__ == "__main__":
    unittest.main()
