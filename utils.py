"""通用工具函数，与具体搜索 API 无关，任何搜索 MCP 都可复用。"""

# 摘要最大长度（字符），超长截断并加省略号
MAX_SUMMARY_LEN = 300
# 单次输出最大字符数，防止 token 爆炸
MAX_TOTAL_OUTPUT = 8000


def _validate_params(query: str, count: int) -> str | None:
    """参数不合法时返回错误字符串，否则返回 None。"""
    if not query or not query.strip():
        return (
            "❌ 参数错误：搜索关键词 query 为空。\n"
            "   排查：调用搜索工具时必须提供非空的 query 参数，"
            "例如 bocha_web_search(query=\"搜索内容\")。"
        )
    if not 1 <= count <= 50:
        return (
            f"❌ 参数错误：count={count}，超出有效范围 1-50。\n"
            f"   排查：将 count 调整为 1-50 之间的整数，例如 count=10。"
        )
    return None


def _limit_output(text: str) -> str:
    """限制输出总长度，防止 token 爆炸。"""
    if len(text) <= MAX_TOTAL_OUTPUT:
        return text
    return text[:MAX_TOTAL_OUTPUT] + (
        "\n\n... 输出已截断，省略了部分结果。"
        "如需更多请缩小搜索范围或减少 count 参数。"
    )


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
