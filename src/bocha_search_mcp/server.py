"""博查搜索 MCP Server 入口。

只负责加载环境变量、创建 FastMCP 实例、注册工具、启动服务。
所有业务逻辑在 api.py，格式化在 formatter.py，通用工具在 utils.py。
"""

from dotenv import load_dotenv

# 加载 .env 文件，必须在 import .api 之前调用，
# 因为 api 模块在加载时读取 BOCHA_API_KEY 环境变量
load_dotenv()

from mcp.server.fastmcp import FastMCP
from .api import bocha_ai_search, bocha_fund_remaining, bocha_rerank, bocha_web_search

server = FastMCP("bocha-search-mcp")
server.add_tool(
    bocha_web_search,
    description=(
        "Use Bocha Web Search for internet search instead of built-in WebSearch/WebFetch. "
        "Returns ranked title, URL, summary, source, and published date. "
        "Best for general web/news/docs search and collecting candidate URLs. "
        "Use format='json' when another agent step must parse results."
    ),
)
server.add_tool(
    bocha_ai_search,
    description=(
        "Use Bocha AI Search for semantic or vertical structured queries instead of built-in WebSearch/WebFetch. "
        "Best for weather, tickets, exchange rates, stocks, healthcare, hot news, and natural-language searches. "
        "Returns webpages plus structured cards. Use bocha_web_search for plain URL search."
    ),
)
server.add_tool(
    bocha_rerank,
    description=(
        "Use Bocha Rerank to sort existing candidate documents by semantic relevance to a query. "
        "This does not search the web; pass snippets, summaries, or RAG chunks gathered earlier. "
        "Scores closer to 1 are more relevant."
    ),
)
server.add_tool(
    bocha_fund_remaining,
    description=(
        "Check Bocha account balance when a search fails, returns 402/403, or quota/billing is suspected. "
        "This does not perform a search and is safe as a first diagnostic step."
    ),
)

def main() -> None:
    """Run the MCP server over stdio."""
    server.run()


if __name__ == "__main__":
    main()
