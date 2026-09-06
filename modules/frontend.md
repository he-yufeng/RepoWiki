# frontend

> React-based web interface for generating and viewing codebase documentation.

A Vite-powered React application that provides a UI for scanning codebases, generating wiki documentation with diagrams, and interactive Q&A features. It includes routing, state management, and API integration with a backend service.

## Files

### `package.json`

Defines project dependencies and scripts

### `tsconfig.json`

TypeScript configuration

### `vite.config.ts`

Vite build configuration with proxy and output settings

- `defineConfig` (function) - Configures Vite with React plugin, Tailwind, and API proxy

### `App.tsx`

Main application router

- `App` (component) - Sets up routes for Home, WikiView, and ChatView

### `index.html`

Entry HTML file

### `MermaidDiagram.tsx`

Renders Mermaid diagrams from code

- `MermaidDiagram` (component) - Converts Mermaid code to SVG diagrams with error handling

### `SettingsModal.tsx`

Displays and updates application settings

- `SettingsModal` (component) - Manages API key, model selection, and language preferences

### `WikiContent.tsx`

Renders wiki content with markdown and diagrams

- `WikiContent` (component) - Processes markdown content with Mermaid diagram support
- `splitMermaid` (function) - Separates Mermaid code blocks from markdown text
- `markdownToHtml` (function) - Converts markdown to styled HTML

### `WikiSidebar.tsx`

Displays navigation sidebar for wiki pages

- `WikiSidebar` (component) - Shows hierarchical navigation of wiki pages with chat button

### `api.ts`

API client for backend communication

- `scanProject` (function) - Initiates codebase scanning
- `streamScanProgress` (function) - Streams scanning progress updates
- `streamChat` (function) - Handles streaming chat responses

### `main.tsx`

Application entry point

- `main` (function) - Renders React app to DOM

### `ChatView.tsx`

Interactive chat interface

- `ChatView` (component) - Manages chat messages and streaming responses

### `Home.tsx`

Landing page with project scanning

- `Home` (component) - Handles project URL input and scan initiation

### `WikiView.tsx`

Main wiki documentation view

- `WikiView` (component) - Coordinates sidebar and content rendering

### `wiki.ts`

Global state management

- `useWikiStore` (store) - Zustand store for application state including project, wiki, and chat data

## Key Concepts

- **State Management**: Uses Zustand for global state including project data, wiki structure, and chat history
- **Markdown Processing**: Converts markdown to HTML with special handling for Mermaid diagrams and code blocks
- **Streaming API**: Handles both progress updates during scanning and chunked responses during chat
- **Routing**: React Router manages navigation between home, wiki, and chat views

## Internal Relationships

- `App.tsx` → `Home.tsx`: Routes to Home component
- `App.tsx` → `WikiView.tsx`: Routes to WikiView component
- `App.tsx` → `ChatView.tsx`: Routes to ChatView component
- `WikiView.tsx` → `WikiSidebar.tsx`: Uses sidebar for navigation
- `WikiView.tsx` → `WikiContent.tsx`: Displays rendered wiki content
- `Home.tsx` → `api.ts`: Uses API functions for project scanning
- `ChatView.tsx` → `wiki.ts`: Manages chat state via store
- `WikiContent.tsx` → `MermaidDiagram.tsx`: Embeds Mermaid diagrams in content
