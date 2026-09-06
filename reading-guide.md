# Reading Guide

This codebase appears to be a documentation generator for code repositories (RepoWiki) with both backend and frontend components. Start with entry points to understand the overall flow, then examine core data models and processing logic, and finally explore the supporting utilities.

## Step 1: Understand the application entry points (~10 min)

**Files:** `src/repowiki/server/app.py`, `frontend/src/App.tsx`

Look at how the backend server is initialized and routes are defined in app.py, and how the frontend React application is bootstrapped in App.tsx. This gives the high-level structure.

## Step 2: Examine core data models (~15 min)

**Files:** `src/repowiki/core/models.py`

Study the fundamental data structures in models.py that represent the code documentation being generated. This is the foundation of the application's domain.

## Step 3: Understand the wiki generation pipeline (~20 min)

**Files:** `src/repowiki/core/wiki_builder.py`, `src/repowiki/core/scanner.py`, `src/repowiki/core/analyzer.py`

Trace the main documentation generation flow through these files to see how code is scanned, analyzed, and converted to wiki format.

## Step 4: Learn about graph processing (~15 min)

**Files:** `src/repowiki/core/graph.py`

Examine how code relationships are modeled as graphs, which appears to be a key feature of the documentation system.

## Step 5: Review LLM integration (~20 min)

**Files:** `src/repowiki/llm/client.py`, `src/repowiki/llm/prompts.py`, `src/repowiki/core/rag.py`

Understand how the system interacts with language models for documentation generation, including prompt engineering and retrieval-augmented generation.

## Step 6: Explore the frontend API layer (~15 min)

**Files:** `frontend/src/lib/api.ts`, `frontend/src/stores/wiki.ts`

See how the frontend communicates with the backend through the API client and state management for wiki content.

## Step 7: Examine export formats (~10 min)

**Files:** `src/repowiki/export/markdown.py`, `src/repowiki/export/html.py`

Look at how the system outputs documentation in different formats (Markdown and HTML).

## Step 8: Review CLI interface (~10 min)

**Files:** `src/repowiki/cli.py`

Understand the command-line interface for running the documentation generator.

## Tips

- The system appears to use a pipeline architecture - look for how data flows between scanning, analysis, and generation stages
- Pay attention to how the graph structure is used throughout the system for representing code relationships
- The frontend seems relatively lightweight compared to the backend processing logic
- Look for configuration points where users can customize documentation generation
