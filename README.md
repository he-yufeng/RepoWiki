# repowiki

# RepoWiki

> Generates wiki documentation for codebases using LLMs.

RepoWiki analyzes codebases locally or from GitHub to produce structured wiki documentation. It scans files, uses language models to generate explanations, and outputs Markdown, JSON, or HTML. The tool includes a web interface for browsing and a CLI for scanning and chatting with the documentation. It handles incremental updates and caches results to minimize API calls.

> **Partial coverage:** this wiki was built from 118 of 124 files. Excluded directories: `.pytest_cache`, `dist`, `.ruff_cache`, `.venv`, `.git`. Pages below describe only the scanned subset.

## Tech Stack

- **Python** 3.10+ (language)
- **TypeScript** ES2020 (language)
- **FastAPI** 0.115.0+ (framework)
- **React** 19.2.5+ (framework)
- **Vite** 8.0.8+ (build tool)
- **SQLite** 3.0+ (database)

## Key Features

- Generates wiki pages from code analysis
- Exports to Markdown, JSON, and HTML
- Includes a web UI and CLI for interaction
- Supports incremental scans and caching
- Handles cross-linking between documentation pages

## Getting Started

1. Install with pip: pip install repowiki
2. Set an API key: export DEEPSEEK_API_KEY=your_key or use repowiki config set
3. Scan a project: repowiki scan ./path-to-project

## Contents

- [Overview](index.md)
- [Architecture](architecture.md)
- [Knowledge Cards](cards.md)
- **Modules**
  - [repowiki](modules/repowiki.md)
  - [tests](modules/tests.md)
  - [frontend](modules/frontend.md)
  - [evals](modules/evals.md)
  - [root](modules/root.md)
  - [.github](modules/.github.md)
- [Reading Guide](reading-guide.md)
- [Dependencies](dependencies.md)
- [Symbol Index](symbols.md)
