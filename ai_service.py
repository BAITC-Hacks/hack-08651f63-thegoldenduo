"""OpenAI-powered market research helpers used by the FastAPI proxy."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import APIError, APITimeoutError, OpenAI


DEFAULT_MODEL = "gpt-5.6-terra"


class AIServiceError(RuntimeError):
    """A safe, user-facing failure from the external AI service."""


def _client() -> OpenAI:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise AIServiceError("Переменная окружения OPENAI_API_KEY не настроена.")
    return OpenAI(api_key=api_key, timeout=45.0, max_retries=1)


def _model() -> str:
    """Allow a hackathon account to select another available Responses model."""
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _source_urls(response: Any) -> list[str]:
    """Extract and de-duplicate web-search URL citations from Responses output."""
    urls: list[str] = []
    for output_item in _value(response, "output", []) or []:
        if _value(output_item, "type") != "message":
            continue
        for content_item in _value(output_item, "content", []) or []:
            for annotation in _value(content_item, "annotations", []) or []:
                url = _value(annotation, "url")
                if not url:
                    url = _value(_value(annotation, "url_citation", {}), "url")
                if isinstance(url, str) and url and url not in urls:
                    urls.append(url)
    return urls


def _create_response(**kwargs: Any) -> Any:
    try:
        return _client().responses.create(**kwargs)
    except APITimeoutError as exc:
        print("REAL AI ERROR (timeout):", repr(exc))
        raise AIServiceError("OpenAI API не ответил вовремя. Повторите запрос позже.") from exc
    except APIError as exc:
        print("REAL AI ERROR (api):", repr(exc))
        raise AIServiceError(
            "OpenAI API вернул ошибку. Проверьте ключ, доступ к модели и лимиты аккаунта."
        ) from exc
    except Exception as exc:
        print("REAL AI ERROR (unexpected):", repr(exc))
        raise AIServiceError("Непредвиденная ошибка при обращении к OpenAI API.") from exc


def generate_market_trends(category: str) -> dict[str, Any]:
    """Summarize recent Kazakhstan demand trends and return cited sources."""
    response = _create_response(
        model=_model(),
        reasoning={"effort": "medium"},
        tools=[{"type": "web_search"}],
        tool_choice="required",
        input=(
            "Кратко опиши текущие тренды спроса на рынке Казахстана в категории "
            f"{category} за последние месяцы: рост/падение спроса, сезонные факторы, "
            "что говорят отраслевые источники. Ответ на русском, 3-5 предложений."
        ),
    )
    summary = (response.output_text or "").strip()
    if not summary:
        raise AIServiceError("OpenAI API вернул пустой ответ.")
    return {"summary": summary, "sources": _source_urls(response)}


ALTERNATIVES_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "market_alternatives",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "alternatives": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "supplier": {"type": "string"},
                        "price": {"type": "string"},
                        "moq": {"type": "string"},
                        "lead_time": {"type": "string"},
                        "source_url": {"type": "string"},
                    },
                    "required": ["supplier", "price", "moq", "lead_time", "source_url"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["alternatives"],
        "additionalProperties": False,
    },
}


def find_market_alternatives(sku: str, name: str, category: str) -> dict[str, Any]:
    """Find up to three Kazakhstan wholesale alternatives as strict JSON."""
    response = _create_response(
        model=_model(),
        reasoning={"effort": "medium"},
        tools=[{"type": "web_search"}],
        tool_choice="required",
        text={"format": ALTERNATIVES_FORMAT},
        input=(
            f"Найди 2-3 оптовых предложения на товар '{name}' (категория {category}) "
            f"от поставщиков в Казахстане. Артикул/SKU: {sku}. "
            "Верни структурированные данные. Указывай только предложения, для которых "
            "можно привести URL источника; неизвестные цену, MOQ или срок поставки помечай "
            "строкой 'не указано'."
        ),
    )
    try:
        result = json.loads(response.output_text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AIServiceError("OpenAI API вернул некорректный структурированный ответ.") from exc

    alternatives = result.get("alternatives") if isinstance(result, dict) else None
    if not isinstance(alternatives, list) or len(alternatives) > 3:
        raise AIServiceError("OpenAI API вернул ответ, не соответствующий схеме альтернатив.")
    return {"alternatives": alternatives}
