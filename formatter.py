"""博查 API 响应格式化，将原始 JSON 转为 Agent 友好的精简文本。

换搜索 API 时替换此文件，实现新 API 的响应格式化逻辑。
"""

import json

from utils import _truncate


def _format_webpage(r: dict, index: int) -> str:
    """格式化单条网页搜索结果。"""
    name = r.get("name", "无标题")
    url = r.get("url", "")
    return (
        f"[{index}] {name}\n"
        f"    URL: {url}\n"
        f"    摘要: {_truncate(r.get('summary', ''))}\n"
        f"    来源: {r.get('siteName', 'N/A')} | 发布: {r.get('datePublished', 'N/A')}"
    )


def _format_rerank_result(result: dict, index: int) -> str:
    """格式化单条 rerank 结果。"""
    original_index = result.get("index", "N/A")
    score = result.get("relevance_score", result.get("rerankScore", "N/A"))
    document = result.get("document", {})
    if isinstance(document, dict):
        text = document.get("text", "")
    else:
        text = str(document)

    return (
        f"[{index}] 原始序号: {original_index} | 相关性: {score}\n"
        f"    文档: {_truncate(text, 500)}"
    )


def _format_card(raw: str) -> str:
    """格式化结构化卡片，精简输出以节省 token。"""
    try:
        card = json.loads(raw)
        if isinstance(card, list):
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
