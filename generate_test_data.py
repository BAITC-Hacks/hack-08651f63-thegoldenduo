"""Generate a deterministic multi-sheet dataset for the custom upload mode."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_PATH = Path(__file__).with_name("test-dataset.xlsx")
START_DATE = pd.Timestamp("2024-10-01")
END_DATE = pd.Timestamp("2026-09-30")
ANOMALY_SKU = "AUTO-B16"
ANOMALY_CLIENT = "anon-anomaly-001"
STOCKOUT_SKU = "PUMP-075"
STOCKOUT_START = pd.Timestamp("2026-07-10")
STOCKOUT_END = pd.Timestamp("2026-07-30")


PRODUCTS = [
    {
        "sku": "HEAT-150",
        "name": "Электрический конвектор 1,5 кВт",
        "category": "Климатическая техника",
        "warehouse": "Алматы — основной",
        "base_daily": 2.4,
        "pattern": "winter",
        "monthly_growth": 0.004,
        "price": 34900,
        "current_stock": 4,
        "historical_stock": 35,
        "in_transit": 18,
        "supplier": "ТОО Qazaq Climate",
        "lead_time_days": 14,
    },
    {
        "sku": "BOIL-080",
        "name": "Электрический котёл 8 кВт",
        "category": "Климатическая техника",
        "warehouse": "Астана — центральный",
        "base_daily": 1.5,
        "pattern": "winter",
        "monthly_growth": 0.008,
        "price": 189000,
        "current_stock": 14,
        "historical_stock": 28,
        "in_transit": 0,
        "supplier": "ТОО Qazaq Climate",
        "lead_time_days": 14,
    },
    {
        "sku": "FAN-045",
        "name": "Вентилятор промышленный 450 мм",
        "category": "Климатическая техника",
        "warehouse": "Алматы — основной",
        "base_daily": 2.1,
        "pattern": "summer",
        "monthly_growth": 0.006,
        "price": 58500,
        "current_stock": 42,
        "historical_stock": 55,
        "in_transit": 0,
        "supplier": "ТОО Qazaq Climate",
        "lead_time_days": 14,
    },
    {
        "sku": "CABL-325",
        "name": "Кабель ВВГнг 3×2,5, бухта 100 м",
        "category": "Кабельная продукция",
        "warehouse": "Алматы — основной",
        "base_daily": 3.4,
        "pattern": "flat",
        "monthly_growth": 0.025,
        "price": 42800,
        "current_stock": 2,
        "historical_stock": 75,
        "in_transit": 30,
        "supplier": "АО КазКабель",
        "lead_time_days": 10,
    },
    {
        "sku": ANOMALY_SKU,
        "name": "Автоматический выключатель B16",
        "category": "Автоматика",
        "warehouse": "Алматы — основной",
        "base_daily": 4.0,
        "pattern": "flat",
        "monthly_growth": 0.0,
        "price": 2750,
        "current_stock": 6,
        "historical_stock": 90,
        "in_transit": 20,
        "supplier": "ТОО ElectroSupply",
        "lead_time_days": 7,
    },
    {
        "sku": "RCD-040",
        "name": "УЗО 40А 30мА",
        "category": "Автоматика",
        "warehouse": "Астана — центральный",
        "base_daily": 2.7,
        "pattern": "flat",
        "monthly_growth": 0.018,
        "price": 14600,
        "current_stock": 1,
        "historical_stock": 48,
        "in_transit": 0,
        "supplier": "ТОО ElectroSupply",
        "lead_time_days": 7,
    },
    {
        "sku": "LED-020",
        "name": "LED-прожектор 20 Вт",
        "category": "Освещение",
        "warehouse": "Шымкент — южный",
        "base_daily": 3.0,
        "pattern": "flat",
        "monthly_growth": 0.0,
        "price": 7900,
        "current_stock": 95,
        "historical_stock": 110,
        "in_transit": 0,
        "supplier": "ТОО Industrial Trade KZ",
        "lead_time_days": 21,
    },
    {
        "sku": "LAMP-012",
        "name": "Светильник уличный LED 120 Вт",
        "category": "Освещение",
        "warehouse": "Астана — центральный",
        "base_daily": 1.8,
        "pattern": "summer",
        "monthly_growth": 0.01,
        "price": 63500,
        "current_stock": 18,
        "historical_stock": 36,
        "in_transit": 12,
        "supplier": "ТОО Industrial Trade KZ",
        "lead_time_days": 21,
    },
    {
        "sku": STOCKOUT_SKU,
        "name": "Насос циркуляционный 75 Вт",
        "category": "Насосное оборудование",
        "warehouse": "Шымкент — южный",
        "base_daily": 2.8,
        "pattern": "summer",
        "monthly_growth": 0.006,
        "price": 31200,
        "current_stock": 3,
        "historical_stock": 44,
        "in_transit": 8,
        "supplier": "ТОО Industrial Trade KZ",
        "lead_time_days": 21,
    },
    {
        "sku": "PUMP-110",
        "name": "Насос дренажный 1,1 кВт",
        "category": "Насосное оборудование",
        "warehouse": "Алматы — основной",
        "base_daily": 1.7,
        "pattern": "summer",
        "monthly_growth": 0.012,
        "price": 87500,
        "current_stock": 27,
        "historical_stock": 40,
        "in_transit": 0,
        "supplier": "ТОО Industrial Trade KZ",
        "lead_time_days": 21,
    },
]

SEASONAL_FACTORS = {
    "flat": {month: 1.0 for month in range(1, 13)},
    "winter": {
        1: 1.75,
        2: 1.45,
        3: 1.10,
        4: 0.82,
        5: 0.68,
        6: 0.58,
        7: 0.55,
        8: 0.62,
        9: 0.82,
        10: 1.12,
        11: 1.55,
        12: 1.95,
    },
    "summer": {
        1: 0.60,
        2: 0.62,
        3: 0.78,
        4: 1.00,
        5: 1.35,
        6: 1.75,
        7: 1.90,
        8: 1.70,
        9: 1.20,
        10: 0.88,
        11: 0.70,
        12: 0.62,
    },
}


def build_tables(seed: int = 8615) -> dict[str, pd.DataFrame]:
    """Build the four custom-upload tables with repeatable business scenarios."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    sales_rows: list[dict[str, object]] = []
    stock_rows: list[dict[str, object]] = []
    transit_rows: list[dict[str, object]] = []
    supplier_rows: list[dict[str, object]] = []

    for product_index, product in enumerate(PRODUCTS):
        sku = str(product["sku"])
        for date in dates:
            month_index = (date.year - START_DATE.year) * 12 + date.month - START_DATE.month
            seasonal = SEASONAL_FACTORS[str(product["pattern"])][date.month]
            trend = 1.0 + float(product["monthly_growth"]) * month_index
            weekday = 0.82 if date.weekday() >= 5 else 1.05
            expected = float(product["base_daily"]) * seasonal * trend * weekday
            quantity = max(0, int(round(expected + rng.normal(0, 0.65))))
            is_stockout = sku == STOCKOUT_SKU and STOCKOUT_START <= date <= STOCKOUT_END
            if is_stockout:
                quantity = 0 if date.day % 5 else 1

            sales_rows.append(
                {
                    "артикул": sku,
                    "наименование": product["name"],
                    "категория": product["category"],
                    "дата": date,
                    "количество": quantity,
                    "цена": int(round(float(product["price"]) * (1 + 0.003 * month_index))),
                    "обезличенный_клиент_id": f"anon-{product_index + 1:02d}-{date.day % 7 + 1:02d}",
                    "склад": product["warehouse"],
                }
            )

            stock = int(product["historical_stock"])
            if is_stockout:
                stock = 0
            elif date == END_DATE:
                stock = int(product["current_stock"])
            stock_rows.append(
                {
                    "артикул": sku,
                    "дата": date,
                    "склад": product["warehouse"],
                    "остаток": stock,
                }
            )

        transit_rows.append(
            {
                "артикул": sku,
                "склад": product["warehouse"],
                "товары в пути": int(product["in_transit"]),
            }
        )
        supplier_rows.append(
            {
                "артикул": sku,
                "поставщик": product["supplier"],
                "срок поставки, дней": int(product["lead_time_days"]),
            }
        )

    regular_anomaly_sales = [
        int(row["количество"])
        for row in sales_rows
        if row["артикул"] == ANOMALY_SKU and int(row["количество"]) > 0
    ]
    typical_quantity = int(round(float(np.mean(regular_anomaly_sales))))
    anomaly_date = pd.Timestamp("2026-05-14")
    sales_rows.append(
        {
            "артикул": ANOMALY_SKU,
            "наименование": "Автоматический выключатель B16",
            "категория": "Автоматика",
            "дата": anomaly_date,
            "количество": typical_quantity * 10,
            "цена": 2910,
            "обезличенный_клиент_id": ANOMALY_CLIENT,
            "склад": "Алматы — основной",
        }
    )

    return {
        "Продажи": pd.DataFrame(sales_rows).sort_values(["дата", "артикул", "обезличенный_клиент_id"]),
        "Остатки": pd.DataFrame(stock_rows).sort_values(["дата", "артикул"]),
        "Товары в пути": pd.DataFrame(transit_rows).sort_values("артикул"),
        "Поставщики": pd.DataFrame(supplier_rows).sort_values("артикул"),
    }


def generate_workbook(output_path: Path = OUTPUT_PATH) -> Path:
    tables = build_tables()
    with pd.ExcelWriter(output_path, engine="openpyxl", datetime_format="YYYY-MM-DD") as writer:
        for sheet_name, frame in tables.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.book[sheet_name]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for column_cells in worksheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 42)
    return output_path


if __name__ == "__main__":
    result = generate_workbook()
    print(f"Создан тестовый датасет: {result}")
