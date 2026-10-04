# Knowledge Cards

One card per module: its purpose, its public surface, its
internal links, and the file to open first. Pick a card, then
open the full module page.

### `tests`

> Unit tests for the repowiki codebase, covering core functionality like AI analysis, caching, RAG, and exports.

27 files · symbols [`test_reading_guide_ranks_by_pagerank_not_scan_order`](modules/tests.md), [`StubLLM`](modules/tests.md), [`test_module_analysis_reuses_cache_on_second_run`](modules/tests.md), [`Cache`](modules/tests.md), [`build_chat_prompt`](modules/tests.md) +37 more · concepts StubLLM, PageRank, Incremental Regeneration, RAG (Retrieval-Augmented Generation)

Entry: [`tests/test_analyzer_guide.py`](modules/tests.md), [`tests/test_cache.py`](modules/tests.md), [`tests/test_chat_prompt.py`](modules/tests.md) +21 more

Internal links: [`tests/test_analyzer_guide.py`](modules/tests.md) → [`tests/test_cache.py`](modules/tests.md), [`tests/test_chat_prompt.py`](modules/tests.md) → [`tests/test_chat_router.py`](modules/tests.md), [`tests/test_incremental.py`](modules/tests.md) → [`tests/test_cache.py`](modules/tests.md), [`tests/test_rag.py`](modules/tests.md) → [`tests/test_rag_eval.py`](modules/tests.md)

[Open the full page](modules/tests.md)

### [`frontend`](modules/.github.md)

> Provides a React-based web interface for generating and viewing wiki documentation for codebases.

17 files · symbols [`dependencies`](modules/frontend.md), [`devDependencies`](modules/frontend.md), [`scripts`](modules/frontend.md), [`compilerOptions`](modules/frontend.md), [`defineConfig`](modules/frontend.md) +21 more · concepts State Management, Real-time Streaming, Dynamic Content Rendering, API Integration

Entry: `frontend/src/App.tsx`, `frontend/src/components/SettingsModal.tsx`, `frontend/src/components/WikiContent.tsx` +6 more

Internal links: [`App.tsx`](modules/frontend.md) → [`src/pages/Home.tsx`](modules/frontend.md), [`App.tsx`](modules/frontend.md) → [`src/pages/WikiView.tsx`](modules/frontend.md), [`App.tsx`](modules/frontend.md) → [`src/pages/ChatView.tsx`](modules/frontend.md), [`App.tsx`](modules/frontend.md) → [`src/pages/FileView.tsx`](modules/frontend.md)

[Open the full page](modules/frontend.md)

### [`root`](modules/frontend.md)

> Project configuration and documentation root for RepoWiki.

6 files · symbols [`OPENAI_API_KEY`](modules/root.md), [`DEEPSEEK_API_KEY`](modules/root.md), [`ANTHROPIC_API_KEY`](modules/root.md), [`REPOWIKI_MODEL`](modules/root.md), [`REPOWIKI_LANG`](modules/root.md) +6 more · concepts LLM Integration, Incremental Caching, Multi-format Export

Internal links: [`README.md`](modules/root.md) → [`README_CN.md`](modules/root.md), [`pyproject.toml`](modules/root.md) → [`.env.example`](modules/root.md), [`pyproject.toml`](modules/root.md) → [`README.md`](modules/root.md)

[Open the full page](modules/root.md)

### `.github`

> Contains GitHub Actions workflows for CI/CD, demo generation, and package publishing.

3 files · symbols [`lint-and-test`](modules/.github.md), [`rag-eval`](modules/.github.md), [`frontend`](modules/.github.md), [`wheel`](modules/.github.md), [`demo`](modules/.github.md) +1 more · concepts GitHub Actions, CI/CD, PyPI Publishing, Demo Generation

Internal links: [`.github/workflows/ci.yml`](modules/.github.md) → [`.github/workflows/publish.yml`](modules/.github.md), [`.github/workflows/ci.yml`](modules/.github.md) → [`.github/workflows/demo.yml`](modules/.github.md), [`.github/workflows/publish.yml`](modules/.github.md) → [`.github/workflows/ci.yml`](modules/.github.md)

[Open the full page](modules/.github.md)

### `evals`

> Evaluates code documentation retrieval accuracy using fixture repositories and predefined questions.

3 files · symbols [`overall`](modules/evals.md), [`repos`](modules/evals.md), [`boosted`](modules/evals.md), [`repo`](modules/evals.md), [`question`](modules/evals.md) +6 more · concepts Fixture Repositories, Retrieval Accuracy, Question Tiers, Module Documentation

Entry: [`evals/run_eval.py`](modules/evals.md)

Internal links: [`evals/run_eval.py`](modules/evals.md) → [`evals/fixtures/questions.json`](modules/evals.md), [`evals/run_eval.py`](modules/evals.md) → [`evals/baseline.json`](modules/evals.md), `evals/fixtures/modules/*.json` → `evals/fixtures/repos/*`

[Open the full page](modules/evals.md)

### [`repowiki`](modules/root.md)

> Module containing 27 files

Entry: `src/repowiki/__main__.py`, `src/repowiki/server/routers/chat.py`, `src/repowiki/server/routers/scan.py` +1 more

[Open the full page](modules/repowiki.md)
