# Knowledge Cards

One card per module: its purpose, its public surface, its
internal links, and the file to open first. Pick a card, then
open the full module page.

### [`repowiki`](modules/root.md)

> Generates wiki documentation for codebases using LLMs.

27 files · symbols [`Config`](modules/repowiki.md), [`resolve_model`](modules/repowiki.md), [`MODEL_ALIASES`](modules/repowiki.md), [`MODEL_API_BASES`](modules/repowiki.md), [`cli`](modules/repowiki.md) +56 more · concepts Dependency Graph, LLM Analysis Pipeline, Caching, RAG (Retrieval-Augmented Generation)

Entry: [`src/repowiki/__main__.py`](modules/repowiki.md), [`src/repowiki/server/routers/chat.py`](modules/repowiki.md), [`src/repowiki/server/routers/scan.py`](modules/repowiki.md) +1 more

Internal links: [`src/repowiki/cli.py`](modules/repowiki.md) → [`src/repowiki/config.py`](modules/repowiki.md), [`src/repowiki/cli.py`](modules/repowiki.md) → [`src/repowiki/core/analyzer.py`](modules/repowiki.md), [`src/repowiki/core/analyzer.py`](modules/repowiki.md) → [`src/repowiki/llm/client.py`](modules/repowiki.md), [`src/repowiki/core/analyzer.py`](modules/repowiki.md) → [`src/repowiki/llm/prompts.py`](modules/repowiki.md)

[Open the full page](modules/repowiki.md)

### `tests`

> Unit tests for the repowiki codebase covering all major components.

27 files · symbols [`test_reading_guide_ranks_by_pagerank_not_scan_order`](modules/tests.md), [`test_analyzer_passes_configured_max_tokens`](modules/tests.md), [`test_fresh_entry_survives_default_ttl`](modules/tests.md), [`test_module_analysis_reuses_cache_on_second_run`](modules/tests.md), [`test_chat_prompt_without_history_stays_two_messages`](modules/tests.md) +46 more · concepts Test Isolation, LLM Mocking, Incremental Testing, Cache Validation

Entry: [`tests/test_analyzer_guide.py`](modules/tests.md), [`tests/test_cache.py`](modules/tests.md), [`tests/test_chat_prompt.py`](modules/tests.md) +21 more

Internal links: [`tests/test_analyzer_guide.py`](modules/tests.md) → `repowiki/core/analyzer.py`, [`tests/test_cache.py`](modules/tests.md) → `repowiki/core/cache.py`, [`tests/test_chat_prompt.py`](modules/tests.md) → `repowiki/llm/prompts.py`, [`tests/test_chat_router.py`](modules/tests.md) → `repowiki/server/app.py`

[Open the full page](modules/tests.md)

### [`frontend`](modules/.github.md)

> Provides a React-based web interface for generating and viewing wiki documentation for codebases.

17 files · symbols [`dependencies`](modules/frontend.md), [`devDependencies`](modules/frontend.md), [`scripts`](modules/frontend.md), [`compilerOptions`](modules/frontend.md), [`defineConfig`](modules/frontend.md) +35 more · concepts React Router, Zustand Store, API Integration, Markdown Rendering

Entry: `frontend/src/App.tsx`, `frontend/src/components/SettingsModal.tsx`, `frontend/src/components/WikiContent.tsx` +6 more

Internal links: [`src/App.tsx`](modules/frontend.md) → [`src/pages/Home.tsx`](modules/frontend.md), [`src/App.tsx`](modules/frontend.md) → [`src/pages/WikiView.tsx`](modules/frontend.md), [`src/App.tsx`](modules/frontend.md) → [`src/pages/ChatView.tsx`](modules/frontend.md), [`src/App.tsx`](modules/frontend.md) → [`src/pages/FileView.tsx`](modules/frontend.md)

[Open the full page](modules/frontend.md)

### `evals`

> Evaluates retrieval-augmented generation (RAG) performance for code documentation by testing if LLMs can correctly identify source files based on natural language questions.

6 files · symbols [`run_eval`](modules/evals.md), [`EvalReport`](modules/evals.md) · concepts Retrieval Evaluation, Fixture Repositories, Baseline Comparison

Entry: [`evals/run_eval.py`](modules/evals.md)

Internal links: [`evals/run_eval.py`](modules/evals.md) → [`evals/fixtures/questions.json`](modules/evals.md), [`evals/run_eval.py`](modules/evals.md) → [`evals/baseline.json`](modules/evals.md), `evals/fixtures/modules/*.json` → `evals/fixtures/repos/`

[Open the full page](modules/evals.md)

### [`root`](modules/frontend.md)

> Project configuration and documentation for RepoWiki, an open-source tool that generates wiki documentation for codebases using LLMs.

6 files · symbols [`OPENAI_API_KEY`](modules/root.md), [`DEEPSEEK_API_KEY`](modules/root.md), [`ANTHROPIC_API_KEY`](modules/root.md), [`REPOWIKI_MODEL`](modules/root.md), [`REPOWIKI_LANG`](modules/root.md) +3 more · concepts LLM Integration, Package Management, Multi-language Support

Internal links: [`pyproject.toml`](modules/root.md) → [`README.md`](modules/root.md), [`pyproject.toml`](modules/root.md) → [`.env.example`](modules/root.md), [`README.md`](modules/root.md) → [`README_CN.md`](modules/root.md)

[Open the full page](modules/root.md)

### `.github`

> Contains GitHub Actions workflows for CI/CD, demo deployment, and PyPI publishing.

3 files · symbols [`lint-and-test`](modules/.github.md), [`rag-eval`](modules/.github.md), [`frontend`](modules/.github.md), [`wheel`](modules/.github.md), [`demo`](modules/.github.md) +1 more · concepts Continuous Integration, GitHub Pages Deployment, PyPI Publishing

Internal links: [`.github/workflows/ci.yml`](modules/.github.md) → [`.github/workflows/publish.yml`](modules/.github.md), [`.github/workflows/demo.yml`](modules/.github.md) → [`.github/workflows/ci.yml`](modules/.github.md)

[Open the full page](modules/.github.md)
