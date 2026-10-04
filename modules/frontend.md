# frontend

> Provides a React-based web interface for generating and viewing wiki documentation for codebases.

The frontend module is a React application built with Vite and TypeScript that allows users to input a GitHub URL or local path to generate comprehensive wiki documentation. It features a multi-page interface with wiki viewing, interactive chat Q&A, and file source code viewing capabilities. The application uses Zustand for state management, React Router for navigation, and integrates with various AI models for content generation.

## Files

### `package.json`

Defines project dependencies, scripts, and configuration for the frontend application.

- `dependencies` (configuration) - Lists runtime dependencies including React, React Router, Mermaid for diagrams, Shiki for syntax highlighting, and Zustand for state management.
- `devDependencies` (configuration) - Lists development dependencies including Vite, TypeScript, Tailwind CSS, and React plugins.
- `scripts` (configuration) - Defines build and development commands for the application.

### `tsconfig.json`

Configures TypeScript compiler options for the React application.

- `compilerOptions` (configuration) - Sets TypeScript compilation settings including target ES2020, React JSX support, and strict type checking.

### `vite.config.ts`

Configures Vite build tool with React plugin, Tailwind CSS, and proxy settings.

- `defineConfig` (function) - Defines Vite configuration with plugins, server proxy for API calls, and build output directory.

### `App.tsx`

Main application component that sets up React Router and defines application routes.

- `App` (component) - Root component that renders the router and defines routes for Home, WikiView, ChatView, and FileView.

### `index.html`

HTML entry point that mounts the React application to the DOM.

- `root` (element) - The div element where the React application is mounted.

### `src/main.tsx`

Entry point that renders the React application to the DOM.

- `createRoot` (function) - Renders the App component into the root DOM element.

### `src/index.css`

Imports Tailwind CSS styles for the application.

- `@import` (directive) - Imports Tailwind CSS framework for styling.

### `src/lib/api.ts`

Provides API functions for communicating with the backend server.

- `scanProject` (function) - Initiates a project scan by sending a request to the backend.
- `streamScanProgress` (function) - Sets up an EventSource to stream real-time scan progress updates.
- `getWiki` (function) - Fetches the wiki structure for a project.
- `getPage` (function) - Retrieves content for a specific wiki page.
- `getFileContent` (function) - Fetches file content for source code viewing.
- `streamChat` (function) - Streams chat responses from the AI model with real-time updates.

### `src/stores/wiki.ts`

Manages global application state using Zustand with persistence.

- `useWikiStore` (store) - Zustand store that manages project data, wiki content, chat messages, settings, and application state.

### `src/pages/Home.tsx`

Landing page where users input repository URLs to generate wikis.

- `Home` (component) - Component that renders the main input interface and handles project scanning initiation.

### `src/pages/WikiView.tsx`

Displays the generated wiki with sidebar navigation and content.

- `WikiView` (component) - Component that renders the wiki interface with sidebar and content areas.

### `src/pages/ChatView.tsx`

Provides an interactive chat interface for asking questions about the codebase.

- `ChatView` (component) - Component that renders the chat interface with message history and input.

### `src/pages/FileView.tsx`

Displays source code files with syntax highlighting and line navigation.

- `FileView` (component) - Component that renders file content with syntax highlighting and line reference support.

### `src/components/WikiSidebar.tsx`

Renders the navigation sidebar for wiki pages.

- `WikiSidebar` (component) - Component that displays the hierarchical navigation structure of wiki pages.

### `src/components/WikiContent.tsx`

Renders wiki content with Markdown parsing and Mermaid diagram support.

- `WikiContent` (component) - Component that parses and renders wiki content with Markdown formatting and embedded diagrams.
- `splitMermaid` (function) - Splits content into text and Mermaid diagram sections for separate rendering.
- `markdownToHtml` (function) - Converts Markdown syntax to HTML with custom styling.

### `src/components/MermaidDiagram.tsx`

Renders Mermaid diagrams from code blocks.

- `MermaidDiagram` (component) - Component that renders Mermaid diagrams and handles rendering errors.

### `src/components/SettingsModal.tsx`

Provides a modal for configuring API keys and model preferences.

- `SettingsModal` (component) - Modal component for managing application settings including API keys and AI model selection.

## Key Concepts

- **State Management**: Uses Zustand with sessionStorage persistence to manage global application state including project data, wiki content, chat history, and user settings across the application.
- **Real-time Streaming**: Implements EventSource for scan progress updates and streaming chat responses to provide real-time feedback without page refreshes.
- **Dynamic Content Rendering**: Combines Markdown parsing with custom Mermaid diagram rendering and Shiki syntax highlighting to dynamically display rich wiki content and source code.
- **API Integration**: Communicates with a backend server through RESTful APIs for project scanning, wiki generation, file access, and AI-powered chat functionality.
- **Route-based Navigation**: Uses React Router to provide distinct views for different application modes (home, wiki, chat, file view) with parameterized routes for project-specific content.

## Internal Relationships

- `App.tsx` → `src/pages/Home.tsx`: App.tsx imports and routes to Home component for the landing page.
- `App.tsx` → `src/pages/WikiView.tsx`: App.tsx imports and routes to WikiView component for wiki display.
- `App.tsx` → `src/pages/ChatView.tsx`: App.tsx imports and routes to ChatView component for interactive Q&A.
- `App.tsx` → `src/pages/FileView.tsx`: App.tsx imports and routes to FileView component for source code viewing.
- `src/pages/WikiView.tsx` → `src/components/WikiSidebar.tsx`: WikiView imports WikiSidebar for navigation.
- `src/pages/WikiView.tsx` → `src/components/WikiContent.tsx`: WikiView imports WikiContent for rendering wiki pages.
- `src/components/WikiContent.tsx` → `src/components/MermaidDiagram.tsx`: WikiContent imports MermaidDiagram to render embedded diagrams.
- `src/pages/Home.tsx` → `src/components/SettingsModal.tsx`: Home imports SettingsModal for configuration management.
- `src/pages/Home.tsx` → `src/lib/api.ts`: Home imports API functions to initiate project scans.
- `src/pages/WikiView.tsx` → `src/lib/api.ts`: WikiView imports API functions to fetch wiki data.
- `src/pages/ChatView.tsx` → `src/lib/api.ts`: ChatView imports API functions for streaming chat responses.
- `src/pages/FileView.tsx` → `src/lib/api.ts`: FileView imports API functions to fetch file content.
- `src/pages/Home.tsx` → `src/stores/wiki.ts`: Home uses the wiki store to manage scan state and settings.
- `src/pages/WikiView.tsx` → `src/stores/wiki.ts`: WikiView uses the wiki store to manage wiki data and navigation state.
- `src/pages/ChatView.tsx` → `src/stores/wiki.ts`: ChatView uses the wiki store to manage chat messages and history.
- `src/components/SettingsModal.tsx` → `src/stores/wiki.ts`: SettingsModal uses the wiki store to update application settings.
