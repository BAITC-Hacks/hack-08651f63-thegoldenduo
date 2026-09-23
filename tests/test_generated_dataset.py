import unittest
from io import BytesIO

from calculation import calculate_orders
from generate_test_data import ANOMALY_CLIENT, ANOMALY_SKU, STOCKOUT_SKU, build_tables
from parser import parse_custom_file


class GeneratedDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tables = build_tables()
        buffer = BytesIO()
        with __import__("pandas").ExcelWriter(buffer, engine="openpyxl") as writer:
            for sheet_name, frame in cls.tables.items():
                frame.to_excel(writer, sheet_name=sheet_name, index=False)
        cls.frame, cls.issues = parse_custom_file(buffer.getvalue(), "test-dataset.xlsx")
        cls.result = calculate_orders(cls.frame)

    def test_custom_workbook_is_joined_for_calculation(self) -> None:
        self.assertEqual(self.issues, [])
        self.assertEqual(self.frame["sku"].nunique(), 10)
        self.assertEqual(self.frame["category"].nunique(), 5)
        self.assertEqual(self.frame["supplier"].nunique(), 4)
        self.assertEqual(set(self.frame["lead_time_days"].unique()), {7, 10, 14, 21})
        self.assertGreaterEqual((self.frame["date"].max() - self.frame["date"].min()).days, 365)
        self.assertTrue({"stock", "in_transit", "supplier", "lead_time_days"}.issubset(self.frame))
        current_stocks = self.tables["Остатки"]
        current_stocks = current_stocks[current_stocks["дата"] == current_stocks["дата"].max()]
        self.assertLessEqual(current_stocks["остаток"].min(), 1)
        self.assertGreaterEqual(current_stocks["остаток"].max(), 90)
        transit = self.tables["Товары в пути"]["товары в пути"]
        self.assertTrue((transit == 0).any())
        self.assertTrue((transit > 0).any())

    def test_one_off_order_is_excluded_without_changing_recommendation(self) -> None:
        anomaly = next(item for item in self.result["excluded_anomalies"] if item["client_id"] == ANOMALY_CLIENT)
        self.assertEqual(len(self.result["excluded_anomalies"]), 1)
        self.assertEqual(anomaly["sku"], ANOMALY_SKU)
        self.assertIn("разовая крупная продажа", anomaly["reason"])

        anomaly_sales = self.tables["Продажи"]
        anomaly_qty = int(anomaly_sales.loc[anomaly_sales["обезличенный_клиент_id"] == ANOMALY_CLIENT, "количество"].iloc[0])
        regular_mean = anomaly_sales.loc[
            (anomaly_sales["артикул"] == ANOMALY_SKU)
            & (anomaly_sales["обезличенный_клиент_id"] != ANOMALY_CLIENT),
            "количество",
        ].mean()
        self.assertGreaterEqual(anomaly_qty / regular_mean, 8)
        self.assertLessEqual(anomaly_qty / regular_mean, 10.5)

        baseline_frame = self.frame[self.frame["client_id"] != ANOMALY_CLIENT]
        baseline = calculate_orders(baseline_frame)
        actual_order = next(order for order in self.result["orders"] if order["sku"] == ANOMALY_SKU)
        baseline_order = next(order for order in baseline["orders"] if order["sku"] == ANOMALY_SKU)
        self.assertEqual(actual_order["recommended_qty"], baseline_order["recommended_qty"])

    def test_seasonality_growth_and_stockout_are_visible(self) -> None:
        orders = {order["sku"]: order for order in self.result["orders"]}
        self.assertGreater(orders["HEAT-150"]["reasoning"]["seasonality_factor"], 1.05)
        self.assertLess(orders["PUMP-110"]["reasoning"]["seasonality_factor"], 0.95)
        self.assertGreater(orders["CABL-325"]["reasoning"]["trend_growth"], 0)
        self.assertGreater(orders[STOCKOUT_SKU]["reasoning"]["stockout_compensation"], 0)
        self.assertTrue(orders[STOCKOUT_SKU]["stockout_periods"])


if __name__ == "__main__":
    unittest.main()
