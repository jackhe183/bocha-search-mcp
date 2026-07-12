# bocha-search-mcp

博查搜索 MCP Server，为 Claude Code 等 AI Agent 提供网络搜索能力。

## 工具说明

| 工具 | 用途 | 适用场景 |
|------|------|---------|
| `bocha_web_search` | 网页搜索 | 查找技术文档、新闻资讯、一般性搜索 |
| `bocha_ai_search` | AI 语义搜索 | 查天气、票务、汇率、新闻热点等结构化信息 |

**选择建议**：一般搜索用 `bocha_web_search`；需要结构化数据（天气/票务/汇率等）用 `bocha_ai_search`。

## 快速开始

### 1. 安装依赖

```bash
cd bocha-search-mcp
uv sync
```

### 2. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，填入博查 API Key：

```env
BOCHA_API_KEY="sk-xxx"
```

> Key 获取：[https://open.bochaai.com](https://open.bochaai.com) 注册后在控制台创建。

### 3. 注册到 Claude Code

**macOS / Linux：**

```bash
claude mcp add bocha-search -s user -- \
  /你的路径/bocha-search-mcp/.venv/bin/python \
  /你的路径/bocha-search-mcp/server.py
```

**Windows（PowerShell）：**

```powershell
claude mcp add bocha-search -s user -- `
  D:\projects\bocha-search-mcp\.venv\Scripts\python.exe `
  D:\projects\bocha-search-mcp\server.py
```

> `-s user` 表示全局可用，也可用 `-s project` 仅当前项目可用。

### 4. 验证

重启 Claude Code 后，运行：

```bash
claude mcp list
```

看到 `bocha-search: ✔ Connected` 即配置成功。

在对话中直接说"搜索 xxx"，Claude Code 会自动调用博查搜索。

### 5. 禁用内置 WebSearch（可选）

如果你使用非官方订阅，内置 WebSearch 可能无法使用。可在 `~/.claude/settings.json` 中禁用：

```json
{
  "permissions": {
    "deny": ["WebSearch"]
  }
}
```

## 测试

### 直接调用 Python 函数

```python
import asyncio
from dotenv import load_dotenv
load_dotenv()  # 必须在 import api 之前调用
from api import bocha_web_search, bocha_ai_search

async def main():
    print(await bocha_web_search("FastMCP 使用教程", count=3))
    print(await bocha_ai_search("今天北京天气", count=3))

asyncio.run(main())
```

### MCP Inspector 可视化测试

```bash
npx @modelcontextprotocol/inspector .venv/bin/python server.py
```

浏览器打开 `http://localhost:5173`，在 Tools 面板手动测试。

## 项目结构

```
bocha-search-mcp/
├── server.py        # MCP 入口：加载环境变量、注册工具、启动服务
├── api.py           # 博查 API 客户端：HTTP 调用、错误处理、工具函数
├── formatter.py     # 博查响应格式化：网页结果、结构化卡片、天气卡片
├── utils.py         # 通用工具：参数校验、输出截断、长度限制
├── pyproject.toml   # 依赖声明
├── .env.example     # API Key 格式示例
├── .env             # API Key（本地，不提交 git）
└── .gitignore
```

**换搜索 API？** 只需替换 `api.py` + `formatter.py`，`utils.py` 和 `server.py` 不用动。

## 修改后生效方式

修改代码保存即可。Claude Code 每次调用都启动新进程，无需手动重启 MCP 服务。
