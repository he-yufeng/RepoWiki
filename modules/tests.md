# tests

> Unit tests for the repowiki codebase covering all major components.

Comprehensive test suite verifying the functionality of repowiki's core modules including code analysis, caching, chat features, configuration, exports, and server operations. Tests use pytest fixtures and temporary directories to isolate test cases.

## Files

### `tests/test_analyzer_guide.py`

Tests the reading guide generation and analyzer behavior

- `test_reading_guide_ranks_by_pagerank_not_scan_order` (function) - Verifies reading guide uses PageRank for file ordering
- `test_analyzer_passes_configured_max_tokens` (function) - Tests analyzer respects token limits

### `tests/test_cache.py`

Tests the LLM response cache functionality

- `test_fresh_entry_survives_default_ttl` (function) - Tests cache entry persistence
- `test_module_analysis_reuses_cache_on_second_run` (function) - Verifies cache reuse for module analysis

### `tests/test_chat_prompt.py`

Tests chat prompt building with history threading

- `test_chat_prompt_without_history_stays_two_messages` (function) - Tests basic prompt structure
- `test_history_threads_before_the_question_in_order` (function) - Tests history integration in prompts

### `tests/test_chat_router.py`

Tests FastAPI chat router endpoints

- `test_chat_router_threads_history_into_prompt` (function) - Tests chat endpoint with conversation history

### `tests/test_config.py`

Tests configuration model resolution and vendor endpoints

- `test_mimo_alias_resolves` (function) - Tests model alias resolution
- `test_vendor_aliases_get_endpoints` (function) - Tests vendor-specific API endpoints

### `tests/test_cross_links.py`

Tests cross-reference linking between wiki pages

- `test_known_symbol_mention_becomes_a_link` (function) - Tests symbol mention linking
- `test_html_export_turns_page_links_into_show_page_calls` (function) - Tests HTML link conversion

### `tests/test_diff.py`

Tests diff functionality for changed file analysis

- `test_diff_files_parses_modified_added_deleted` (function) - Tests diff file parsing
- `test_report_ranks_changed_files_by_pagerank_and_blast_radius` (function) - Tests ranking of changed files

### `tests/test_github_token.py`

Tests GitHub token handling for private repositories

- `test_token_used_for_github_clone` (function) - Tests token authentication for GitHub
- `test_token_never_leaks_into_errors` (function) - Tests token security in error messages

### `tests/test_graph.py`

Tests dependency graph analysis and cycle detection

- `test_find_circular_dependencies_detects_mutual_imports` (function) - Tests circular dependency detection
- `test_entry_points_require_outgoing_imports` (function) - Tests entry point identification

### `tests/test_html_export.py`

Tests HTML export functionality

- `test_html_export_writes_a_file_with_the_project_title` (function) - Tests basic HTML export
- `test_html_export_skips_the_write_when_content_is_unchanged` (function) - Tests incremental HTML export

### `tests/test_incremental.py`

Tests incremental regeneration of wiki pages

- `test_first_run_writes_all_pages_and_state` (function) - Tests initial full generation
- `test_single_file_change_regenerates_only_its_module_page` (function) - Tests targeted regeneration

### `tests/test_knowledge_cards.py`

Tests knowledge cards generation for module overview

- `test_cards_page_lists_one_card_per_module` (function) - Tests card generation per module
- `test_card_shows_the_entry_file_from_the_dependency_graph` (function) - Tests entry file display in cards

### `tests/test_lazy_litellm.py`

Tests lazy loading of LLM dependencies

- `test_package_cli_and_analyzer_imports_stay_litellm_free` (function) - Tests lazy import avoidance
- `test_llm_client_construction_imports_litellm` (function) - Tests on-demand LLM import

### `tests/test_llm_retry.py`

Tests LLM client retry logic for transient failures

- `test_transient_error_retries_until_success` (function) - Tests retry on transient errors
- `test_non_transient_error_is_not_retried` (function) - Tests no retry on fatal errors

### `tests/test_markdown_export.py`

Tests Markdown export with README generation

- `test_writes_each_page_and_sidebar` (function) - Tests basic Markdown export
- `test_writes_readme_landing_page_with_overview_and_contents` (function) - Tests README generation

### `tests/test_rag.py`

