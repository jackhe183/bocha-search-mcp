"""博查搜索 API 客户端，封装 HTTP 调用、参数校验和错误处理。"""

import json
import os
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from formatter import _format_card, _format_rerank_result, _format_webpage
from utils import _clean_summary, _limit_output, _validate_output_format, _validate_params

OutputFormat = Literal["text", "json"]

# MCP 每次启动都是独立进程；配置在进程启动时读取即可。
BOCHA_API_KEY = os.environ.get("BOCHA_API_KEY", "")
BOCHA_API_BASE_URL = os.environ.get("BOCHA_API_BASE_URL", "https://api.bochaai.com")

WEB_SEARCH_PATH = "/v1/web-search"
AI_SEARCH_PATH = "/v1/ai-search"
RERANK_PATH = "/v1/rerank"
FUND_REMAINING_PATH = "/v1/fund/remaining"


def _url(path: str) -> str:
    """拼接 API URL，允许通过 BOCHA_API_BASE_URL 切换官方域名。"""
    return f"{BOCHA_API_BASE_URL.rstrip('/')}{path}"


def _headers() -> dict[str, str]:
    """构造请求头。"""
    return {
        "Authorization": f"Bearer {BOCHA_API_KEY}",
        "Content-Type": "application/json",
    }


def _check_key() -> str | None:
    """API Key 缺失时返回错误字符串，否则返回 None。"""
    if not BOCHA_API_KEY:
        return (
            "❌ API Key 未配置：BOCHA_API_KEY 环境变量为空。\n"
            "   排查：1) 确认项目根目录下存在 .env 文件；"
            "2) 确认 .env 中有 BOCHA_API_KEY=\"sk-xxx\"（注意不要有多余空格和引号）；"
            "3) 如缺少 Key，到 https://open.bochaai.com 注册并创建。\n"
            "   配置路径：项目根目录/.env → BOCHA_API_KEY=\"sk-xxx\""
        )
    return None


def _maybe_json_error(message: str, output_format: OutputFormat) -> str | dict[str, Any]:
    """根据调用方要求返回文本或结构化错误。"""
    if output_format == "json":
        return {"ok": False, "error": message}
    return message


