import unittest

from fastapi.testclient import TestClient

from main import app
from test_calculation import sample_data


class ApiTests(unittest.TestCase):
    def test_upload_calculate_and_contract_endpoints(self) -> None:
        client = TestClient(app)
        csv_content = sample_data(include_outlier=True).to_csv(index=False).encode("utf-8")

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


if __name__ == "__main__":
    unittest.main()
