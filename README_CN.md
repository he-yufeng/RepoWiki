# RepoWiki

**开源 DeepWiki 替代品** — 从终端或浏览器为任意代码仓库生成完整 wiki 文档。

[English](README.md)

## 为什么选 RepoWiki？

| | DeepWiki | deepwiki-open | **RepoWiki** |
|---|---------|--------------|-------------|
| 部署方式 | SaaS，不可自托管 | Docker Compose | **`pip install repowiki`** |
| 本地仓库 | 不支持 | 不支持 | **原生支持** |
| CLI | 无 | 无 | **有** |
| Web UI | 有 | 有 | **有** |
| 导出格式 | 仅网页 | 仅网页 | **Markdown / JSON / HTML** |
| 阅读指南 | 无 | 无 | **PageRank 排名 + 阅读路径** |
| 终端问答 | 无 | 无 | **`repowiki chat`** |
| 依赖 | N/A | Docker + PostgreSQL | **Python + SQLite** |

## 快速开始

```bash
pip install repowiki

# 设置 API Key（DeepSeek、OpenAI、Anthropic 等）
export DEEPSEEK_API_KEY=sk-xxx
# 或者
repowiki config set api_key sk-xxx

# 扫描本地项目
repowiki scan ./my-project

# 扫描 GitHub 仓库
repowiki scan https://github.com/pallets/flask

# 生成自包含 HTML 并打开
repowiki scan ./my-project --format html --open

# 启动 Web 界面
pip install repowiki[web]
repowiki serve
```

## 核心功能

### Wiki 生成
自动为任意代码仓库生成结构化文档：
- **项目概览** — 做什么、技术栈、如何运行
- **模块文档** — 用途、关键文件、模块间关系、重要函数
- **架构图** — 自动识别架构模式，Mermaid 可视化
- **阅读指南** — 基于 PageRank 文件重要性排名的"从这里开始读"路径

### 多格式导出
- **Markdown** — `.md` 文件目录，可以直接放进仓库当文档用
- **JSON** — 结构化数据，方便 API 消费或自定义渲染
- **HTML** — 自包含单文件，分享给任何人都能直接打开（内含 Mermaid 图表）

### Web 界面
三栏布局 wiki 查看器：侧边导航 + 内容区 + Mermaid 图表，还有 AI 问答聊天功能。

### CLI 优先
所有功能都能在终端完成。不需要 Docker，不需要数据库，不需要浏览器。

```bash
repowiki scan .                    # 生成 wiki
repowiki scan . -f html --open     # 浏览器打开
repowiki scan . -l zh              # 中文输出
repowiki chat .                    # 终端问答（即将推出）
repowiki config list               # 查看配置
```

## 支持的语言

Python、JavaScript、TypeScript、Go、Rust、Java、Kotlin、C/C++、C#、Ruby、PHP、Swift、Dart、Vue、Svelte 等 30+ 种编程语言。

## 支持的 LLM 提供商

基于 [litellm](https://github.com/BerriAI/litellm)，支持 100+ LLM 提供商：

| 提供商 | 模型 | 别名 |
|--------|------|------|
| DeepSeek | deepseek-chat | `deepseek` |
| OpenAI | gpt-4o | `gpt4o` |
| OpenAI | gpt-5 | `gpt5` |
| Anthropic | claude-sonnet-4 | `claude` |
| Google | gemini-2.5-flash | `gemini` |
| 阿里云 | qwen-plus | `qwen` |

## 工作原理

1. **扫描** — 遍历目录树，过滤二进制和生成文件，检测语言和入口文件
2. **建图** — 解析 6 种语言的 import 语句，构建依赖图，PageRank 计算文件重要性
3. **分析** — 4 步 LLM 分析（概览、模块、架构、阅读指南），并发执行
4. **缓存** — SQLite 按内容 hash 缓存，重新扫描时跳过未变更文件
5. **导出** — 组装 wiki 页面，注入 Mermaid 图和源码链接，按选定格式输出

## 开发

```bash
git clone https://github.com/he-yufeng/RepoWiki.git
cd RepoWiki

# 后端
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,web]"

# 前端
cd frontend && npm install && npm run dev

# 启动后端
repowiki serve --port 8000
```

## 许可证

MIT
