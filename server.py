"""博查搜索 MCP Server 入口。

只负责加载环境变量、创建 FastMCP 实例、注册工具、启动服务。
所有业务逻辑在 api.py，格式化在 formatter.py，通用工具在 utils.py。
"""

from dotenv import load_dotenv

# 加载 .env 文件，必须在 import api 之前调用，
# 因为 api.py 在模块加载时读取 BOCHA_API_KEY 环境变量
load_dotenv()

from mcp.server.fastmcp import FastMCP
from api import bocha_web_search, bocha_ai_search

server = FastMCP("bocha-search-mcp")
server.add_tool(bocha_web_search)
server.add_tool(bocha_ai_search)

if __name__ == "__main__":
    server.run()
