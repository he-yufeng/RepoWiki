# RepoWiki

> Generate wiki documentation for any codebase from your terminal or browser.

RepoWiki is an open-source tool that automatically generates comprehensive wiki documentation for any codebase. It works by scanning local projects or GitHub repositories, analyzing the code structure, and producing detailed documentation. The tool supports multiple output formats, including Markdown, JSON, and HTML, making it easy to share or integrate the documentation into existing workflows. RepoWiki also includes a web interface and a terminal-based chat feature for interactive Q&A about the codebase. It respects [`.gitignore`](modules/root.md) and `.repowikiignore` files during scans and skips common secret files by default.

## Tech Stack

- **Python** 3.10+ (language)
- **React** 19.2.5 (frontend)
- **TypeScript** 6.0.2 (frontend)
- **FastAPI** 0.115.0 (backend)
- **SQLite** 3.0+ (database)

## Key Features

- Structured wiki with project overview, per-module docs, and Mermaid diagrams.
- Cross-linked pages and symbol index for easy navigation.
- Incremental re-runs to only regenerate changed pages.
- Three output formats: Markdown, JSON, and self-contained HTML.
- Web viewer and terminal chat for interactive Q&A.

## Getting Started

1. Install RepoWiki using pip: `pip install repowiki`.
2. Set your API key: `export DEEPSEEK_API_KEY=<your-api-key>`.
3. Scan a local project or GitHub repo: `repowiki scan ./my-project` or `repowiki scan https://github.com/pallets/flask`.
4. Start the web interface: `pip install repowiki[web]` and `repowiki serve ./my-project`.
