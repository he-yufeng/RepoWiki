<div align="center">

<img src="docs/banner.png" alt="RepoWiki — 为任意代码库生成 wiki 文档" width="100%">

[![PyPI](https://img.shields.io/pypi/v/repowiki.svg)](https://pypi.org/project/repowiki/)
[![Python](https://img.shields.io/pypi/pyversions/repowiki.svg)](https://pypi.org/project/repowiki/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/he-yufeng/RepoWiki/actions/workflows/ci.yml/badge.svg)](https://github.com/he-yufeng/RepoWiki/actions/workflows/ci.yml)

[**快速开始**](#快速开始) · [**工作原理**](#工作原理) · [English](README.md)

</div>

**开源 DeepWiki 替代品** — 从终端或浏览器为任意代码仓库生成完整 wiki 文档。

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
export DEEPSEEK_API_KEY=<your-api-key>
# 或者
repowiki config set api_key <your-api-key>

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

扫描时会遵守 `.gitignore` 和 `.repowikiignore`，并默认跳过 `.env`、`.env.local`、`.npmrc`、`.pypirc`、SSH 私钥等本地敏感文件，避免把不该进入文档上下文的内容喂给后续分析。

## 核心功能

- **结构化 wiki** — 项目概览、逐模块文档、自动识别的架构（含 Mermaid 图），以及基于 PageRank 的"从这里开始读"路径。
- **import 感知排名** — 先解析 Python 和 JS/TS 的 import 再排名，并跳过 minified/生成式 bundle，避免浪费 LLM 上下文。
- **三种导出格式** — 可直接提交的 Markdown 目录、结构化 JSON，或自包含、随手能分享的 HTML 单文件（含图表）。
- **Web 查看器 + 终端问答** — 三栏浏览器界面，或 `repowiki chat .` 在终端里做基于源码的问答（内置 TF-IDF 检索，无需 embedding 服务）。
- **CLI 优先** — 不需要 Docker、数据库或浏览器。

```bash
repowiki scan .                    # 生成 wiki
repowiki scan . -f html --open     # 浏览器打开
repowiki scan . -l zh              # 中文输出
repowiki chat .                    # 终端里就代码问答
```

## 语言与模型

识别 Python、JavaScript、TypeScript、Go、Rust、Java、Kotlin、C/C++、C#、Ruby、PHP、Swift 等 30+ 种语言。litellm 的 100+ 提供商都能用，用别名选一个，或直接传模型名：

```bash
repowiki config set model deepseek   # deepseek / claude / gpt / gemini / qwen / kimi / glm ...
repowiki scan . -m gpt               # 或直接传模型名
```

## 工作原理

![RepoWiki 流程](docs/architecture.png)

1. **扫描** — 遍历目录树，过滤二进制、生成式 bundle 和超大文件，检测语言和入口文件
2. **建图** — 解析 6 种语言的 import，正确处理 Python 包内相对导入和
   JavaScript / TypeScript 相对模块，再用 PageRank 计算文件重要性
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

## 后续规划

生成、Web 界面、图表这几块已经能用，接下来想让 wiki 保持新鲜、彼此连通：

- **增量重生成**：只重生成自上次运行以来源码有变化的页面，大仓库更新 wiki 时不必每次整体重建。
- **交叉引用链接**：把某个模块页里提到的符号链到它定义所在的页面，让 wiki 读起来像一份相互连通的文档，而不是一堆孤立页面。
- **更多图表类型**：在依赖图之外再加调用图和数据流图——分析本来就走了 import，能挖出更多。
- **发布成静态站点**：一条命令导出成可直接上 GitHub Pages 的站点，让生成的 wiki 能当项目文档用，而不只是一个本地文件。

## 相关项目

如果 RepoWiki 帮你摸清了一个代码库，下面几个我做的东西也许你会喜欢：

- [**CoreCoder**](https://github.com/he-yufeng/CoreCoder) — 想搞懂一个 coding agent 到底怎么运作？把整套约 1000 行引擎从头读到尾，而不是当黑箱。
- [**FindJobs-Agent**](https://github.com/he-yufeng/FindJobs-Agent) — 别再手动刷招聘网站：它按你的简历给岗位排序，还能跑模拟面试。
- [**ContractGuard**](https://github.com/he-yufeng/ContractGuard) — 签字前先把有风险的条款挑出来：它读合同、标出危险点。
- [**GitSense**](https://github.com/he-yufeng/GitSense) — 想给开源做贡献？它帮你找到值得做的 issue，还能估你的 PR 多大概率被合。
- [**CodeABC**](https://github.com/he-yufeng/CodeABC) — 不会写代码也能看懂一个项目，专给小白做的。

## 许可证

MIT
