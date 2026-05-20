const BASE = "/api";

function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const apiKey = localStorage.getItem("repowiki_api_key");
  if (apiKey) headers["x-api-key"] = apiKey;
  return headers;
}

export interface ScanRequest {
  path?: string;
  url?: string;
  language?: string;
  model?: string;
  // Optional git ref (e.g. "HEAD~5", "main") for incremental scan. Only
  // honored when `path` is set; GitHub URL scans are always full.
  since?: string;
}

export interface ProjectInfo {
  id: string;
  name: string;
  status: string;
  total_files: number;
  total_lines: number;
  error?: string;
}

export interface WikiStructure {
  project_name: string;
  sidebar: SidebarItem[];
  pages: PageMeta[];
}

export interface SidebarItem {
  title: string;
  page_id: string;
  children?: SidebarItem[];
}

export interface PageMeta {
  id: string;
  title: string;
  order: number;
  parent_id: string;
}

export interface WikiPage {
  id: string;
  title: string;
  content: string;
}

export async function scanProject(req: ScanRequest): Promise<ProjectInfo> {
  const res = await fetch(`${BASE}/scan`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(req),
  });
  return res.json();
}

export function streamScanProgress(
  projectId: string,
  onProgress: (step: string) => void,
  onDone: (status: string) => void,
) {
  const es = new EventSource(`${BASE}/project/${projectId}/status`);
  es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.step) onProgress(data.step);
    if (data.status) {
      onDone(data.status);
      es.close();
    }
    if (data.error) {
      onDone("error");
      es.close();
    }
  };
  es.onerror = () => {
    es.close();
    onDone("error");
  };
  return es;
}

export async function getWiki(projectId: string): Promise<WikiStructure> {
  const res = await fetch(`${BASE}/project/${projectId}/wiki`, { headers: getHeaders() });
  return res.json();
}

export async function getPage(projectId: string, pageId: string): Promise<WikiPage> {
  const res = await fetch(`${BASE}/project/${projectId}/wiki/${pageId}`, { headers: getHeaders() });
  return res.json();
}

export interface FileContent {
  path: string;
  language: string;
  content: string;
  lines: number;
  // Present only when start/end query params were supplied.
  snippet?: string;
  snippet_start?: number;
  highlight_start?: number;
  highlight_end?: number;
  error?: string;
}

export async function getFileContent(
  projectId: string,
  filePath: string,
  opts?: { start?: number; end?: number },
): Promise<FileContent> {
  const qs = new URLSearchParams();
  if (opts?.start) qs.set("start", String(opts.start));
  if (opts?.end) qs.set("end", String(opts.end));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const res = await fetch(
    `${BASE}/project/${projectId}/file/${filePath}${suffix}`,
    { headers: getHeaders() },
  );
  return res.json();
}

export interface FileReference {
  path: string;
  line_start: number;
  line_end: number;
  snippet: string;
}

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

export interface ChatStreamEvent {
  content?: string;
  references?: FileReference[];
  error?: string;
  done?: boolean;
}

export interface StreamChatCallbacks {
  onChunk: (data: ChatStreamEvent) => void;
  onError: (message: string) => void;
  onDone: () => void;
  // Optional progress notification when the underlying fetch fails before
  // any bytes are streamed and we're about to retry. UI can show a small
  // "Reconnecting (N/M)..." indicator.
  onRetry?: (attempt: number, maxAttempts: number) => void;
}

// Retry budget for transient connection failures (DNS hiccups, gateway
// resets). 3 attempts total with backoff 0.5s -> 1.5s -> 3s. We only
// retry the *initial* fetch / handshake -- once bytes start flowing we
// don't double-send and confuse the LLM.
const STREAM_MAX_ATTEMPTS = 3;
const STREAM_BACKOFF_MS = [500, 1500, 3000];

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function streamChat(
  projectId: string,
  question: string,
  history: ChatHistoryItem[],
  callbacks: StreamChatCallbacks,
): AbortController {
  const controller = new AbortController();

  async function attempt(n: number): Promise<{ ok: boolean; res?: Response; err?: Error }> {
    try {
      const res = await fetch(`${BASE}/project/${projectId}/chat`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({ question, history }),
        signal: controller.signal,
      });
      if (!res.ok) {
        return { ok: false, err: new Error(`HTTP ${res.status}: ${res.statusText}`) };
      }
      return { ok: true, res };
    } catch (err) {
      return { ok: false, err: err as Error };
    }
  }

  (async () => {
    let res: Response | undefined;
    let lastErr: Error | undefined;
    for (let i = 0; i < STREAM_MAX_ATTEMPTS; i++) {
      if (i > 0) {
        callbacks.onRetry?.(i + 1, STREAM_MAX_ATTEMPTS);
        await sleep(STREAM_BACKOFF_MS[i - 1] ?? STREAM_BACKOFF_MS[STREAM_BACKOFF_MS.length - 1]);
        if (controller.signal.aborted) {
          callbacks.onDone();
          return;
        }
      }
      const r = await attempt(i);
      if (r.ok) {
        res = r.res!;
        break;
      }
      lastErr = r.err;
      // AbortError means the caller stopped us deliberately -- don't retry.
      if (lastErr?.name === "AbortError") {
        callbacks.onDone();
        return;
      }
    }

    if (!res) {
      callbacks.onError(lastErr?.message || "Network error");
      callbacks.onDone();
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      callbacks.onError("No response body");
      callbacks.onDone();
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let finished = false;
    try {
      while (!finished) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          // The server emits ``: heartbeat\n\n`` lines (SSE comments) when
          // the LLM is slow; skip anything that isn't a real data frame.
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          try {
            const data = JSON.parse(payload) as ChatStreamEvent;
            if (data.error) callbacks.onError(data.error);
            else callbacks.onChunk(data);
            if (data.done) {
              finished = true;
              break;
            }
          } catch (err) {
            callbacks.onError(`Malformed stream chunk: ${(err as Error).message}`);
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        callbacks.onError((err as Error).message || "Stream error");
      }
    } finally {
      callbacks.onDone();
    }
  })();
  return controller;
}
