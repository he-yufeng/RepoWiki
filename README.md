# RepoWiki

**Open-source DeepWiki alternative** — generate comprehensive wiki documentation for any codebase from your terminal or browser.

[中文文档](README_CN.md)

## Why RepoWiki?

| | DeepWiki | deepwiki-open | **RepoWiki** |
|---|---------|--------------|-------------|
| Deploy | SaaS only | Docker Compose | **`pip install repowiki`** |
| Local repos | No | No | **Yes** |
| CLI | No | No | **Yes** |
| Web UI | Yes | Yes | **Yes** |
| Export | Web only | Web only | **Markdown / JSON / HTML** |
| Reading guide | No | No | **PageRank + guided path** |
| Terminal Q&A | No | No | **`repowiki chat`** |
| Dependencies | N/A | Docker + PostgreSQL | **Python + SQLite** |

## Quick Start

```bash
pip install repowiki

# set your API key (DeepSeek, OpenAI, Anthropic, etc.)
export DEEPSEEK_API_KEY=sk-xxx
# or
repowiki config set api_key sk-xxx

# scan a local project
repowiki scan ./my-project

# scan a GitHub repo
repowiki scan https://github.com/pallets/flask

# generate self-contained HTML
repowiki scan ./my-project --format html --open

# start the web interface
pip install repowiki[web]
repowiki serve
```

## Features

### Wiki Generation
Automatically generates structured documentation for any codebase:
- **Project overview** — what it does, tech stack, setup instructions
- **Module documentation** — purpose, key files, relationships, important functions
- **Architecture diagrams** — auto-detected architecture type with Mermaid visualizations
- **Reading guide** — "start here" path based on PageRank file importance ranking

### Multiple Output Formats
- **Markdown** — directory of `.md` files, ready to commit to your repo
- **JSON** — structured data for API consumption or custom rendering
- **HTML** — self-contained single file, share with anyone (Mermaid diagrams included)

### Web Interface
Three-column wiki viewer with sidebar navigation, Mermaid diagram rendering, and an AI-powered Q&A chat about the codebase.

### CLI-First Design
Everything works from the terminal. No Docker, no database server, no web browser required.

```bash
repowiki scan .                    # generate wiki
repowiki scan . -f html --open     # open in browser
repowiki scan . -l zh              # Chinese output
repowiki chat .                    # ask questions (coming soon)
repowiki config list               # show configuration
```

## Supported Languages

Python, JavaScript, TypeScript, Go, Rust, Java, Kotlin, C/C++, C#, Ruby, PHP, Swift, Dart, Vue, Svelte, and 30+ more.

## Supported LLM Providers

Powered by [litellm](https://github.com/BerriAI/litellm), RepoWiki works with 100+ LLM providers:

| Provider | Model | Alias |
|----------|-------|-------|
| Anthropic | Claude Opus 4.6 | `opus` |
| Anthropic | Claude Sonnet 4.6 | `claude` |
| OpenAI | GPT-5.4 | `gpt` |
| OpenAI | GPT-5.4 Mini | `gpt-mini` |
| Google | Gemini 3.1 Pro | `gemini` |
| Google | Gemini 2.5 Flash | `gemini-flash` |
| DeepSeek | DeepSeek V3.2 | `deepseek` |
| Alibaba | Qwen3.5 Plus | `qwen` |
| Moonshot | Kimi K2.6 | `kimi` |
| Zhipu | GLM-5 | `glm` |
| MiniMax | M2.7 | `minimax` |

```bash
repowiki config set model deepseek    # use alias
repowiki scan . -m gpt                # or pass directly
```

## Configuration

RepoWiki looks for config in this order:
1. CLI flags (`-m`, `-l`, `-o`)
2. Environment variables (`REPOWIKI_MODEL`, `REPOWIKI_API_KEY`)
3. Config file (`~/.repowiki/config.json`)
4. Provider-specific env vars (`DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)

## Project Structure

```
RepoWiki/
├── src/repowiki/
│   ├── cli.py              # Click CLI with scan/serve/chat/config commands
│   ├── config.py           # Configuration management
│   ├── core/
│   │   ├── scanner.py      # File scanning with language detection
│   │   ├── analyzer.py     # Multi-step LLM analysis pipeline
│   │   ├── graph.py        # Dependency graph + PageRank
│   │   ├── wiki_builder.py # Wiki page assembly
│   │   ├── rag.py          # TF-IDF retrieval for Q&A
│   │   └── cache.py        # SQLite caching
│   ├── llm/
│   │   ├── client.py       # litellm async wrapper
│   │   └── prompts.py      # Structured prompt templates
│   ├── ingest/
│   │   ├── local.py        # Local directory ingestion
│   │   └── github.py       # Git clone with caching
│   ├── export/
│   │   ├── markdown.py     # Markdown directory export
│   │   ├── json_export.py  # JSON export
│   │   └── html.py         # Self-contained HTML export
│   └── server/             # FastAPI web backend
├── frontend/               # React + Vite + TailwindCSS
├── pyproject.toml
└── LICENSE
```

## How It Works

1. **Scan** — Walk the directory tree, filter out binaries and generated files, detect languages and entry points
2. **Graph** — Parse import statements across 6 languages, build a dependency graph, run PageRank to rank file importance
3. **Analyze** — Send file tree + key files to LLM in 4 structured passes (overview, modules, architecture, reading guide)
4. **Cache** — Store results in SQLite keyed by content hash, skip unchanged files on re-scan
5. **Export** — Assemble wiki pages with Mermaid diagrams and source links, output in chosen format

## Development

```bash
git clone https://github.com/he-yufeng/RepoWiki.git
cd RepoWiki

# backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,web]"

# frontend
cd frontend && npm install && npm run dev

# run backend
repowiki serve --port 8000
```

## License

MIT
