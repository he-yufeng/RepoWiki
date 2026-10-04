# frontend

> Provides a React-based web interface for generating and viewing wiki documentation for codebases.

The frontend module is a single-page application built with React, TypeScript, and Vite that allows users to scan codebases (via GitHub URLs or local paths), view generated wiki documentation with interactive diagrams, chat with an AI assistant about the codebase, and browse source files with syntax highlighting. It communicates with a backend API to handle scanning, wiki generation, and chat functionality.

## Files

### `package.json`

Defines project metadata, dependencies, and npm scripts for the frontend application.

- `dependencies` (configuration) - Lists runtime dependencies including React, React Router, Mermaid for diagrams, Shiki for syntax highlighting, and Zustand for state management.
- `devDependencies` (configuration) - Lists development dependencies including Vite, TypeScript, Tailwind CSS, and related plugins.
- `scripts` (configuration) - Defines npm scripts for development (dev), building (build), and previewing (preview) the application.

### `tsconfig.json`

Configures TypeScript compiler options for the project.

- `compilerOptions` (configuration) - Sets TypeScript options like target (ES2020), module resolution (bundler), JSX (react-jsx), and strict type checking.

### `vite.config.ts`

Configures Vite build tool with plugins, server proxy, and build output directory.

- `defineConfig` (function) - Defines Vite configuration with React plugin, Tailwind CSS plugin, and server proxy to backend API.
- `server.proxy` (configuration) - Proxies API requests to the backend server running on localhost:8000.
- `build.outDir` (configuration) - Specifies the output directory for built files (../src/repowiki/server/static).

### `src/App.tsx`

Root component that sets up React Router with routes for home, wiki view, chat, and file view.

- `App` (component) - Main application component that renders BrowserRouter and defines routes for Home, WikiView, ChatView, and FileView.
- `Routes` (component) - Defines route paths and their corresponding components.

### `index.html`

HTML entry point that mounts the React application to the DOM.

- `root` (element) - Div element where the React app is mounted.

### `src/components/MermaidDiagram.tsx`

Renders Mermaid diagrams from markdown code blocks.

- `MermaidDiagram` (component) - Component that takes Mermaid code as input, renders it to SVG using the Mermaid library, and displays errors if rendering fails.
- `mermaid.initialize` (function) - Initializes Mermaid with configuration to not start rendering automatically.
- `mermaid.render` (function) - Asynchronously renders Mermaid code to SVG.

### `src/components/SettingsModal.tsx`

Modal dialog for configuring API key, model, and language settings.

- `SettingsModal` (component) - Displays form inputs for API key, model selection, and language selection, with changes persisted to the Zustand store and localStorage.
- `useWikiStore` (hook) - Accesses and updates settings from the global state store.

### `src/components/WikiContent.tsx`

Renders wiki page content by converting markdown to HTML and handling Mermaid diagrams.

- `WikiContent` (component) - Component that splits content into text and Mermaid parts, renders Mermaid diagrams separately, and converts markdown text to HTML with Tailwind CSS styling.
- `splitMermaid` (function) - Splits markdown content into an array of text and Mermaid code blocks using regex.
- `markdownToHtml` (function) - Converts markdown text to HTML with support for code blocks, headings, blockquotes, bold, inline code, links, and lists.

### `src/components/WikiSidebar.tsx`

Displays the wiki navigation sidebar with project name, page hierarchy, and chat button.

- `WikiSidebar` (component) - Renders a collapsible sidebar with project name, hierarchical page navigation, and a button to open the chat view.
- `SidebarItem` (interface) - Defines the structure of sidebar items including title, page_id, and optional children for nested pages.

### `src/lib/api.ts`

Provides functions to interact with the backend API for scanning, wiki data, and chat.

- `scanProject` (function) - Initiates a codebase scan by sending a POST request to /api/scan with project details.
- `streamScanProgress` (function) - Sets up an EventSource to stream scan progress updates from the backend.
- `getWiki` (function) - Fetches the wiki structure (sidebar and pages) for a project.
- `getPage` (function) - Fetches the content of a specific wiki page by ID.
- `getFileContent` (function) - Fetches the content and metadata of a source file from the project.
- `streamChat` (function) - Streams chat responses from the backend using Server-Sent Events (SSE).
- `getHeaders` (function) - Returns HTTP headers including the API key from localStorage for authenticated requests.

### `src/main.tsx`

Entry point that renders the React application to the DOM.

- `createRoot` (function) - Creates a React root and renders the App component inside StrictMode.

### `src/pages/ChatView.tsx`

Page component for interactive Q&A chat about the codebase.

