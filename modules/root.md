# root

> Project configuration and documentation for RepoWiki, an open-source tool that generates wiki documentation for codebases using LLMs.

The root module contains essential project configuration files, package metadata, and documentation. It defines the project's dependencies, build settings, and provides user-facing documentation in both English and Chinese. Key files include pyproject.toml for package configuration, README.md for project overview, and .env.example for environment variable setup.

## Files

### `.env.example`

Template for environment variables configuration, specifying required API keys and optional settings for LLM providers and output language.

- `OPENAI_API_KEY` (environment_variable) - API key for OpenAI LLM provider
- `DEEPSEEK_API_KEY` (environment_variable) - API key for DeepSeek LLM provider
- `ANTHROPIC_API_KEY` (environment_variable) - API key for Anthropic LLM provider
- `REPOWIKI_MODEL` (environment_variable) - Default LLM model to use (optional)
- `REPOWIKI_LANG` (environment_variable) - Output language for documentation (en, zh, ja, ko)

### `README.md`

Primary project documentation in English, featuring installation instructions, feature overview, and usage examples.

### `pyproject.toml`

Python project configuration file defining metadata, dependencies, build settings, and tool configurations.

- `repowiki` (package) - Main package name and entry point configuration
- [`cli`](repowiki.md) (script) - Command-line interface entry point
- `web` (dependency_group) - Optional dependencies for web server functionality

### `.gitignore`

Specifies files and directories to be ignored by Git, including build artifacts, virtual environments, and cache files.

### `LICENSE`

MIT license file granting permissions for software use, modification, and distribution.

### `README_CN.md`

Chinese translation of the primary README.md, providing localized documentation for Chinese-speaking users.

## Key Concepts

- **LLM Integration**: Configuration and setup for multiple LLM providers (OpenAI, DeepSeek, Anthropic) to generate documentation
- **Package Management**: Defines Python package metadata, dependencies, and build process using pyproject.toml and hatchling
- **Multi-language Support**: Provides documentation in both English and Chinese through README.md and README_CN.md

## Internal Relationships

- `pyproject.toml` → `README.md`: pyproject.toml references README.md as the project's readme file
- `pyproject.toml` → `.env.example`: pyproject.toml dependencies (like python-dotenv) interact with environment variables defined in .env.example
- `README.md` → `README_CN.md`: README.md links to README_CN.md for Chinese documentation
