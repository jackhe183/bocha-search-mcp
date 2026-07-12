import unittest
from unittest.mock import AsyncMock, patch

import httpx

import api


class BochaApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.key_patch = patch.object(api, "BOCHA_API_KEY", "test-key")
        self.key_patch.start()

    async def asyncTearDown(self):
        self.key_patch.stop()

    async def test_web_search_json_returns_structured_results(self):
        mock_request = AsyncMock(
            return_value={
                "data": {
                    "webPages": {
                        "value": [
                            {
                                "name": "FastMCP docs",
                                "url": "https://example.com/fastmcp",
                                "summary": "How to register tools.",
                                "siteName": "Example",
                                "datePublished": "2026-01-01",
                            }
                        ]
                    }
                }
            }
        )

        with patch.object(api, "_request_json", mock_request):
            result = await api.bocha_web_search("FastMCP", count=1, format="json")

        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "bocha_web_search")
        self.assertEqual(result["result_count"], 1)
        self.assertEqual(result["results"][0]["rank"], 1)
        self.assertEqual(result["results"][0]["title"], "FastMCP docs")
        self.assertEqual(result["results"][0]["url"], "https://example.com/fastmcp")
        mock_request.assert_awaited_once_with(
            "POST",
            api.WEB_SEARCH_PATH,
            {"query": "FastMCP", "summary": True, "freshness": "noLimit", "count": 1},
        )

    async def test_web_search_text_keeps_readable_output(self):
        mock_request = AsyncMock(
            return_value={
                "data": {
                    "webPages": {
                        "value": [
                            {
                                "name": "FastMCP docs",
                                "url": "https://example.com/fastmcp",
                                "summary": "How to register tools.",
                                "siteName": "Example",
                                "datePublished": "2026-01-01",
                            }
                        ]
                    }
                }
            }
        )

        with patch.object(api, "_request_json", mock_request):
            result = await api.bocha_web_search("FastMCP", count=1)

        self.assertIn("搜索「FastMCP」", result)
        self.assertIn("URL: https://example.com/fastmcp", result)

    async def test_ai_search_json_splits_webpages_and_cards(self):
        mock_request = AsyncMock(
            return_value={
                "messages": [
                    {
                        "content_type": "webpage",
                        "content": '{"value":[{"name":"Weather","url":"https://example.com","summary":"rain"}]}',
                    },
                    {
                        "content_type": "weather",
                        "content": '{"location":"北京","day":[]}',
                    },
                    {
                        "content_type": "image",
                        "content": '{"ignored": true}',
                    },
                ]
            }
        )

        with patch.object(api, "_request_json", mock_request):
            result = await api.bocha_ai_search("北京天气", count=3, format="json")

        self.assertTrue(result["ok"])
        self.assertEqual(result["webpage_count"], 1)
        self.assertEqual(result["card_count"], 1)
        self.assertEqual(result["webpages"][0]["title"], "Weather")
        self.assertEqual(result["cards"][0]["content_type"], "weather")
        self.assertEqual(result["cards"][0]["content"]["location"], "北京")

    async def test_rerank_posts_expected_payload_and_formats_text(self):
        mock_request = AsyncMock(
            return_value={
                "log_id": "abc",
                "data": {
                    "model": "gte-rerank",
                    "results": [
                        {
                            "index": 1,
                            "document": {"text": "FastMCP add_tool example"},
                            "relevance_score": 0.9,
                        }
                    ],
                },
            }
        )

        with patch.object(api, "_request_json", mock_request):
            result = await api.bocha_rerank(
                "FastMCP 注册工具",
                ["unrelated", "FastMCP add_tool example"],
                top_n=1,
            )

        self.assertIn("重排「FastMCP 注册工具」", result)
        self.assertIn("相关性: 0.9", result)
        mock_request.assert_awaited_once_with(
            "POST",
            api.RERANK_PATH,
            {
                "model": "gte-rerank",
                "query": "FastMCP 注册工具",
                "documents": ["unrelated", "FastMCP add_tool example"],
                "return_documents": True,
                "top_n": 1,
            },
        )

    async def test_rerank_json_returns_raw_results(self):
        mock_request = AsyncMock(
            return_value={
                "log_id": "abc",
                "data": {
                    "model": "gte-rerank",
                    "results": [{"index": 0, "relevance_score": 0.8}],
                },
            }
        )

        with patch.object(api, "_request_json", mock_request):
            result = await api.bocha_rerank("query", ["doc"], format="json")

        self.assertTrue(result["ok"])
        self.assertEqual(result["log_id"], "abc")
        self.assertEqual(result["result_count"], 1)
        self.assertEqual(result["results"][0]["index"], 0)

    async def test_fund_remaining_supports_json_and_text(self):
        mock_request = AsyncMock(
            return_value={
                "success": True,
                "code": "200",
                "msg": "success",
                "data": {"remaining": 12.34},
                "timestamp": 1739845090213,
            }
        )

        with patch.object(api, "_request_json", mock_request):
            json_result = await api.bocha_fund_remaining(format="json")
            text_result = await api.bocha_fund_remaining()

        self.assertTrue(json_result["ok"])
        self.assertEqual(json_result["remaining"], 12.34)
        self.assertIn("12.34 元", text_result)
        self.assertEqual(mock_request.await_count, 2)
        mock_request.assert_any_await("GET", api.FUND_REMAINING_PATH)

    async def test_invalid_freshness_is_rejected_before_http(self):
        mock_request = AsyncMock()

        with patch.object(api, "_request_json", mock_request):
            result = await api.bocha_web_search("query", freshness="yesterday", format="json")

        self.assertFalse(result["ok"])
        self.assertIn("freshness", result["error"])
        mock_request.assert_not_called()

    async def test_http_402_suggests_fund_remaining(self):
        request = httpx.Request("POST", "https://api.bochaai.com/v1/web-search")
        response = httpx.Response(402, request=request, json={"msg": "insufficient balance"})
        mock_request = AsyncMock(side_effect=httpx.HTTPStatusError("payment", request=request, response=response))

        with patch.object(api, "_request_json", mock_request):
            result = await api.bocha_web_search("query")

        self.assertIn("额度不足", result)
        self.assertIn("bocha_fund_remaining", result)

    async def test_http_403_money_message_suggests_balance_and_permission_checks(self):
        request = httpx.Request("POST", "https://api.bochaai.com/v1/rerank")
        response = httpx.Response(403, request=request, json={"msg": "You do not have enough money"})
        mock_request = AsyncMock(side_effect=httpx.HTTPStatusError("forbidden", request=request, response=response))

        with patch.object(api, "_request_json", mock_request):
            result = await api.bocha_rerank("query", ["doc"])

        self.assertIn("额度或计费受限", result)
        self.assertIn("bocha_fund_remaining", result)
        self.assertIn("接口权限", result)

    async def test_missing_key_returns_structured_error_for_json(self):
        with patch.object(api, "BOCHA_API_KEY", ""):
            result = await api.bocha_web_search("query", format="json")

        self.assertFalse(result["ok"])
        self.assertIn("API Key 未配置", result["error"])


if __name__ == "__main__":
    unittest.main()
