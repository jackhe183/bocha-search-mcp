# 博察搜索 MCP 服务器

> 为 AI 提供强大的中文搜索能力，从近百亿网页和生态内容源中获取高质量信息

## ✨ 特性

- 🔍 **全网搜索** - 覆盖近百亿网页，包括新闻、百科、天气、医疗等
- 🤖 **AI 搜索** - 智能识别搜索词语义，返回结构化模态卡
- 🚀 **极简安装** - 使用 uv 一键安装，无需复杂配置
- 💻 **本地运行** - 完全在本地运行，与平台无关

## 📦 安装

### 前置要求

- [Python](https://www.python.org/) >= 3.10
- [uv](https://github.com/astral-sh/uv) (Python 包管理器)

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/jackhe183/bocha-search-mcp.git
cd bocha-search-mcp

# 2. 安装依赖
uv sync

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env 文件，填入您的博察 API Key
```

### 获取 API Key

访问 [博察AI开放平台](https://open.bochaai.com) 注册并获取免费 API Key

## 🚀 使用

### 命令行运行

```bash
# 运行 MCP 服务器
uv run bocha-mcp
```

### Claude Desktop 配置

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "bocha-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/bocha-mcp",
        "run",
        "bocha-mcp"
      ],
      "env": {
        "BOCHA_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Windows 配置示例：**
```json
{
  "mcpServers": {
    "bocha-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\YourName\\Desktop\\bocha-mcp",
        "run",
        "bocha-mcp"
      ],
      "env": {
        "BOCHA_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

配置文件位置：
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

## 🔧 可用工具

### 1. `bocha_web_search` - 全网搜索

从博察搜索全网信息和网页链接，返回标题、URL、摘要、网站名称等。

**参数：**
- `query` (必填): 搜索词
- `freshness` (可选): 时间范围，默认 `noLimit`
  - 选项: `noLimit`, `oneYear`, `oneMonth`, `oneWeek`, `oneDay`, `YYYY-MM-DD..YYYY-MM-DD`
- `count` (可选): 返回结果数量 (1-50)，默认 10

### 2. `bocha_ai_search` - AI 搜索

在全网搜索基础上，额外返回垂直领域内容的结构化模态卡（天气卡、百科卡等）。

**参数：**
- `query` (必填): 搜索词
- `freshness` (可选): 时间范围，默认 `noLimit`
- `count` (可选): 返回结果数量 (1-50)，默认 10

## 📖 使用示例

在 Claude 中这样使用：

```
请帮我在博察上搜索 "2024年人工智能发展趋势"
```

```
用博察AI搜索查找最近的Python编程教程
```

## 🐛 调试

使用 MCP Inspector 调试本地服务器：

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/bocha-mcp run bocha-mcp
```

## ❓ 常见问题

**Q: API Key 在哪里获取？**
A: 访问 https://open.bochaai.com 注册即可获得免费额度。

**Q: 支持哪些 AI 客户端？**
A: 支持 Claude Desktop、Cursor、Windsurf、Cline 等所有支持 MCP 协议的客户端。

**Q: 是否需要联网？**
A: 是的，需要访问博察 API 进行搜索。

## 📄 许可证

MIT License

## 🔗 相关链接

- [博察AI开放平台](https://open.bochaai.com)
- [MCP 协议文档](https://modelcontextprotocol.io)
- [GitHub 仓库](https://github.com/jackhe183/bocha-search-mcp)
