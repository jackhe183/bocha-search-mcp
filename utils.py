"""通用工具函数，与具体搜索 API 无关，任何搜索 MCP 都可复用。"""

import re

# 摘要最大长度（字符），超长截断并加省略号
MAX_SUMMARY_LEN = 300
# 单次输出最大字符数，防止 token 爆炸
MAX_TOTAL_OUTPUT = 8000

# 摘要中常见的广告/导航噪音模式
_NOISE_PATTERNS = [
    r"咨询电话[：:]?\s*\d[\d\-]+\s*",           # 咨询电话: 400-626-9916
    r"客服电话[：:]?\s*\d[\d\-]+\s*",           # 客服电话: 400-xxx
    r"电话[：:]?\s*\d{3}[\d\-]{7,}\s*",          # 电话: 400-xxx-xxx
    r"\d{5,}\s+.{0,30}(?:区|路|号|室|层)",       # 经销商地址: 4009726368 上海市浦东新区康杉路118号
    r"打开APP[，,]?\s*查看更多.{0,20}",          # 打开APP, 查看更多高清行情
    r"打开.{0,5}[\"'].{0,100}",                   # 打开微信"扫一扫"... 整段去掉
    r"去APP.{0,20}",                             # 去APP中参与热议吧
    r"关注手机.{0,30}随时看",                    # 关注手机金投网, 财经动态随时看
    r"下载.{0,10}APP.{0,20}",                    # 下载XX APP
    r"扫码.{0,30}",                             # 扫码关注/扫码下载
    r"点击.{0,5}查看更多",                       # 点击查看更多
    r"关灯\s*发送\s*发表成功.{0,20}",            # 关灯 发送 发表成功! 视频详情
    r"收藏\s*引用\s*分享\s*推荐",                 # 收藏 引用 分享 推荐
    r"咨询我.{0,10}",                            # 咨询我 / 我也要问
    r"我也要问.{0,10}",                          # 我也要问
    r"还没有.{0,5}账户.{0,10}注册",              # 还没有龙源账户? 立即注册
    r"立即注册",                                 # 立即注册
    r"文章作者[：:]\s*\S+\s*",                   # 文章作者: 小编
    r"浏览次数[：:]?\s*\d*\s*",                   # 浏览次数: 123
    r"发表时间[：:]\s*\S+\s*",                   # 发表时间: 2025-01-09
    r"上传人[：:]\s*\S+\s*",                     # 上传人: 七巧**rt
    r"版权归作者所有.{0,50}",                     # 版权声明
    r"责任编辑[：:]\s*\S+\s*",                   # 责任编辑: xxx
    r"声明[：:]\s*.{0,30}(?:$|\n)",              # 声明: xxx
    r"备注[：:].{0,50}",                          # 备注: 以上汇率仅供参考
    r"询问底价.{0,50}",                          # 询问底价 基本参数
]

_NOISE_RE = re.compile("|".join(_NOISE_PATTERNS))


def _clean_summary(text: str) -> str:
    """清理摘要中的广告/导航噪音文字。"""
    if not text:
        return text
    cleaned = _NOISE_RE.sub("", text)
    # 清理多余空白
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


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
