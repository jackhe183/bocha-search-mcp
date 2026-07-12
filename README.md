# bocha-search-mcp

博查搜索 MCP Server，为 Claude Code 等 AI Agent 提供网络搜索能力。

## 工具说明

| 工具 | 用途 | 适用场景 |
|------|------|---------|
| `bocha_web_search` | 网页搜索 | 查找技术文档、新闻资讯、一般性搜索 |
| `bocha_ai_search` | AI 语义搜索 | 查天气、票务、汇率、新闻热点等结构化信息 |
| `bocha_rerank` | 语义重排 | 搜索后筛选最相关网页、RAG 候选排序 |
| `bocha_fund_remaining` | 余额查询 | 搜索失败、疑似欠费或排查 API Key 状态 |

**选择建议**：一般搜索用 `bocha_web_search`；需要结构化数据（天气/票务/汇率等）用 `bocha_ai_search`；拿到候选结果后需要二次筛选用 `bocha_rerank`；遇到 402 或搜索异常先用 `bocha_fund_remaining` 查余额。

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
# 可选：官方文档中也可能出现 https://api.bocha.cn
BOCHA_API_BASE_URL="https://api.bochaai.com"
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

### 5. 禁用内置 WebSearch / WebFetch（可选）

如果你希望 Agent 统一通过博查 API 检索，避免绕过第三方搜索引擎，可在 `~/.claude/settings.json` 中禁用 Claude Code 内置联网工具：

```json
{
  "permissions": {
    "deny": ["WebSearch", "WebFetch"]
  }
}
```

也可以写到项目级 `.claude/settings.json`，只对当前项目生效。

> 注意：禁用 `WebFetch` 后，Agent 将不能再直接抓取网页全文，只能使用博查返回的标题、URL、摘要和结构化卡片。如果任务需要逐字核验网页正文，需要额外接入网页正文抽取 API，或临时允许 `WebFetch`。

## 测试

### 直接调用 Python 函数

```python
import asyncio
from dotenv import load_dotenv
load_dotenv()  # 必须在 import api 之前调用
from api import (
    bocha_web_search,
    bocha_ai_search,
    bocha_rerank,
    bocha_fund_remaining,
)

async def main():
    print(await bocha_web_search("FastMCP 使用教程", count=3))
    print(await bocha_web_search("FastMCP 使用教程", count=3, format="json"))
    print(await bocha_ai_search("今天北京天气", count=3))
    print(await bocha_rerank(
        "FastMCP 如何注册工具",
        ["FastMCP 支持 add_tool 注册函数", " unrelated document "],
        top_n=1,
    ))
    print(await bocha_fund_remaining())

asyncio.run(main())
```

### MCP Inspector 可视化测试

```bash
npx @modelcontextprotocol/inspector .venv/bin/python server.py
```

浏览器打开 `http://localhost:5173`，在 Tools 面板手动测试。

### Claude Code 实测

注册 MCP 后，可在 Claude Code 中依次输入：

```text
使用 MCP 工具 bocha_fund_remaining，format=json，查一下博查余额。
```

```text
使用 MCP 工具 bocha_web_search，query="FastMCP MCP add_tool"，count=3，format=json，验证是否能返回 URL。
```

```text
使用 MCP 工具 bocha_ai_search，query="今天北京天气"，count=3，format=json，验证是否返回网页和结构化卡片。
```

```text
使用 MCP 工具 bocha_rerank，query="FastMCP 如何注册工具"，documents=["FastMCP 可以通过 add_tool 注册 Python 函数为 MCP 工具。","今天晚饭吃什么。"]，top_n=1，format=json。
```

预期结果：

- `bocha_fund_remaining` 返回 `ok=true` 和 `remaining`。
- `bocha_web_search` 返回 `ok=true`、`result_count` 和带 `url` 的 `results`。
- `bocha_ai_search` 返回 `ok=true`、`webpage_count`、`card_count`。
- `bocha_rerank` 返回 `ok=true`，最相关文档应排在前面。
- 若返回 402/403，先查余额；余额充足但仍失败时，检查该接口是否开通或是否需要白名单。

## 项目结构

```
bocha-search-mcp/
├── server.py        # MCP 入口：加载环境变量、注册工具、启动服务
├── api.py           # 博查 API 客户端：HTTP 调用、错误处理、工具函数
├── formatter.py     # 博查响应格式化：网页结果、结构化卡片、天气卡片
├── utils.py         # 通用工具：参数校验、输出截断、长度限制
├── tests/           # 离线单元测试
├── pyproject.toml   # 依赖声明
├── .env.example     # API Key 格式示例
├── .env             # API Key（本地，不提交 git）
└── .gitignore
```

**换搜索 API？** 只需替换 `api.py` + `formatter.py`，`utils.py` 和 `server.py` 不用动。

## 修改后生效方式

修改代码保存即可。Claude Code 每次调用都启动新进程，无需手动重启 MCP 服务。

## Agent 友好输出

`bocha_web_search` 和 `bocha_ai_search` 支持 `format="json"`，用于让 Agent 稳定解析标题、URL、摘要、结构化卡片等字段。默认 `format="text"` 保持兼容，适合直接阅读。

结构化输出包含：

- `ok`: 调用是否成功。
- `query`: 实际查询词。
- `result_count` / `webpage_count` / `card_count`: 结果数量。
- `rank`: 搜索结果排序位置。
- `title`, `url`, `summary`, `site_name`, `published_at`: 网页结果关键字段。
- `error`: 失败时的可操作诊断信息。

搜索结果质量边界：

- 博查 Web Search 返回的是搜索摘要，不是网页全文；如果摘要不完整，这是搜索 API 的信息边界。
- MCP 层负责把结果整理得更清晰、稳定、可解析，但不会凭空补全 API 未返回的正文内容。
- 对多条摘要或候选段落做相关性筛选时，使用 `bocha_rerank`。
