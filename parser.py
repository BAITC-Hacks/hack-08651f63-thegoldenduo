"""Parsing and lightweight validation for supplier-order source files."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "sku": "артикул",
    "date": "дата",
    "quantity": "количество",
    "price": "цена",
    "client_id": "обезличенный клиент",
    "warehouse": "склад",
    "stock": "остаток",
}

# Both parsers produce these canonical columns before data enters the calculation core.
COMMON_ALIASES = {
    "sku": {"артикул", "sku", "код товара", "номенклатура"},
    "date": {"дата", "дата продажи", "date"},
    "quantity": {"количество", "qty", "quantity", "кол-во"},
    "price": {"цена", "price", "стоимость"},
    "client_id": {"обезличенный клиент", "client_id", "клиент", "контрагент"},
    "warehouse": {"склад", "warehouse"},
    "stock": {"остаток", "stock", "остаток на складе"},
    "in_transit": {"товары в пути", "в пути", "in_transit", "goods_in_transit"},
    "name": {"наименование", "название", "name"},
    "category": {"категория", "category"},
    "supplier": {"поставщик", "supplier"},
    "lead_time_days": {
        "срок поставки",
        "срок поставки, дней",
        "срок поставки (дни)",
        "lead_time_days",
        "lead time days",
    },
}


class FileValidationError(ValueError):
    """Raised when an uploaded file cannot be used by the calculation pipeline."""


def _normalise_column(name: object) -> str:
    return " ".join(str(name).strip().lower().split())


def _read_table(content: bytes, filename: str) -> pd.DataFrame:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    source = BytesIO(content)
    if suffix in {"xlsx", "xls"}:
        return pd.read_excel(source)
    if suffix == "csv":
        try:
            return pd.read_csv(source, encoding="utf-8-sig")
        except UnicodeDecodeError:
            source.seek(0)
            return pd.read_csv(source, encoding="cp1251")
    raise FileValidationError("Поддерживаются только файлы CSV, XLSX и XLS.")


def _canonicalise_columns(frame: pd.DataFrame, aliases: dict[str, set[str]]) -> pd.DataFrame:
    aliases_to_field = {
        _normalise_column(alias): field
        for field, field_aliases in aliases.items()
        for alias in field_aliases
    }
    rename_map = {
        column: aliases_to_field[_normalise_column(column)]
        for column in frame.columns
        if _normalise_column(column) in aliases_to_field
    }
    return frame.rename(columns=rename_map)


def _validate(frame: pd.DataFrame) -> list[str]:
    missing = [label for field, label in REQUIRED_COLUMNS.items() if field not in frame.columns]
    if missing:
        raise FileValidationError("Не найдены обязательные колонки: " + ", ".join(missing))

    issues: list[str] = []
    if frame.empty:
        issues.append("Файл не содержит строк данных.")
    null_columns = [field for field in REQUIRED_COLUMNS if frame[field].isna().any()]
    if null_columns:
        issues.append("Есть пропуски в колонках: " + ", ".join(null_columns))
    duplicate_count = int(frame.duplicated().sum())
    if duplicate_count:
        issues.append(f"Найдены дублирующиеся строки: {duplicate_count}.")
    return issues


def parse_1c(content: bytes, filename: str) -> tuple[pd.DataFrame, list[str]]:
    """Parse a 1C export. The alias map is intentionally isolated for future 1C details."""
    frame = _canonicalise_columns(_read_table(content, filename), COMMON_ALIASES)
    return frame, _validate(frame)


def parse_custom_file(content: bytes, filename: str) -> tuple[pd.DataFrame, list[str]]:
    """Parse the team's simplified CSV/XLSX template."""
    frame = _canonicalise_columns(_read_table(content, filename), COMMON_ALIASES)
    return frame, _validate(frame)


def parse_upload(content: bytes, filename: str, mode: str) -> tuple[pd.DataFrame, list[str]]:
    """Select a parser and return canonical data plus non-blocking validation issues."""
    normalised_mode = mode.strip().lower()
    if normalised_mode in {"1c", "формат 1с", "формат 1c"}:
        return parse_1c(content, filename)
    if normalised_mode in {"custom", "свой файл", "свой файл (быстрый анализ)"}:
        return parse_custom_file(content, filename)
    raise FileValidationError("Неизвестный режим. Используйте '1c' или 'custom'.")


def make_preview(frame: pd.DataFrame, issues: list[str]) -> dict[str, Any]:
    """Return a JSON-safe upload preview without exposing raw client data."""
    dates = pd.to_datetime(frame["date"], errors="coerce") if "date" in frame else pd.Series(dtype="datetime64[ns]")
    valid_dates = dates.dropna()
    return {
        "rows": int(len(frame)),
        "date_range": {
            "start": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
            "end": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        },
        "columns": list(frame.columns),
        "issues": issues,
    }
