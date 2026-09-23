import unittest

import pandas as pd

from calculation import calculate_orders


def sample_data(include_outlier: bool) -> pd.DataFrame:
    seasonal_pattern = [0, 2, 4, 6, 8, 10, 8, 6, 4, 2, 0, -2]
    rows = []
    for index, date in enumerate(pd.date_range("2024-01-01", periods=24, freq="MS")):
        quantity = 20 + index // 6 + seasonal_pattern[index % 12]
        stock = 0 if index in {9, 10} else 5
        if stock == 0:
            quantity = 0
        rows.append(
            {
                "sku": "ABC-123",
                "date": date,
                "quantity": quantity,
                "price": 100,
                "client_id": f"anon-{index % 4}",
                "warehouse": "Склад №1",
                "stock": stock,
                "in_transit": 2,
                "name": "Автоматический выключатель 16А",
                "category": "Автоматика",
                "supplier": "ООО Поставщик-1",
                "lead_time_days": 10,
            }
        )
    if include_outlier:
        outlier = rows[-1].copy()
        outlier.update(
            {
                "date": pd.Timestamp("2025-12-15"),
                "quantity": rows[-1]["quantity"] * 10,
                "client_id": "anon-outlier",
            }
        )
        rows.append(outlier)
    return pd.DataFrame(rows)


class CalculationTests(unittest.TestCase):
    def test_large_one_off_sale_does_not_change_recommendation(self) -> None:
        baseline = calculate_orders(sample_data(include_outlier=False))
        with_outlier = calculate_orders(sample_data(include_outlier=True))

        self.assertEqual(
            baseline["orders"][0]["recommended_qty"],
            with_outlier["orders"][0]["recommended_qty"],
        )
        self.assertEqual(len(with_outlier["excluded_anomalies"]), 1)
        self.assertEqual(with_outlier["excluded_anomalies"][0]["client_id"], "anon-outlier")

    def test_stockout_adds_lost_demand_compensation(self) -> None:
        stockout_data = sample_data(include_outlier=False)
        result = calculate_orders(stockout_data)
        reasoning = result["orders"][0]["reasoning"]

        no_stockout_data = stockout_data.copy()
        no_stockout_data.loc[no_stockout_data["stock"] <= 0, "quantity"] = 25
        no_stockout_data["stock"] = 5
        no_stockout_result = calculate_orders(no_stockout_data)

        self.assertGreater(reasoning["stockout_compensation"], 0)
        self.assertGreater(len(result["orders"][0]["stockout_periods"]), 0)
        self.assertGreater(
            result["orders"][0]["recommended_qty"],
            no_stockout_result["orders"][0]["recommended_qty"],
        )

    def test_result_keeps_section_four_contract_shape(self) -> None:
        result = calculate_orders(sample_data(include_outlier=True))
        self.assertEqual(set(result), {"orders", "excluded_anomalies"})
        self.assertEqual(
            set(result["orders"][0]),
            {
                "sku",
                "name",
                "category",
                "supplier",
                "warehouse",
                "recommended_qty",
                "urgency",
                "lead_time_days",
                "peak_season_start",
                "reasoning",
                "history",
                "stockout_periods",
            },
        )
        self.assertEqual(result["orders"][0]["lead_time_days"], 10)
        self.assertIsNotNone(result["orders"][0]["peak_season_start"])
        self.assertTrue(result["orders"][0]["peak_season_start"].endswith("-06-01"))


if __name__ == "__main__":
    unittest.main()