Tests TF-IDF retrieval for chat functionality

- `test_retrieve_ranks_relevant_file_first` (function) - Tests retrieval ranking
- `test_module_boost_surfaces_zero_overlap_file` (function) - Tests module-based boosting

### `tests/test_rag_eval.py`

Tests RAG evaluation suite against baseline

- `test_fixture_suite_holds_baseline` (function) - Tests RAG performance against baseline

### `tests/test_rag_persistence.py`

Tests RAG index persistence and invalidation

- `test_index_round_trip` (function) - Tests index serialization
- `test_content_change_invalidates_the_saved_index` (function) - Tests index invalidation

### `tests/test_repo_map.py`

Tests repository mapping without LLM calls

- `test_map_json_ranks_by_dependency_pagerank` (function) - Tests JSON map output with PageRank
- `test_map_text_lists_files_and_top_limit` (function) - Tests text map output

### `tests/test_scan_report.py`

Tests scan coverage reporting

- `test_report_counts_oversized_files_with_example_paths` (function) - Tests oversized file reporting
- `test_overview_page_flags_partial_coverage` (function) - Tests coverage warnings in overview

### `tests/test_scanner.py`

Tests directory scanning and file filtering

- `test_scan_skips_minified_suffixes` (function) - Tests minified file filtering
- `test_scan_respects_gitignore_and_repowikiignore` (function) - Tests ignore file handling

### `tests/test_server_static.py`

Tests static file serving and fallback behavior

- `test_root_serves_built_frontend` (function) - Tests frontend serving
- `test_client_side_route_falls_back_to_app_shell` (function) - Tests SPA fallback routing

### `tests/test_site_and_serve.py`

Tests serve command and site generation

- `test_write_site_loader` (function) - Tests site loader generation
- `test_serve_passes_the_target_through` (function) - Tests serve command target passing

### `tests/test_skeleton.py`

Tests symbol skeleton extraction for oversized files

- `test_skeleton_extracts_module_doc_classes_and_functions` (function) - Tests Python skeleton extraction
- `test_context_for_file_prefers_skeleton_for_big_python` (function) - Tests skeleton preference over truncation

### `tests/test_smoke.py`

Basic smoke tests for import verification

- `test_package_imports` (function) - Tests basic package import

### `tests/test_symbol_index.py`

Tests symbol index page generation

- `test_kind_sections_follow_first_appearance_order` (function) - Tests symbol grouping by kind
- `test_entries_link_to_owning_module_and_keep_descriptions` (function) - Tests symbol linking and descriptions

### `tests/test_scan_wiki_routers.py`

Tests scan and wiki API routers

- `test_scan_registers_project_and_background_task_runs` (function) - Tests project registration
- `test_wiki_returns_sidebar_and_pages` (function) - Tests wiki endpoint responses

## Key Concepts

- **Test Isolation**: Tests use pytest fixtures and temporary directories to ensure isolation between test cases
- **LLM Mocking**: Most tests use stub LLM implementations to avoid real API calls and control responses
- **Incremental Testing**: Multiple tests verify incremental regeneration behavior to ensure unchanged content is skipped
- **Cache Validation**: Tests verify cache behavior including TTL, invalidation, and reuse
- **Export Formats**: Tests cover multiple export formats including HTML, Markdown, and site generation
- **API Endpoints**: Router tests verify FastAPI endpoint behavior including error handling and response formats

## Internal Relationships

- `tests/test_analyzer_guide.py` → `repowiki/core/analyzer.py`: Tests the analyzer module's reading guide generation
- `tests/test_cache.py` → `repowiki/core/cache.py`: Tests the LLM cache implementation
- `tests/test_chat_prompt.py` → `repowiki/llm/prompts.py`: Tests chat prompt building utilities
- `tests/test_chat_router.py` → `repowiki/server/app.py`: Tests FastAPI chat endpoints
- `tests/test_config.py` → `repowiki/config.py`: Tests configuration model resolution
- `tests/test_graph.py` → `repowiki/core/graph.py`: Tests dependency graph analysis
- `tests/test_rag.py` → `repowiki/core/rag.py`: Tests RAG retrieval functionality
- `tests/test_scanner.py` → `repowiki/core/scanner.py`: Tests directory scanning implementation
