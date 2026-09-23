import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import ai_service
from main import app


class AIServiceTests(unittest.TestCase):
    @patch("ai_service._create_response")
    def test_market_trends_extracts_unique_annotation_urls(self, create_response) -> None:
        create_response.return_value = SimpleNamespace(
            output_text="Спрос растёт умеренно.",
            output=[
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "annotations": [
                                {"type": "url_citation", "url": "https://example.kz/report"},
                                {"type": "url_citation", "url": "https://example.kz/report"},
                                {
                                    "type": "url_citation",
                                    "url_citation": {"url": "https://industry.kz/news"},
                                },
                            ],
                        }
                    ],
                }
            ],
        )

        result = ai_service.generate_market_trends("Автоматика")

        self.assertEqual(result["summary"], "Спрос растёт умеренно.")
        self.assertEqual(
            result["sources"],
            ["https://example.kz/report", "https://industry.kz/news"],
        )
        kwargs = create_response.call_args.kwargs
        self.assertEqual(kwargs["tools"], [{"type": "web_search"}])
        self.assertEqual(kwargs["reasoning"], {"effort": "medium"})

    @patch("ai_service._create_response")
    def test_market_alternatives_uses_strict_schema(self, create_response) -> None:
        alternative = {
            "supplier": "ТОО Поставщик",
            "price": "1 500 ₸",
            "moq": "10 шт.",
            "lead_time": "7 дней",
            "source_url": "https://supplier.kz/item",
        }
        create_response.return_value = SimpleNamespace(
            output_text=json.dumps({"alternatives": [alternative]}, ensure_ascii=False)
        )

        result = ai_service.find_market_alternatives("ABC-123", "Выключатель", "Автоматика")

        self.assertEqual(result, {"alternatives": [alternative]})
        response_format = create_response.call_args.kwargs["text"]["format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["strict"])
        self.assertEqual(response_format["schema"]["properties"]["alternatives"]["maxItems"], 3)

    def test_missing_key_is_a_readable_502(self) -> None:
        client = TestClient(app)
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            trends = client.post("/ai/market-trends", json={"category": "Автоматика"})
            alternatives = client.post(
                "/ai/market-alternatives",
                json={"sku": "ABC-123", "name": "Выключатель", "category": "Автоматика"},
            )

        self.assertEqual(trends.status_code, 502)
        self.assertIn("OPENAI_API_KEY", trends.json()["detail"])
        self.assertEqual(alternatives.status_code, 502)
        self.assertIn("OPENAI_API_KEY", alternatives.json()["detail"])


if __name__ == "__main__":
    unittest.main()
