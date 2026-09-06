# Symbol Index

54 symbols across 3 modules.

## Function

### [frontend](modules/frontend.md)

- [`defineConfig`](modules/frontend.md) - Configures Vite with React plugin, Tailwind, and API proxy
- [`main`](modules/frontend.md) - Renders React app to DOM
- [`markdownToHtml`](modules/frontend.md) - Converts markdown to styled HTML
- [`scanProject`](modules/frontend.md) - Initiates codebase scanning
- [`splitMermaid`](modules/frontend.md) - Separates Mermaid code blocks from markdown text
- [`streamChat`](modules/frontend.md) - Handles streaming chat responses
- [`streamScanProgress`](modules/frontend.md) - Streams scanning progress updates

### [tests](modules/tests.md)

- [`test_chat_prompt_without_history_stays_two_messages`](modules/tests.md) - Verifies basic prompt structure
- [`test_chat_router_threads_history_into_prompt`](modules/tests.md) - Verifies chat history is included in API requests
- [`test_content_change_invalidates_the_saved_index`](modules/tests.md) - Tests cache invalidation
- [`test_expired_entry_is_deleted`](modules/tests.md) - Tests automatic cleanup of expired entries
- [`test_file_path_mentions_become_links`](modules/tests.md) - Tests file reference linking
- [`test_find_circular_dependencies_detects_mutual_imports`](modules/tests.md) - Verifies cycle detection
- [`test_first_run_writes_all_pages_and_state`](modules/tests.md) - Initial generation test
- [`test_fresh_entry_survives_default_ttl`](modules/tests.md) - Verifies cache entries persist within TTL
- [`test_history_threads_before_the_question_in_order`](modules/tests.md) - Tests proper history sequencing
- [`test_html_export_skips_the_write_when_content_is_unchanged`](modules/tests.md) - Tests incremental export
- [`test_html_export_writes_a_file_with_the_project_title`](modules/tests.md) - Basic export verification
- [`test_index_round_trip`](modules/tests.md) - Tests save/load cycle
- [`test_kind_sections_follow_first_appearance_order`](modules/tests.md) - Tests symbol grouping
- [`test_known_symbol_mention_becomes_a_link`](modules/tests.md) - Verifies symbol references are linked
- [`test_map_json_ranks_by_dependency_pagerank`](modules/tests.md) - Tests JSON output format
- [`test_map_text_lists_files_and_top_limit`](modules/tests.md) - Tests text output format
- [`test_modules_and_symbols_sorted_within_each_kind`](modules/tests.md) - Tests deterministic ordering
- [`test_package_cli_and_analyzer_imports_stay_litellm_free`](modules/tests.md) - Verifies no early LLM imports
- [`test_package_imports`](modules/tests.md) - Basic import test
- [`test_python_relative_imports_resolve_inside_src_package`](modules/tests.md) - Tests Python import resolution
- [`test_reading_guide_cache_follows_ranking_inputs`](modules/tests.md) - Tests cache invalidation when import dependencies change
- [`test_reading_guide_ranks_by_pagerank_not_scan_order`](modules/tests.md) - Verifies files are ranked by importance not scan order
- [`test_readme_includes_nested_children`](modules/tests.md) - Tests sidebar hierarchy
- [`test_retrieve_ranks_relevant_file_first`](modules/tests.md) - Tests TF-IDF ranking
- [`test_root_serves_built_frontend`](modules/tests.md) - Tests UI serving
- [`test_scan_respects_gitignore_and_repowikiignore`](modules/tests.md) - Tests ignore file handling
- [`test_scan_skips_minified_suffixes`](modules/tests.md) - Tests minified file exclusion
- [`test_second_run_skips_unchanged_pages`](modules/tests.md) - Incremental optimization test
- [`test_serve_passes_the_target_through`](modules/tests.md) - Tests serve command
- [`test_token_never_leaks_into_errors`](modules/tests.md) - Tests security of error messages
- [`test_token_used_for_github_clone`](modules/tests.md) - Verifies token authentication
- [`test_unrelated_query_returns_nothing`](modules/tests.md) - Tests query filtering
- [`test_write_site_loader`](modules/tests.md) - Tests static site generation
- [`test_writes_each_page_and_sidebar`](modules/tests.md) - Basic export test

## Component

### [frontend](modules/frontend.md)

- [`App`](modules/frontend.md) - Sets up routes for Home, WikiView, and ChatView
- [`ChatView`](modules/frontend.md) - Manages chat messages and streaming responses
- [`Home`](modules/frontend.md) - Handles project URL input and scan initiation
- [`MermaidDiagram`](modules/frontend.md) - Converts Mermaid code to SVG diagrams with error handling
- [`SettingsModal`](modules/frontend.md) - Manages API key, model selection, and language preferences
- [`WikiContent`](modules/frontend.md) - Processes markdown content with Mermaid diagram support
- [`WikiSidebar`](modules/frontend.md) - Shows hierarchical navigation of wiki pages with chat button
- [`WikiView`](modules/frontend.md) - Coordinates sidebar and content rendering

## Store

### [frontend](modules/frontend.md)

- [`useWikiStore`](modules/frontend.md) - Zustand store for application state including project, wiki, and chat data

## Job

### [.github](modules/.github.md)

- [`frontend`](modules/.github.md) - Builds the frontend using Node.js
- [`lint-and-test`](modules/.github.md) - Runs Ruff linter and pytest across multiple Python/OS versions
- [`publish`](modules/.github.md) - Builds frontend, creates Python package, verifies assets, and publishes to PyPI
- [`wheel`](modules/.github.md) - Verifies the built wheel includes frontend assets
