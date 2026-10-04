# root

> Project configuration and documentation root for RepoWiki.

The root module contains essential configuration files, project metadata, and documentation that define the RepoWiki project setup, dependencies, and usage instructions.

## Files

### `.env.example`

Template environment configuration file for API keys and settings.

- `OPENAI_API_KEY` (environment_variable) - API key for OpenAI LLM provider.
- `DEEPSEEK_API_KEY` (environment_variable) - API key for DeepSeek LLM provider.
- `ANTHROPIC_API_KEY` (environment_variable) - API key for Anthropic LLM provider.
- `REPOWIKI_MODEL` (environment_variable) - Default LLM model to use (e.g., deepseek/deepseek-chat).
- `REPOWIKI_LANG` (environment_variable) - Output language for documentation (en, zh, ja, ko).

### `README.md`

Primary project documentation with overview, features, and usage examples.

- `repowiki scan` (cli_command) - Command to scan a codebase and generate wiki documentation.
- `repowiki chat` (cli_command) - Command for interactive terminal Q&A about the codebase.
- `repowiki serve` (cli_command) - Command to start the web interface for browsing documentation.

### `pyproject.toml`

Python project configuration defining dependencies, build settings, and metadata.

- `repowiki` (python_package) - Main package entry point defined in project.scripts.
- `litellm` (dependency) - LLM orchestration library for API calls.
- `fastapi` (dependency) - Web framework for the optional web interface.

### `.gitignore`

Specifies files and directories to be ignored by Git.

### `LICENSE`

MIT license terms for the project.

### `README_CN.md`

Chinese language version of the README documentation.

## Key Concepts

- **LLM Integration**: Uses multiple LLM providers (OpenAI, DeepSeek, Anthropic) via litellm for AI-powered code analysis.
- **Incremental Caching**: SQLite cache stores analysis results to avoid redundant LLM API calls on re-scans of unchanged code.
- **Multi-format Export**: Supports output in Markdown, JSON, and self-contained HTML for documentation flexibility.

## Internal Relationships

- `README.md` → `README_CN.md`: README_CN.md is a translated version of README.md for Chinese users.
- `pyproject.toml` → `.env.example`: pyproject.toml dependencies (e.g., python-dotenv) load environment variables defined in .env.example.
- `pyproject.toml` → `README.md`: pyproject.toml references README.md as the project readme file.