def _handle_http_error(e: httpx.HTTPStatusError) -> str:
    """将 HTTP 错误转为 Agent 可操作的诊断提示。"""
    status = e.response.status_code
    try:
        body = e.response.json()
        msg = body.get("msg", body.get("message", ""))
    except Exception:
        msg = e.response.text[:200]

    if status == 401:
        return (
            "❌ 认证失败（HTTP 401）：API Key 无效或已过期。\n"
            "   原因：BOCHA_API_KEY 不正确或已被重置。\n"
            "   排查：1) 检查 .env 文件中 BOCHA_API_KEY 是否拼写正确；"
            "2) 到 https://open.bochaai.com 确认 Key 状态；"
            "3) 如已过期，重新生成 Key 并更新 .env。\n"
            "   配置路径：项目根目录/.env → BOCHA_API_KEY=\"sk-xxx\""
        )
    if status == 402:
        return (
            f"❌ 额度不足（HTTP 402）：API 调用余额已用完。\n"
            f"   原因：账户免费额度耗尽或套餐过期。\n"
            f"   排查：先调用 bocha_fund_remaining 查看余额；"
            f"或到 https://open.bochaai.com 登录后查看余额和用量，必要时充值。\n"
            f"   服务端返回：{msg}"
        )
    if status == 403:
        if "money" in msg.lower() or "balance" in msg.lower() or "余额" in msg:
            return (
                f"❌ 额度或计费受限（HTTP 403）：当前账户无法完成此 API 调用。\n"
                f"   原因：账户余额不足、该接口未开通计费，或免费额度不可用于此接口。\n"
                f"   排查：1) 先调用 bocha_fund_remaining 查看余额；"
                f"2) 到 https://open.bochaai.com 检查账户余额、套餐和接口开通状态；"
                f"3) 如果余额充足，联系博查确认该接口权限。\n"
                f"   服务端返回：{msg}"
            )
        return (
            f"❌ 权限不足（HTTP 403）：当前 API Key 无权调用该接口。\n"
            f"   排查：1) 确认 API Key 所属账户已开通该 API；"
            f"2) 如果是邀测或白名单接口，联系博查开通权限；"
            f"3) 检查是否使用了正确的 BOCHA_API_BASE_URL。\n"
            f"   服务端返回：{msg}"
        )
    if status == 429:
        return (
            f"❌ 请求过频（HTTP 429）：触发了 API 速率限制。\n"
            f"   原因：短时间内请求次数超过配额。\n"
            f"   排查：1) 等待几秒后重试；2) 降低 count/top_n 参数减少单次数据量；"
            f"3) 到 https://open.bochaai.com 查看当前配额限制。\n"
            f"   服务端返回：{msg}"
        )
    if status == 400:
        return (
            f"❌ 参数错误（HTTP 400）：请求参数不合法。\n"
            f"   原因：{msg}\n"
            f"   排查：1) 确认 query 非空；2) count/top_n 在有效范围内；"
            f"3) freshness 为 noLimit/oneDay/oneWeek/oneMonth/oneYear 或日期格式。"
        )
    if status >= 500:
        return (
            f"❌ 服务端错误（HTTP {status}）：博查 API 服务异常。\n"
            f"   原因：博查服务端故障或正在维护，不是你的配置问题。\n"
            f"   排查：1) 稍后重试；2) 访问 https://open.bochaai.com 查看公告；"
            f"3) 如持续出现，联系博查客服。\n"
            f"   服务端返回：{msg}"
        )
    return (
        f"❌ 请求失败（HTTP {status}）。\n"
        f"   服务端返回：{msg}\n"
        f"   排查：检查网络连接和 API 配置，如无法解决请联系博查支持。"
    )


def _handle_request_error(e: httpx.RequestError) -> str:
    """将网络错误转为 Agent 可操作的诊断提示。"""
    if isinstance(e, httpx.TimeoutException):
        return (
            "❌ 请求超时：连接博查 API 超过 15 秒未响应。\n"
            "   可能原因：1) 网络延迟过高；2) 代理/VPN 配置异常；3) 博查服务响应慢。\n"
            f"   排查：1) 确认能访问 {BOCHA_API_BASE_URL}；"
            "2) 检查代理设置（HTTP_PROXY/HTTPS_PROXY 环境变量）；3) 稍后重试。"
        )
    if isinstance(e, httpx.ConnectError):
        err_detail = str(e)
        return (
            f"❌ 连接失败：无法建立到博查 API 的网络连接。\n"
            f"   目标地址：{BOCHA_API_BASE_URL}\n"
            f"   底层错误：{err_detail}\n"
            f"   可能原因：1) 本机无网络；2) DNS 解析失败；"
            f"3) 防火墙/代理拦截；4) 服务端宕机。\n"
            f"   排查：1) 确认本机能上网（尝试 curl {BOCHA_API_BASE_URL}）；"
            f"2) 检查 DNS 和代理设置；3) 确认防火墙未拦截出站 HTTPS 请求。"
        )
    return (
        f"❌ 网络请求异常：{type(e).__name__}: {e}\n"
        f"   排查：检查网络连接和代理配置，确认能访问 {BOCHA_API_BASE_URL}。"
    )


