# Reading Guide

Start by understanding the project's configuration and entry points, then dive into core logic and data models, followed by integration points and utilities. Focus on how components interact rather than memorizing every detail.

## Step 1: Understand Configuration and Entry Points (~10 min)

**Files:** `src/repowiki/config.py`, `src/repowiki/cli.py`, `src/repowiki/server/app.py`

Look for how the application is configured (config.py), the command-line interface structure (cli.py), and the web server entry point (app.py) to grasp how the system starts and what options are available.

## Step 2: Explore Core Data Models (~10 min)

**Files:** `src/repowiki/core/models.py`, `src/repowiki/server/models.py`

Examine the data structures defining the wiki content, caching, and server responses to understand what information the system handles and how it's organized.

## Step 3: Review Core Processing Logic (~15 min)

**Files:** `src/repowiki/core/wiki_builder.py`, `src/repowiki/core/scanner.py`, `src/repowiki/core/analyzer.py`

Focus on how the wiki is built (wiki_builder.py), how code is scanned (scanner.py), and how analysis is performed (analyzer.py) to see the main transformation steps from code to documentation.

## Step 4: Understand AI and Graph Components (~15 min)

**Files:** `src/repowiki/core/rag.py`, `src/repowiki/core/graph.py`, `src/repowiki/llm/client.py`

Look at the RAG implementation (rag.py) for retrieval-augmented generation, graph handling (graph.py) for knowledge representation, and the LLM client (client.py) for AI interactions to see how intelligence is integrated.

## Step 5: Examine Caching and Utilities (~10 min)

**Files:** `src/repowiki/core/cache.py`, `src/repowiki/core/skeleton.py`

Check the caching mechanism (cache.py) for performance and the skeleton generation (skeleton.py) for template structures to understand supporting utilities.

## Step 6: Look at Frontend Integration (~10 min)

**Files:** `frontend/src/lib/api.ts`, `frontend/src/stores/wiki.ts`, `frontend/src/components/MermaidDiagram.tsx`

Review the API client (api.ts) for backend communication, the state management (wiki.ts) for frontend data flow, and component examples (MermaidDiagram.tsx) to see how the UI interacts with the core system.

## Step 7: Explore Data Ingestion and Export (~10 min)

**Files:** `src/repowiki/ingest/local.py`, `src/repowiki/export/markdown.py`, `src/repowiki/export/html.py`

Understand how local data is ingested (local.py) and how wikis are exported to Markdown (markdown.py) and HTML (html.py) to see input/output mechanisms.

## Tips

- Use the CLI (cli.py) to run commands and see outputs in action for better understanding.
- Pay attention to imports in each file to see dependencies and how modules connect.
- Refer to tests for examples of usage and expected behavior.
