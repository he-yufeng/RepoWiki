# RepoWiki

> Generates wiki documentation for codebases using AI analysis.

RepoWiki is an open-source tool that automatically creates comprehensive wiki documentation for any codebase. It analyzes source code using LLMs to generate structured documentation including project overviews, module descriptions, architecture diagrams, and cross-linked pages. The tool works with both local repositories and GitHub URLs, and can export documentation in multiple formats including Markdown, JSON, and self-contained HTML. It includes features like incremental scanning to avoid redundant API calls, a web interface for browsing documentation, and a chat interface for asking questions about the codebase. The system uses SQLite for caching and state management, making it lightweight and easy to deploy without complex infrastructure.

> **Partial coverage:** this wiki was built from 118 of 124 files. Excluded directories: `.git`. Pages below describe only the scanned subset.

## Tech Stack

- **Python** 3.10+ (language)
- **FastAPI** 0.115.0+ (web framework)
- **React** 19.2.5+ (frontend)
- **TypeScript** 6.0.2+ (frontend)
- **SQLite** 3.0+ (database)
- **LiteLLM** 1.40.0+ (LLM client)

## Key Features

- AI-powered code analysis and documentation generation
- Multiple export formats (Markdown, JSON, HTML)
- Incremental scanning with SQLite caching
- Web interface for browsing documentation
- Chat interface for codebase questions
- Cross-linked documentation pages
- Support for local and GitHub repositories

## Getting Started

1. pip install repowiki
2. Set API key: export DEEPSEEK_API_KEY=your_key
3. Scan a project: repowiki scan ./my-project