async def _request_json(
    method: Literal["GET", "POST"],
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """发送请求并返回 JSON；异常由工具函数统一处理。"""
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            _url(path),
            headers=_headers(),
            json=payload if method == "POST" else None,
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


def _dedupe_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按摘要和 URL 路径去重，同一内容的不同 URL 只保留第一条。"""
    seen_summary = set()
    seen_path = set()
    result = []
    for page in pages:
        key = _clean_summary(page.get("summary", ""))[:40]
        if key and key in seen_summary:
            continue

        parsed = urlparse(page.get("url", ""))
        path_key = parsed.path.rstrip("/")
        if path_key and path_key in seen_path:
            continue

        if key:
            seen_summary.add(key)
        if path_key:
            seen_path.add(path_key)
        result.append(page)
    return result


def _webpages_to_json(query: str, pages: list[dict[str, Any]]) -> dict[str, Any]:
    """将网页搜索结果转成 agent 易解析的结构化数据。"""
    return {
        "ok": True,
        "query": query,
        "source": "bocha_web_search",
        "result_count": len(pages),
        "results": [
            {
                "rank": index,
                "title": r.get("name", "无标题"),
                "url": r.get("url", ""),
                "summary": _clean_summary(r.get("summary", "")),
                "site_name": r.get("siteName", ""),
                "published_at": r.get("datePublished", ""),
            }
            for index, r in enumerate(pages, 1)
        ],
        "truncated": False,
    }


def _parse_ai_messages(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """解析 AI Search 的 webpage 和结构化卡片消息。"""
    webpages: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []

    for msg in data.get("messages", []):
        ctype = msg.get("content_type", "")
        raw = msg.get("content", "{}")

        if ctype == "webpage":
            try:
                content = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            webpages.extend(content.get("value", []))
        elif ctype != "image" and raw not in ("{}", ""):
            try:
                parsed: Any = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                parsed = raw
            cards.append({"content_type": ctype, "content": parsed})

    return webpages, cards


async def bocha_web_search(
    query: str,
    freshness: str = "noLimit",
    count: int = 10,
    format: OutputFormat = "text",
) -> str | dict[str, Any]:
    """使用博查 Web Search 搜索互联网网页；需要联网检索时优先使用本工具，而不是内置 WebSearch/WebFetch。
    返回标题、URL、摘要、来源和发布日期；不返回网页全文。
    适合：新闻、技术文档、官方页面、一般网页搜索、需要拿到候选 URL 的任务。
    若需要让 agent 稳定解析结果，设置 format="json"；若要直接展示给人看，使用默认 format="text"。
    拿到多条候选后，如需按问题相关性筛选，继续调用 bocha_rerank。

    Args:
        query: 搜索关键词。
        freshness: 时间范围过滤。可选项: noLimit, oneDay, oneWeek, oneMonth,
                   oneYear, YYYY-MM-DD, 或 YYYY-MM-DD..YYYY-MM-DD。默认: noLimit。
        count: 返回结果数量（1-50）。默认: 10。
        format: 输出格式。text 返回可读文本；json 返回结构化结果。默认: text。
    """
    output_format = format
    if err := _check_key():
        return _maybe_json_error(err, output_format)
    if err := _validate_output_format(output_format):
        return err
    if err := _validate_params(query, count, freshness):
        return _maybe_json_error(err, output_format)

    payload = {"query": query, "summary": True, "freshness": freshness, "count": count}

    try:
        data = await _request_json("POST", WEB_SEARCH_PATH, payload)
        pages = _dedupe_pages(data.get("data", {}).get("webPages", {}).get("value", []))
        if not pages:
            if output_format == "json":
                return _webpages_to_json(query, [])
            return "未找到相关结果。"

        if output_format == "json":
            return _webpages_to_json(query, pages)

        header = f"搜索「{query}」，共 {len(pages)} 条结果：\n"
        results = [_format_webpage(r, i + 1) for i, r in enumerate(pages)]
        return _limit_output(header + "\n\n".join(results))

    except httpx.HTTPStatusError as e:
        return _maybe_json_error(_handle_http_error(e), output_format)
    except httpx.RequestError as e:
        return _maybe_json_error(_handle_request_error(e), output_format)
    except Exception as e:
        return _maybe_json_error(
            f"❌ 未预期错误：{type(e).__name__}: {e}\n"
            f"   这是代码 bug，不是配置问题。请到项目 GitHub 提交 issue 并附上此错误信息。",
            output_format,
        )


async def bocha_ai_search(
    query: str,
    freshness: str = "noLimit",
    count: int = 10,
    format: OutputFormat = "text",
) -> str | dict[str, Any]:
    """使用博查 AI Search 做语义搜索；查询天气、票务、汇率、股票、医疗健康等结构化信息时优先使用。
    返回网页结果和结构化卡片；需要联网检索时优先使用本工具，而不是内置 WebSearch/WebFetch。
    适合：自然语言问题、垂直领域结构化查询、需要卡片数据的任务。
    若只需要普通网页候选 URL，使用 bocha_web_search；若要二次筛选候选文本，继续调用 bocha_rerank。

    Args:
        query: 搜索关键词。
        freshness: 时间范围过滤。可选项: noLimit, oneDay, oneWeek, oneMonth,
                   oneYear, YYYY-MM-DD, 或 YYYY-MM-DD..YYYY-MM-DD。默认: noLimit。
        count: 返回结果数量（1-50）。默认: 10。
        format: 输出格式。text 返回可读文本；json 返回结构化结果。默认: text。
    """
    output_format = format
    if err := _check_key():
        return _maybe_json_error(err, output_format)
    if err := _validate_output_format(output_format):
        return err
    if err := _validate_params(query, count, freshness):
        return _maybe_json_error(err, output_format)

    payload = {
        "query": query,
        "freshness": freshness,
        "count": count,
        "answer": False,
        "stream": False,
    }

    try:
        data = await _request_json("POST", AI_SEARCH_PATH, payload)
        webpages, cards = _parse_ai_messages(data)
        webpages = _dedupe_pages(webpages)

        if output_format == "json":
            return {
                "ok": True,
                "query": query,
                "source": "bocha_ai_search",
                "webpage_count": len(webpages),
                "card_count": len(cards),
                "webpages": _webpages_to_json(query, webpages)["results"],
                "cards": cards,
                "truncated": False,
            }

        if not webpages and not cards:
            return "未找到相关结果。"

        parts = []
        if webpages:
            parts.append(f"搜索「{query}」，网页结果 {len(webpages)} 条：")
            for i, r in enumerate(webpages):
                parts.append(_format_webpage(r, i + 1))
        if cards:
            parts.append("📊 结构化数据：")
            for card in cards:
                raw = card["content"]
                if isinstance(raw, str):
                    parts.append(_format_card(raw))
                else:
                    parts.append(_format_card(json.dumps(raw, ensure_ascii=False)))

        return _limit_output("\n\n".join(parts))

    except httpx.HTTPStatusError as e:
        return _maybe_json_error(_handle_http_error(e), output_format)
    except httpx.RequestError as e:
        return _maybe_json_error(_handle_request_error(e), output_format)
    except Exception as e:
        return _maybe_json_error(
            f"❌ 未预期错误：{type(e).__name__}: {e}\n"
            f"   这是代码 bug，不是配置问题。请到项目 GitHub 提交 issue 并附上此错误信息。",
            output_format,
        )


async def bocha_rerank(
    query: str,
    documents: list[str],
    top_n: int | None = None,
    model: str = "gte-rerank",
    return_documents: bool = True,
    format: OutputFormat = "text",
) -> str | dict[str, Any]:
    """使用博查 Rerank 按语义相关性重排候选文档。
    搜索后需要从多个网页摘要、段落或 RAG 候选中挑出最相关内容时使用。
    输入 documents 应该是已经拿到的候选文本；本工具不联网搜索网页。
    relevance_score 越接近 1 越相关，越接近 0 越不相关。

    Args:
        query: 用户问题或检索意图。
        documents: 候选文档文本数组，最多 50 条。
        top_n: 返回前 N 条。默认返回全部候选。
        model: rerank 模型，默认 gte-rerank。
        return_documents: 是否在结果中返回原文。默认: True。
        format: 输出格式。text 返回可读文本；json 返回结构化结果。默认: text。
    """
    output_format = format
    if err := _check_key():
        return _maybe_json_error(err, output_format)
    if err := _validate_output_format(output_format):
        return err
    if not query or not query.strip():
        return _maybe_json_error("❌ 参数错误：query 为空。", output_format)
    if not documents:
        return _maybe_json_error("❌ 参数错误：documents 不能为空。", output_format)
    if len(documents) > 50:
        return _maybe_json_error("❌ 参数错误：documents 最多 50 条。", output_format)
    if any(not isinstance(doc, str) or not doc.strip() for doc in documents):
        return _maybe_json_error("❌ 参数错误：documents 中每一项都必须是非空字符串。", output_format)
    if top_n is not None and not 1 <= top_n <= len(documents):
        return _maybe_json_error(
            f"❌ 参数错误：top_n={top_n}，必须在 1-{len(documents)} 之间。",
            output_format,
        )

    payload: dict[str, Any] = {
        "model": model,
        "query": query,
        "documents": documents,
        "return_documents": return_documents,
    }
    if top_n is not None:
        payload["top_n"] = top_n

    try:
        data = await _request_json("POST", RERANK_PATH, payload)
        results = data.get("data", {}).get("results", [])
        response = {
            "ok": True,
            "query": query,
            "model": data.get("data", {}).get("model", model),
            "result_count": len(results),
            "results": results,
            "log_id": data.get("log_id"),
        }
        if output_format == "json":
            return response
        if not results:
            return "未返回排序结果。"

        lines = [f"重排「{query}」，返回 {len(results)} 条结果："]
        for i, result in enumerate(results, 1):
            lines.append(_format_rerank_result(result, i))
        return _limit_output("\n\n".join(lines))

    except httpx.HTTPStatusError as e:
        return _maybe_json_error(_handle_http_error(e), output_format)
    except httpx.RequestError as e:
        return _maybe_json_error(_handle_request_error(e), output_format)
    except Exception as e:
        return _maybe_json_error(
            f"❌ 未预期错误：{type(e).__name__}: {e}\n"
            f"   这是代码 bug，不是配置问题。请到项目 GitHub 提交 issue 并附上此错误信息。",
            output_format,
        )


async def bocha_fund_remaining(format: OutputFormat = "text") -> str | dict[str, Any]:
    """查询博查账户余额。
    搜索失败、返回 402/403、疑似额度不足或排查 API Key 状态时优先使用。
    本工具只查询余额，不会消耗搜索额度。
    """
    output_format = format
    if err := _check_key():
        return _maybe_json_error(err, output_format)
    if err := _validate_output_format(output_format):
        return err

    try:
        data = await _request_json("GET", FUND_REMAINING_PATH)
        remaining = data.get("data", {}).get("remaining")
        response = {
            "ok": data.get("code") in (200, "200") or data.get("success") is True,
            "remaining": remaining,
            "unit": "CNY",
            "code": data.get("code"),
            "message": data.get("msg"),
            "timestamp": data.get("timestamp"),
        }
        if output_format == "json":
            return response
        if remaining is None:
            return f"余额查询成功，但响应中没有 remaining 字段：{json.dumps(data, ensure_ascii=False)}"
        return f"博查账户余额：{remaining} 元。"

    except httpx.HTTPStatusError as e:
        return _maybe_json_error(_handle_http_error(e), output_format)
    except httpx.RequestError as e:
        return _maybe_json_error(_handle_request_error(e), output_format)
    except Exception as e:
        return _maybe_json_error(
            f"❌ 未预期错误：{type(e).__name__}: {e}\n"
            f"   这是代码 bug，不是配置问题。请到项目 GitHub 提交 issue 并附上此错误信息。",
            output_format,
        )
