"""Demand forecasting and anomaly detection for the order calculation core."""

from __future__ import annotations

import math
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


class CalculationError(ValueError):
    """Raised when validated input still cannot be used for a calculation."""


def _number(value: float) -> int | float:
    rounded = round(float(value), 2)
    return int(rounded) if rounded.is_integer() else rounded


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    for column in ("quantity", "stock", "price"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if "in_transit" not in data:
        data["in_transit"] = 0.0
    data["in_transit"] = pd.to_numeric(data["in_transit"], errors="coerce").fillna(0.0)
    if "lead_time_days" not in data:
        data["lead_time_days"] = 14
    data["lead_time_days"] = (
        pd.to_numeric(data["lead_time_days"], errors="coerce").fillna(14).clip(lower=0)
    )
    for column, default in {
        "name": None,
        "category": "Без категории",
        "supplier": "Не указан",
    }.items():
        if column not in data:
            data[column] = default

    invalid = data[["sku", "date", "quantity", "client_id", "warehouse", "stock"]].isna().any(axis=1)
    if invalid.any():
        raise CalculationError(f"Невозможно рассчитать: некорректных обязательных строк — {int(invalid.sum())}.")
    if (data["quantity"] < 0).any():
        raise CalculationError("Количество продаж не может быть отрицательным.")
    data["sku"] = data["sku"].astype(str)
    data["client_id"] = data["client_id"].astype(str)
    data["warehouse"] = data["warehouse"].astype(str)
    data["name"] = data["name"].fillna(data["sku"]).astype(str)
    data["category"] = data["category"].fillna("Без категории").astype(str)
    data["supplier"] = data["supplier"].fillna("Не указан").astype(str)
    return data.sort_values("date").reset_index(drop=True)


def detect_anomalies(data: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Remove unusually large SKU/client/day totals using a per-SKU IQR fence."""
    transaction_totals = (
        data.groupby(["sku", "client_id", "date"], as_index=False, dropna=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "transaction_qty"})
    )
    anomalous_keys: list[pd.DataFrame] = []
    for _, sku_rows in transaction_totals.groupby("sku", sort=False):
        quantities = sku_rows["transaction_qty"].astype(float)
        if len(quantities) < 4:
            continue
        q1, q3 = quantities.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr > 0:
            # A conservative outer fence avoids treating legitimate seasonal peaks
            # as one-off orders while still catching the 8-10x customer spikes that
            # matter for regular replenishment.
            upper_fence = max(q3 + 3.0 * iqr, float(quantities.median()) * 3.0)
        else:
            # A zero IQR is common for steady sales; retain small natural variation.
            upper_fence = max(q3 * 3.0, q3 + 1.0)
        flagged = sku_rows[sku_rows["transaction_qty"] > upper_fence].copy()
        if not flagged.empty:
            anomalous_keys.append(flagged)

    if not anomalous_keys:
        return data.copy(), []

    anomalies_frame = pd.concat(anomalous_keys, ignore_index=True)
    key_index = pd.MultiIndex.from_frame(anomalies_frame[["sku", "client_id", "date"]])
    row_index = pd.MultiIndex.from_frame(data[["sku", "client_id", "date"]])
    clean_data = data.loc[~row_index.isin(key_index)].copy()
    anomalies = [
        {
            "sku": str(row.sku),
            "date": row.date.date().isoformat(),
            "qty": _number(row.transaction_qty),
            "client_id": str(row.client_id),
            "reason": "разовая крупная продажа одному клиенту (IQR-выброс)",
        }
        for row in anomalies_frame.itertuples(index=False)
    ]
    return clean_data, anomalies


def _monthly_history(sku_data: pd.DataFrame) -> pd.Series:
    monthly = sku_data.set_index("date")["quantity"].resample("MS").sum().astype(float)
    return monthly.asfreq("MS", fill_value=0.0)


def _forecast(monthly: pd.Series) -> tuple[float, float, float, float]:
    """Return next-period forecast, recent base, seasonality factor and stable trend growth."""
    if monthly.empty:
        return 0.0, 0.0, 1.0, 0.0
    recent = monthly.tail(min(6, len(monthly)))
    base_demand = max(float(recent.mean()), 0.0)

    nonseasonal_forecast = base_demand
    if len(monthly) >= 4 and monthly.nunique() > 1:
        try:
            model = ExponentialSmoothing(
                monthly,
                trend="add",
                damped_trend=True,
                initialization_method="estimated",
            ).fit(optimized=True)
            nonseasonal_forecast = max(float(model.forecast(1).iloc[0]), 0.0)
        except (ValueError, RuntimeError, OverflowError):
            nonseasonal_forecast = base_demand

    forecast = nonseasonal_forecast
    seasonality_factor = 1.0
    if len(monthly) >= 24 and monthly.nunique() > 1:
        try:
            seasonal_model = ExponentialSmoothing(
                monthly,
                trend="add",
                damped_trend=True,
                seasonal="add",
                seasonal_periods=12,
                initialization_method="estimated",
            ).fit(optimized=True)
            forecast = max(float(seasonal_model.forecast(1).iloc[0]), 0.0)
            if nonseasonal_forecast > 0:
                seasonality_factor = float(np.clip(forecast / nonseasonal_forecast, 0.25, 4.0))
        except (ValueError, RuntimeError, OverflowError):
            forecast = nonseasonal_forecast

    trend_growth = 0.0
    if len(monthly) >= 4 and float(monthly.mean()) > 0:
        x = np.arange(len(monthly), dtype=float)
        slope, intercept = np.polyfit(x, monthly.to_numpy(dtype=float), 1)
        predicted = intercept + slope * x
        residual_sum = float(np.square(monthly.to_numpy(dtype=float) - predicted).sum())
        total_sum = float(np.square(monthly.to_numpy(dtype=float) - monthly.mean()).sum())
        r_squared = 1.0 - residual_sum / total_sum if total_sum > 0 else 0.0
        if slope > 0 and r_squared >= 0.2:
            trend_growth = float(np.clip(slope / max(base_demand, 1.0), 0.0, 1.0))

    return forecast, base_demand, seasonality_factor, trend_growth


def _stockout_details(all_sku_data: pd.DataFrame, clean_sku_data: pd.DataFrame) -> tuple[float, list[dict[str, str]]]:
    daily_stock = all_sku_data.groupby("date")["stock"].min().sort_index()
    stockout_dates = daily_stock[daily_stock <= 0].index
    if stockout_dates.empty:
        return 0.0, []

    clean_daily = clean_sku_data.groupby("date")["quantity"].sum()
    normal_dates = daily_stock[daily_stock > 0].index
    normal_sales = clean_daily.reindex(normal_dates, fill_value=0.0)
    expected_daily = float(normal_sales.median()) if not normal_sales.empty else 0.0
    observed_during_stockout = clean_daily.reindex(stockout_dates, fill_value=0.0)
    compensation = float(np.maximum(expected_daily - observed_during_stockout.to_numpy(), 0.0).sum())

    periods: list[dict[str, str]] = []
    period_start = previous = stockout_dates[0]
    for current in stockout_dates[1:]:
        if (current - previous).days > 1:
            periods.append({"start": period_start.date().isoformat(), "end": previous.date().isoformat()})
            period_start = current
        previous = current
    periods.append({"start": period_start.date().isoformat(), "end": previous.date().isoformat()})
    return compensation, periods


def _peak_season_start(monthly: pd.Series, today: date | None = None) -> str | None:
    """Return the nearest future start of a reliably recurring peak month."""
    if len(monthly) < 24 or monthly.index.month.nunique() < 12:
        return None

    month_averages = monthly.groupby(monthly.index.month).mean()
    overall_average = float(monthly.mean())
    if overall_average <= 0:
        return None

    peak_month = int(month_averages.idxmax())
    peak_strength = float(month_averages.loc[peak_month]) / overall_average
    if peak_strength < 1.15:
        return None

    reference = today or date.today()
    candidate = date(reference.year, peak_month, 1)
    if candidate <= reference:
        candidate = date(reference.year + 1, peak_month, 1)
    return candidate.isoformat()


def calculate_orders(
    source: pd.DataFrame,
    warehouse: str | None = None,
    category: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Calculate contract-compatible recommendations from an uploaded dataset."""
    data = _prepare(source)
    if warehouse:
        data = data[data["warehouse"] == warehouse]
    if category:
        data = data[data["category"] == category]
    if data.empty:
        return {"orders": [], "excluded_anomalies": []}

    clean_data, anomalies = detect_anomalies(data)
    orders: list[dict[str, Any]] = []
    for sku, all_sku_data in data.groupby("sku", sort=True):
        clean_sku_data = clean_data[clean_data["sku"] == sku]
        if clean_sku_data.empty:
            continue
        monthly = _monthly_history(clean_sku_data)
        forecast, base_demand, seasonality_factor, sku_trend_growth = _forecast(monthly)
        category = str(all_sku_data.iloc[-1]["category"])
        category_data = clean_data[clean_data["category"] == category]
        category_monthly = _monthly_history(category_data)
        _, _, _, category_trend_growth = _forecast(category_monthly)

        # The SKU model remains dominant, while category growth provides a stable
        # signal for sparse/noisy item histories.
        trend_growth = 0.75 * sku_trend_growth + 0.25 * category_trend_growth
        forecast *= 1.0 + trend_growth - sku_trend_growth
        forecast = max(forecast, 0.0)
        stockout_compensation, stockout_periods = _stockout_details(all_sku_data, clean_sku_data)
        peak_season_start = _peak_season_start(monthly)

        latest = all_sku_data.sort_values("date").iloc[-1]
        current_stock = max(float(latest["stock"]), 0.0)
        in_transit = max(float(latest["in_transit"]), 0.0)
        lead_time_days = int(round(float(latest["lead_time_days"])))
        recommended = max(0, math.ceil(forecast + stockout_compensation - current_stock - in_transit))
        if current_stock <= 0 or recommended >= max(forecast * 0.75, 1.0):
            urgency = "critical"
        elif recommended > 0:
            urgency = "high"
        else:
            urgency = "normal"

        history = [
            {"date": index.date().isoformat(), "qty": _number(value)}
            for index, value in monthly.items()
        ]
        explanation = (
            f"Прогноз спроса: {forecast:.1f}; текущий остаток: {current_stock:.1f}; "
            f"в пути: {in_transit:.1f}; компенсация stockout: {stockout_compensation:.1f}. "
            f"Тренд артикула и категории «{category}» учтён. "
            "Крупные разовые продажи исключены IQR-детектором."
        )
        orders.append(
            {
                "sku": str(sku),
                "name": str(latest["name"]),
                "category": str(latest["category"]),
                "supplier": str(latest["supplier"]),
                "warehouse": str(latest["warehouse"]),
                "recommended_qty": recommended,
                "urgency": urgency,
                "lead_time_days": lead_time_days,
                "peak_season_start": peak_season_start,
                "reasoning": {
                    "base_demand": _number(base_demand),
                    "seasonality_factor": _number(seasonality_factor),
                    "stockout_compensation": _number(stockout_compensation),
                    "trend_growth": _number(trend_growth),
                    "explanation_text": explanation,
                },
                "history": history,
                "stockout_periods": stockout_periods,
            }
        )
    return {"orders": orders, "excluded_anomalies": anomalies}
