import unittest
from pathlib import Path

from parser import parse_upload


DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "test-dataset.xlsx"


class ProjectDatasetTests(unittest.TestCase):
    def test_own_multisheet_dataset_is_combined_without_gaps(self) -> None:
        frame, issues = parse_upload(DATASET_PATH.read_bytes(), DATASET_PATH.name, "1c")

        self.assertEqual(issues, [])
        self.assertEqual(len(frame), 7301)
        self.assertEqual(frame["sku"].nunique(), 10)
        self.assertTrue(
            {
                "sku",
                "date",
                "quantity",
                "price",
                "client_id",
                "warehouse",
                "stock",
                "in_transit",
                "name",
                "category",
                "supplier",
                "lead_time_days",
            }.issubset(frame.columns)
        )
        self.assertEqual(int(frame["stock"].isna().sum()), 0)
        self.assertEqual(int(frame["in_transit"].isna().sum()), 0)
        self.assertEqual(int(frame["supplier"].isna().sum()), 0)
        self.assertEqual(int(frame["lead_time_days"].isna().sum()), 0)

    def test_own_multisheet_dataset_runs_through_full_calculation(self) -> None:
        from calculation import calculate_orders

        frame, _ = parse_upload(DATASET_PATH.read_bytes(), DATASET_PATH.name, "1c")

        result = calculate_orders(frame)

        self.assertEqual(len(result["orders"]), 10)
        self.assertGreater(len(result["excluded_anomalies"]), 0)
        self.assertTrue(all(order["supplier"] != "Не указан" for order in result["orders"]))
        self.assertTrue(all(order["lead_time_days"] > 0 for order in result["orders"]))


if __name__ == "__main__":
    unittest.main()
