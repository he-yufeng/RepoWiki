# Reading Guide

Start by understanding the project's purpose and entry points, then explore core data models and workflows, followed by key processing logic, and finally the frontend and utilities. Focus on how components interact.

## Step 1: Understand Project Setup and Entry Points (~10 min)

**Files:** [`src/repowiki/config.py`](modules/repowiki.md), [`src/repowiki/cli.py`](modules/repowiki.md), [`src/repowiki/server/app.py`](modules/repowiki.md)

Look for configuration settings, CLI command structure, and web server entry points to grasp how the tool is configured and launched.

## Step 2: Explore Core Data Models (~10 min)

**Files:** [`src/repowiki/core/models.py`](modules/repowiki.md), [`src/repowiki/server/models.py`](modules/repowiki.md)

Identify the main data structures used throughout the application, such as wiki pages, code entities, and API request/response models.

## Step 3: Review Code Scanning and Analysis (~15 min)

**Files:** [`src/repowiki/core/scanner.py`](modules/repowiki.md), [`src/repowiki/core/analyzer.py`](modules/repowiki.md)

Understand how the codebase scans and analyzes source files to extract information for wiki generation.

## Step 4: Examine Wiki Generation Logic (~15 min)

**Files:** [`src/repowiki/core/wiki_builder.py`](modules/repowiki.md), [`src/repowiki/core/skeleton.py`](modules/repowiki.md)

Look at how the wiki content is structured and built, including the creation of page skeletons and content assembly.

## Step 5: Study LLM Integration and RAG (~15 min)

**Files:** [`src/repowiki/llm/client.py`](modules/repowiki.md), [`src/repowiki/core/rag.py`](modules/repowiki.md)

Focus on how LLMs are called and how retrieval-augmented generation is used to enhance documentation.

## Step 6: Inspect Graph and Caching Mechanisms (~10 min)

**Files:** [`src/repowiki/core/graph.py`](modules/repowiki.md), [`src/repowiki/core/cache.py`](modules/repowiki.md)

Understand the graph structure for code relationships and caching strategies to optimize performance.

## Step 7: Review Frontend Integration (~10 min)

**Files:** `frontend/src/lib/api.ts`, `frontend/src/stores/wiki.ts`, `frontend/src/components/MermaidDiagram.tsx`

See how the frontend interacts with the backend API, manages state, and displays diagrams.

## Step 8: Check Export and Ingest Modules (~10 min)

**Files:** [`src/repowiki/export/markdown.py`](modules/repowiki.md), [`src/repowiki/export/html.py`](modules/repowiki.md), [`src/repowiki/ingest/local.py`](modules/repowiki.md)

Look at how wikis are exported to different formats and how local codebases are ingested.

## Tips

- Pay attention to how data flows from scanning to wiki generation.
- Note the use of caching to avoid redundant LLM calls.
- Check the frontend components for visualization of code relationships.