- `ChatView` (component) - Displays chat messages, handles user input, streams AI responses, and shows source code references.
- `streamChat` (function) - Initiates a chat stream with the backend, processing response chunks and updating the UI in real-time.

### `src/pages/FileView.tsx`

Page component for viewing source files with syntax highlighting and line number navigation.

- `FileView` (component) - Fetches and displays a source file with syntax highlighting using Shiki, supports line highlighting via URL hash.
- `parseHash` (function) - Parses URL hash (e.g., #L10-L20) to extract line range for highlighting.
- `LANG_ALIAS` (object) - Maps language names from the scanner to Shiki grammar IDs for syntax highlighting.

### `src/pages/Home.tsx`

Landing page for entering codebase URLs and initiating wiki generation.

- `Home` (component) - Displays project description, URL input field, scan progress, and settings modal.
- `handleScan` (function) - Handles form submission to start scanning a codebase, updates progress, and navigates to wiki view on completion.

### `src/pages/WikiView.tsx`

Main wiki page that displays the sidebar and content of the selected page.

- `WikiView` (component) - Fetches wiki structure and page content, renders WikiSidebar and WikiContent components.
- `useEffect` (hook) - Used to load wiki structure and page content when the project ID or current page ID changes.

### `src/stores/wiki.ts`

Zustand store for managing global state including project data, wiki structure, chat messages, and settings.

- `useWikiStore` (store) - Zustand store with persisted state for project ID, project info, wiki data, current page, scan progress, chat messages, loading states, errors, and settings.
- `persist` (middleware) - Persists parts of the store (projectId and settings) to sessionStorage.

### `src/vite-env.d.ts`

Provides TypeScript type definitions for Vite-specific modules.

- `reference types` (directive) - References Vite client types for module resolution.

## Key Concepts

- **React Router**: Handles client-side routing for the SPA, enabling navigation between home, wiki, chat, and file views without page reloads.
- **Zustand Store**: Manages global application state including project data, wiki structure, chat history, and user settings with persistence to sessionStorage.
- **API Integration**: Communicates with a backend API via fetch and EventSource for scanning codebases, fetching wiki data, and streaming chat responses.
- **Markdown Rendering**: Converts markdown content to HTML with custom styling and extracts Mermaid diagrams for separate rendering with interactive SVG output.
- **Syntax Highlighting**: Uses Shiki to tokenize and highlight source code in file views, with support for multiple languages and line number navigation.
- **Real-time Streaming**: Implements Server-Sent Events (SSE) for real-time progress updates during scanning and chunked responses during chat interactions.

## Internal Relationships

- `src/App.tsx` → `src/pages/Home.tsx`: App.tsx imports and renders Home component as the root route (/).
- `src/App.tsx` → `src/pages/WikiView.tsx`: App.tsx imports and renders WikiView component for project wiki pages (/project/:id).
- `src/App.tsx` → `src/pages/ChatView.tsx`: App.tsx imports and renders ChatView component for project chat (/project/:id/chat).
- `src/App.tsx` → `src/pages/FileView.tsx`: App.tsx imports and renders FileView component for viewing source files (/project/:id/file/*).
- `src/pages/WikiView.tsx` → `src/components/WikiSidebar.tsx`: WikiView imports and uses WikiSidebar for navigation.
- `src/pages/WikiView.tsx` → `src/components/WikiContent.tsx`: WikiView imports and uses WikiContent to render page content.
- `src/components/WikiContent.tsx` → `src/components/MermaidDiagram.tsx`: WikiContent imports and renders MermaidDiagram for Mermaid code blocks.
- `src/pages/Home.tsx` → `src/components/SettingsModal.tsx`: Home imports and conditionally renders SettingsModal for configuration.
- `src/pages/Home.tsx` → `src/lib/api.ts`: Home uses functions from api.ts to scan projects and stream progress.
- `src/pages/WikiView.tsx` → `src/lib/api.ts`: WikiView uses functions from api.ts to fetch wiki structure and page content.
- `src/pages/ChatView.tsx` → `src/lib/api.ts`: ChatView uses streamChat from api.ts to interact with the chat API.
- `src/pages/FileView.tsx` → `src/lib/api.ts`: FileView uses getFileContent from api.ts to fetch file data.
- `src/pages/Home.tsx` → `src/stores/wiki.ts`: Home uses useWikiStore to manage scan state, progress, and settings.
- `src/pages/WikiView.tsx` → `src/stores/wiki.ts`: WikiView uses useWikiStore to access wiki data and current page state.
- `src/pages/ChatView.tsx` → `src/stores/wiki.ts`: ChatView uses useWikiStore to manage chat messages and references.
- `src/components/SettingsModal.tsx` → `src/stores/wiki.ts`: SettingsModal uses useWikiStore to update and persist settings.
