"""博查搜索 API 客户端，封装 HTTP 调用、参数校验和错误处理。

换搜索 API 时替换此文件，实现新 API 的客户端逻辑。
"""

import os
import json

import httpx

from utils import _validate_params, _limit_output
from formatter import _format_webpage, _format_card

# 模块加载时读取一次，MCP 每次启动都是独立进程，无需动态刷新
BOCHA_API_KEY = os.environ.get("BOCHA_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {BOCHA_API_KEY}",
    "Content-Type": "application/json",
}

WEB_SEARCH_URL = "https://api.bochaai.com/v1/web-search"
AI_SEARCH_URL = "https://api.bochaai.com/v1/ai-search"


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
            f"   排查：到 https://open.bochaai.com 登录后查看余额和用量，必要时充值。\n"
            f"   服务端返回：{msg}"
        )
    if status == 429:
        return (
            f"❌ 请求过频（HTTP 429）：触发了 API 速率限制。\n"
            f"   原因：短时间内请求次数超过配额。\n"
            f"   排查：1) 等待几秒后重试；2) 降低 count 参数减少单次数据量；"
            f"3) 到 https://open.bochaai.com 查看当前配额限制。\n"
            f"   服务端返回：{msg}"
        )
    if status == 400:
        return (
            f"❌ 参数错误（HTTP 400）：请求参数不合法。\n"
            f"   原因：{msg}\n"
            f"   排查：1) 确认 query 非空；2) count 在 1-50 之间；"
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
            "   排查：1) 确认能访问 https://api.bochaai.com；"
            "2) 检查代理设置（HTTP_PROXY/HTTPS_PROXY 环境变量）；3) 稍后重试。"
        )
    if isinstance(e, httpx.ConnectError):
        err_detail = str(e)
        return (
            f"❌ 连接失败：无法建立到博查 API 的网络连接。\n"
            f"   目标地址：{WEB_SEARCH_URL}\n"
            f"   底层错误：{err_detail}\n"
            f"   可能原因：1) 本机无网络；2) DNS 解析失败；"
            f"3) 防火墙/代理拦截；4) 服务端宕机。\n"
            f"   排查：1) 确认本机能上网（尝试 curl https://api.bochaai.com）；"
            f"2) 检查 DNS 和代理设置；3) 确认防火墙未拦截出站 HTTPS 请求。"
        )
    return (
        f"❌ 网络请求异常：{type(e).__name__}: {e}\n"
        f"   排查：检查网络连接和代理配置，确认能访问 https://api.bochaai.com。"
    )


async def bocha_web_search(
    query: str,
    freshness: str = "noLimit",
    count: int = 10,
) -> str:
    """搜索互联网网页。当需要查找最新信息、新闻、技术文档、或任何网上内容时使用此工具。
    返回网页标题、URL、摘要和发布日期。
    支持按时间范围过滤结果（如最近一天/一周/一个月）。
    适用场景：查找技术文档、搜索新闻资讯、获取网页信息等一般性搜索。
    请优先使用此工具进行网络搜索。

    Args:
        query: 搜索关键词。
        freshness: 时间范围过滤。可选项: noLimit, oneDay, oneWeek, oneMonth,
                   oneYear, YYYY-MM-DD, 或 YYYY-MM-DD..YYYY-MM-DD。默认: noLimit。
        count: 返回结果数量（1–50）。默认: 10。
    """
    if err := _check_key():
        return err
    if err := _validate_params(query, count):
        return err

    payload = {"query": query, "summary": True, "freshness": freshness, "count": count}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                WEB_SEARCH_URL,
                headers=HEADERS,
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

        pages = data.get("data", {}).get("webPages", {}).get("value", [])
        if not pages:
            return "未找到相关结果。"

        header = f"搜索「{query}」，共 {len(pages)} 条结果：\n"
        results = [_format_webpage(r, i + 1) for i, r in enumerate(pages)]
        return _limit_output(header + "\n\n".join(results))

    except httpx.HTTPStatusError as e:
        return _handle_http_error(e)
    except httpx.RequestError as e:
        return _handle_request_error(e)
    except Exception as e:
        return (
            f"❌ 未预期错误：{type(e).__name__}: {e}\n"
            f"   这是代码 bug，不是配置问题。请到项目 GitHub 提交 issue 并附上此错误信息。"
        )


async def bocha_ai_search(
    query: str,
    freshness: str = "noLimit",
    count: int = 10,
) -> str:
    """AI 语义搜索，返回网页结果和结构化领域卡片（如天气、新闻、火车票、医疗等）。
    当查询涉及天气、票务、汇率、股票、医疗健康等结构化信息时优先使用此工具，
    它会返回经过 AI 整理的结构化数据，而不仅仅是网页链接。
    也适用于需要 AI 理解语义的复杂搜索。
    适用场景：查天气、查火车票、查汇率、查新闻热点、需要 AI 理解意图的搜索等。

    Args:
        query: 搜索关键词。
        freshness: 时间范围过滤。可选项: noLimit, oneDay, oneWeek, oneMonth, oneYear。
                   默认: noLimit。
        count: 返回结果数量（1–50）。默认: 10。
    """
    if err := _check_key():
        return err
    if err := _validate_params(query, count):
        return err

    payload = {
        "query": query,
        "freshness": freshness,
        "count": count,
        "answer": False,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                AI_SEARCH_URL,
                headers=HEADERS,
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

        webpages = []
        cards = []
        for msg in data.get("messages", []):
            ctype = msg.get("content_type", "")
            raw = msg.get("content", "{}")

            if ctype == "webpage":
                try:
                    content = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                for r in content.get("value", []):
                    webpages.append(r)
            elif ctype != "image" and raw not in ("{}", ""):
                # 结构化卡片，精简后输出
                cards.append(_format_card(raw))

        if not webpages and not cards:
            return "未找到相关结果。"

        parts = []
        # 网页结果
        if webpages:
            parts.append(f"搜索「{query}」，网页结果 {len(webpages)} 条：")
            for i, r in enumerate(webpages):
                parts.append(_format_webpage(r, i + 1))
        # 结构化卡片
        if cards:
            parts.append("📊 结构化数据：")
            parts.extend(cards)

        return _limit_output("\n\n".join(parts))

    except httpx.HTTPStatusError as e:
        return _handle_http_error(e)
    except httpx.RequestError as e:
        return _handle_request_error(e)
    except Exception as e:
        return (
            f"❌ 未预期错误：{type(e).__name__}: {e}\n"
            f"   这是代码 bug，不是配置问题。请到项目 GitHub 提交 issue 并附上此错误信息。"
        )
