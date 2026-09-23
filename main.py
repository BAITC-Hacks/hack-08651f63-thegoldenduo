"""FastAPI entry point for the supplier-order calculation core."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from calculation import CalculationError, calculate_orders
from parser import FileValidationError, make_preview, parse_upload

app = FastAPI(title="TruthQuest Order Core", version="0.1.0")

# `null` supports a vanilla-JS frontend opened directly from file://; localhost is
# retained for development servers running on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["null", "http://localhost", "http://127.0.0.1"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Adjustment(BaseModel):
    quantity: int = Field(ge=0, description="Quantity confirmed by the manager")
    reason: str = Field(min_length=1, max_length=1000)


class ApprovalRequest(BaseModel):
    skus: list[str] | None = None
    comment: str | None = Field(default=None, max_length=1000)


ORDERS_CONTRACT: dict[str, Any] = {
    "orders": [
        {
            "sku": "ABC-123",
            "name": "Автоматический выключатель 16А",
            "category": "Автоматика",
            "supplier": "ООО Поставщик-1",
            "warehouse": "Склад №1",
            "recommended_qty": 120,
            "urgency": "critical",
            "lead_time_days": 14,
            "peak_season_start": "2027-06-01",
            "reasoning": {
                "base_demand": 80,
                "seasonality_factor": 1.4,
                "stockout_compensation": 15,
                "trend_growth": 0.05,
                "explanation_text": "Спрос растёт; сезонный коэффициент и период дефицита учтены в рекомендации.",
            },
            "history": [
                {"date": "2026-01-01", "qty": 12},
                {"date": "2026-02-01", "qty": 15},
            ],
            "stockout_periods": [{"start": "2026-03-10", "end": "2026-03-25"}],
        }
    ],
    "excluded_anomalies": [
        {
            "sku": "ABC-123",
            "date": "2026-04-02",
            "qty": 500,
            "client_id": "anon-9981",
            "reason": "разовая крупная продажа одному клиенту",
        }
    ],
}

_uploaded_preview: dict[str, Any] | None = None
_uploaded_data: Any | None = None
_approvals: list[dict[str, Any]] = []
_adjustments: dict[str, dict[str, Any]] = {}


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    mode: str = Form(..., description="'1c' (Формат 1С) or 'custom' (Свой файл)"),
) -> dict[str, Any]:
    """Validate an Excel/CSV file and keep only preview metadata for this session."""
    global _uploaded_data, _uploaded_preview
    try:
        frame, issues = parse_upload(await file.read(), file.filename or "upload", mode)
        _uploaded_data = frame
        _uploaded_preview = make_preview(frame, issues)
        return {"valid": True, "mode": mode, "preview": _uploaded_preview}
    except FileValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # Avoid returning internals to the browser.
        raise HTTPException(status_code=400, detail="Не удалось прочитать файл.") from exc


@app.post("/calculate")
async def calculate(warehouse: str | None = None, category: str | None = None) -> dict[str, Any]:
    """Run forecasting, stockout compensation and anomaly exclusion."""
    if _uploaded_data is None:
        raise HTTPException(status_code=409, detail="Сначала загрузите данные через POST /upload.")
    try:
        result = calculate_orders(_uploaded_data, warehouse=warehouse, category=category)
    except CalculationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ORDERS_CONTRACT.clear()
    ORDERS_CONTRACT.update(result)
    _adjustments.clear()
    return {"status": "completed", "warehouse": warehouse, "category": category, "result": ORDERS_CONTRACT}


@app.get("/orders")
async def get_orders() -> dict[str, Any]:
    """Return the current result using the unchanged section 4 contract."""
    return ORDERS_CONTRACT


@app.get("/anomalies")
async def get_anomalies() -> list[dict[str, Any]]:
    return ORDERS_CONTRACT["excluded_anomalies"]


@app.post("/orders/{sku}/adjust")
async def adjust_order(sku: str, adjustment: Adjustment) -> dict[str, Any]:
    for order in ORDERS_CONTRACT["orders"]:
        if order["sku"] == sku:
            previous_quantity = order["recommended_qty"]
            order["recommended_qty"] = adjustment.quantity
            record = {
                "status": "adjusted",
                "sku": sku,
                "previous_quantity": previous_quantity,
                "quantity": adjustment.quantity,
                "reason": adjustment.reason,
            }
            _adjustments[sku] = record
            return record
    raise HTTPException(status_code=404, detail="Артикул не найден.")


@app.post("/orders/approve")
async def approve_orders(request: ApprovalRequest) -> dict[str, Any]:
    """Group and record an export-ready order without sending it to suppliers."""
    available = {order["sku"]: order for order in ORDERS_CONTRACT["orders"]}
    selected_skus = list(dict.fromkeys(request.skus or available.keys()))
    missing_skus = [sku for sku in selected_skus if sku not in available]
    if missing_skus:
        raise HTTPException(status_code=404, detail={"message": "Артикулы не найдены.", "skus": missing_skus})
    if not selected_skus:
        raise HTTPException(status_code=409, detail="Нет позиций для утверждения.")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for sku in selected_skus:
        order = available[sku]
        grouped.setdefault(order["supplier"], []).append(
            {
                "sku": sku,
                "name": order["name"],
                "warehouse": order["warehouse"],
                "quantity": order["recommended_qty"],
                "adjustment_reason": _adjustments.get(sku, {}).get("reason"),
            }
        )

    supplier_groups = [
        {
            "supplier": supplier,
            "total_items": len(items),
            "total_quantity": sum(item["quantity"] for item in items),
            "items": items,
        }
        for supplier, items in grouped.items()
    ]
    approval = {
        "approval_id": len(_approvals) + 1,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "status": "approved_for_export",
        "sent_to_supplier": False,
        "comment": request.comment,
        "suppliers": supplier_groups,
    }
    _approvals.append(approval)
    return approval
