# root

> Root module for RepoWiki - generates wiki documentation for codebases

Contains core configuration and project metadata for RepoWiki, including environment setup, package configuration, licensing, and multilingual documentation.

## Files

### `.env.example`

Template for environment configuration including LLM API keys and language settings

### `README.md`

Primary English documentation with installation, usage, and feature overview

### `pyproject.toml`

Python package configuration including dependencies and build settings

### `.gitignore`

Specifies files/directories to exclude from version control

### `LICENSE`

MIT license terms for the project

### `README_CN.md`

Chinese language version of the documentation

## Key Concepts

- **Multi-format output**: Core capability to generate documentation in Markdown, JSON, and HTML formats
- **Incremental builds**: Tracks state to only regenerate changed documentation

## Internal Relationships

- `pyproject.toml` → `README.md`: References README.md as project documentation
- `.env.example` → `README.md`: Example configuration referenced in README setup instructions
