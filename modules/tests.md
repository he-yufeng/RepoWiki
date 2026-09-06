# tests

> Unit and integration tests for the repowiki codebase

The tests module contains comprehensive test coverage for all major components including the analyzer, cache, chat system, dependency graph, exports, and GitHub integration. Tests verify both functionality and edge cases across the codebase.

## Files

### `test_analyzer_guide.py`

Tests the reading guide generation and PageRank-based file ordering

- `test_reading_guide_ranks_by_pagerank_not_scan_order` (function) - Verifies files are ranked by importance not scan order
- `test_reading_guide_cache_follows_ranking_inputs` (function) - Tests cache invalidation when import dependencies change

### `test_cache.py`

Tests the LLM response cache implementation

- `test_fresh_entry_survives_default_ttl` (function) - Verifies cache entries persist within TTL
- `test_expired_entry_is_deleted` (function) - Tests automatic cleanup of expired entries

### `test_chat_prompt.py`

Tests chat prompt construction and history threading

- `test_chat_prompt_without_history_stays_two_messages` (function) - Verifies basic prompt structure
- `test_history_threads_before_the_question_in_order` (function) - Tests proper history sequencing

### `test_chat_router.py`

Tests FastAPI chat endpoint prompt handling

- `test_chat_router_threads_history_into_prompt` (function) - Verifies chat history is included in API requests

### `test_cross_links.py`

Tests cross-referencing between wiki pages

- `test_known_symbol_mention_becomes_a_link` (function) - Verifies symbol references are linked
- `test_file_path_mentions_become_links` (function) - Tests file reference linking

### `test_github_token.py`

Tests GitHub token handling for private repos

- `test_token_used_for_github_clone` (function) - Verifies token authentication
- `test_token_never_leaks_into_errors` (function) - Tests security of error messages

### `test_graph.py`

Tests dependency graph analysis

- `test_python_relative_imports_resolve_inside_src_package` (function) - Tests Python import resolution
- `test_find_circular_dependencies_detects_mutual_imports` (function) - Verifies cycle detection

### `test_html_export.py`

Tests HTML wiki export

- `test_html_export_writes_a_file_with_the_project_title` (function) - Basic export verification
- `test_html_export_skips_the_write_when_content_is_unchanged` (function) - Tests incremental export

### `test_incremental.py`

Tests incremental wiki regeneration

- `test_first_run_writes_all_pages_and_state` (function) - Initial generation test
- `test_second_run_skips_unchanged_pages` (function) - Incremental optimization test

### `test_lazy_litellm.py`

Tests lazy loading of LLM dependencies

- `test_package_cli_and_analyzer_imports_stay_litellm_free` (function) - Verifies no early LLM imports

### `test_markdown_export.py`

Tests Markdown wiki export

- `test_writes_each_page_and_sidebar` (function) - Basic export test
- `test_readme_includes_nested_children` (function) - Tests sidebar hierarchy

### `test_rag.py`

Tests retrieval-augmented generation (RAG) system

- `test_retrieve_ranks_relevant_file_first` (function) - Tests TF-IDF ranking
- `test_unrelated_query_returns_nothing` (function) - Tests query filtering

### `test_rag_persistence.py`

Tests RAG index persistence and invalidation

- `test_index_round_trip` (function) - Tests save/load cycle
- `test_content_change_invalidates_the_saved_index` (function) - Tests cache invalidation

### `test_repo_map.py`

Tests repository mapping functionality

- `test_map_json_ranks_by_dependency_pagerank` (function) - Tests JSON output format
- `test_map_text_lists_files_and_top_limit` (function) - Tests text output format

### `test_scanner.py`

Tests directory scanning and file filtering

- `test_scan_skips_minified_suffixes` (function) - Tests minified file exclusion
- `test_scan_respects_gitignore_and_repowikiignore` (function) - Tests ignore file handling

### `test_server_static.py`

Tests static file serving

- `test_root_serves_built_frontend` (function) - Tests UI serving

### `test_site_and_serve.py`

Tests site generation and serving

- `test_write_site_loader` (function) - Tests static site generation
- `test_serve_passes_the_target_through` (function) - Tests serve command

### `test_smoke.py`

Basic smoke tests for critical imports

- `test_package_imports` (function) - Basic import test

### `test_symbol_index.py`

Tests symbol index generation

- `test_kind_sections_follow_first_appearance_order` (function) - Tests symbol grouping
- `test_modules_and_symbols_sorted_within_each_kind` (function) - Tests deterministic ordering

## Key Concepts

- **PageRank**: Used to determine file importance based on import relationships
- **Incremental Regeneration**: Tests verify unchanged files skip reprocessing
- **Cache Invalidation**: Multiple tests verify cache keys change when inputs change

## Internal Relationships

- `test_analyzer_guide.py` → `test_cache.py`: Uses Cache class to test analyzer caching behavior
- `test_chat_prompt.py` → `test_chat_router.py`: Shared prompt building logic between CLI and API
- `test_graph.py` → `test_repo_map.py`: Dependency graph powers repository mapping
- `test_rag.py` → `test_rag_persistence.py`: Shared RAG implementation with persistence layer
