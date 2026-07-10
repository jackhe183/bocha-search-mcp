import os
import json
import re

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 加载 .env 文件，必须在读取环境变量之前调用
load_dotenv()

server = FastMCP("bocha-search-mcp")

# 模块加载时读取一次，MCP 每次启动都是独立进程，无需动态刷新
BOCHA_API_KEY = os.environ.get("BOCHA_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {BOCHA_API_KEY}",
    "Content-Type": "application/json",
}

# 摘要最大长度（字符），超长截断并加省略号
MAX_SUMMARY_LEN = 300


def _check_key() -> str | None:
    """API Key 缺失时返回错误字符串，否则返回 None。"""
    if not BOCHA_API_KEY:
        return "Error: BOCHA_API_KEY 未配置，请在 .env 文件中设置。"
    return None


def _truncate(text: str, max_len: int = MAX_SUMMARY_LEN) -> str:
    """截断过长文本，在句号/问号/叹号处断句，超长则硬截断加省略号。"""
    if not text or len(text) <= max_len:
        return text
    # 优先在句末标点处断句
    cut = text[:max_len]
    for sep in ("。", "！", "？", ".", "!", "?", "；", ";"):
        idx = cut.rfind(sep)
        if idx > max_len // 2:
            return text[: idx + 1] + "..."
    # 无合适断句点则硬截断
    return cut + "..."


def _format_webpage(r: dict, index: int) -> str:
    """格式化单条网页搜索结果。"""
    return (
        f"[{index}] {r['name']}\n"
        f"    URL: {r['url']}\n"
        f"    摘要: {_truncate(r.get('summary', ''))}\n"
        f"    来源: {r.get('siteName', 'N/A')} | 发布: {r.get('datePublished', 'N/A')}"
    )


def _format_card(raw: str) -> str:
    """格式化结构化卡片，精简输出以节省 token。"""
    # 尝试解析为 JSON 并精简
    try:
        card = json.loads(raw)
        if isinstance(card, list):
            # 多个卡片，逐个处理
            parts = [_format_single_card(c) for c in card if c]
            return "\n\n".join(parts)
        elif isinstance(card, dict):
            return _format_single_card(card)
    except (json.JSONDecodeError, TypeError):
        pass
    # 非 JSON 直接返回（但截断）
    return _truncate(raw, 500)


def _format_single_card(card: dict) -> str:
    """精简单个结构化卡片，只保留关键字段。"""
    # 天气卡片：day 可能在顶层或 modelCard 内
    if "day" in card and "location" in card:
        return _format_weather_card(card)
    if "modelCard" in card and isinstance(card["modelCard"], dict):
        mc = card["modelCard"]
        if "day" in mc and "location" in mc:
            return _format_weather_card(mc)

    # 通用卡片：提取主要字段，忽略冗余字段
    lines = []
    if "name" in card:
        lines.append(f"📌 {card['name']}")
    if "snippet" in card and card["snippet"]:
        lines.append(f"   {_truncate(card['snippet'])}")
    if "summary" in card and card["summary"]:
        lines.append(f"   {_truncate(card['summary'])}")
    # 尝试提取 modelCard 中的关键信息
    if "modelCard" in card:
        mc = card["modelCard"]
        if isinstance(mc, dict):
            for key, val in mc.items():
                if isinstance(val, (str, int, float, bool)):
                    lines.append(f"   {key}: {val}")
                elif isinstance(val, list) and len(val) <= 5:
                    lines.append(f"   {key}: {json.dumps(val, ensure_ascii=False)}")
    if not lines:
        # 兜底：JSON 输出但截断
        compact = json.dumps(card, ensure_ascii=False, default=str)
        return _truncate(compact, 500)
    return "\n".join(lines)


def _format_weather_card(card: dict) -> str:
    """精简天气卡片，只保留每日概要。"""
    location = card.get("location", "未知")
    days = card.get("day", [])
    lines = [f"🌤 {location} 天气预报"]

    for d in days[:7]:  # 最多 7 天
        date = d.get("date_day", "")
        month = d.get("time_month", "")
        week = d.get("other_week", "")
        summary = d.get("summary", "")
        high = d.get("number_high", "")
        low = d.get("number_low", "")
        wind = d.get("day_wind", "")
        wind_level = d.get("day_windlevel", "")
        humidity = d.get("humidity", "")

        label = f"{week}" if week else f"{month}/{date}"
        lines.append(
            f"   {label}: {summary} {low}~{high}°C "
            f"{wind}{wind_level} 湿度{humidity}%"
        )

    return "\n".join(lines)


@server.tool()
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

    payload = {"query": query, "summary": True, "freshness": freshness, "count": count}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.bochaai.com/v1/web-search",
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
        return header + "\n\n".join(results)

    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"Request error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@server.tool()
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
                "https://api.bochaai.com/v1/ai-search",
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

        return "\n\n".join(parts)

    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"Request error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    server.run()
