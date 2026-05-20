import { useState, useRef, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { streamChat, type FileReference } from "../lib/api";
import {
  useWikiStore,
  toHistoryItems,
  type ChatMessage,
} from "../stores/wiki";
import { markdownToHtml } from "../lib/markdown";

// Module-level stable reference so the Zustand selector below doesn't return
// a brand-new array literal on every render when chatHistory[projectId] is
// undefined — that pattern causes Object.is to fail and triggers a render
// loop (React error #185).
const EMPTY_MESSAGES: ChatMessage[] = [];

export default function ChatView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id ?? "";

  const messages = useWikiStore((s) =>
    projectId ? s.chatHistory[projectId] ?? EMPTY_MESSAGES : EMPTY_MESSAGES,
  );
  const addChatMessage = useWikiStore((s) => s.addChatMessage);
  const appendToLastChat = useWikiStore((s) => s.appendToLastChat);
  const setLastChatReferences = useWikiStore((s) => s.setLastChatReferences);
  const setLastChatError = useWikiStore((s) => s.setLastChatError);
  const setLastChatStopped = useWikiStore((s) => s.setLastChatStopped);
  const truncateChatAfter = useWikiStore((s) => s.truncateChatAfter);
  const clearChat = useWikiStore((s) => s.clearChat);

  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [retryStatus, setRetryStatus] = useState<{ attempt: number; total: number } | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);
  const [hasNewBelow, setHasNewBelow] = useState(false);

  // auto-scroll only when the user was already at the bottom -- otherwise
  // keep their reading position and surface a "new content" pill.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (stickToBottomRef.current) {
      el.scrollTop = el.scrollHeight;
      setHasNewBelow(false);
    } else {
      setHasNewBelow(true);
    }
  }, [messages]);

  function onScroll() {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    stickToBottomRef.current = atBottom;
    if (atBottom) setHasNewBelow(false);
  }

  function jumpToBottom() {
    const el = scrollRef.current;
    if (!el) return;
    stickToBottomRef.current = true;
    el.scrollTop = el.scrollHeight;
    setHasNewBelow(false);
  }

  function sendQuestion(question: string) {
    if (!projectId || streaming) return;
    stickToBottomRef.current = true;

    // history we send is everything *before* this turn, so don't include
    // the placeholder we're about to add.
    const history = toHistoryItems(messages);
    addChatMessage(projectId, { role: "user", content: question });
    addChatMessage(projectId, { role: "assistant", content: "" });
    setStreaming(true);
    setRetryStatus(null);

    controllerRef.current = streamChat(projectId, question, history, {
      onChunk: (data) => {
        if (data.references) {
          setLastChatReferences(projectId, data.references);
        }
        if (data.content) {
          appendToLastChat(projectId, data.content);
        }
      },
      onError: (msg) => {
        setLastChatError(projectId, msg);
      },
      onRetry: (attempt, total) => {
        setRetryStatus({ attempt, total });
      },
      onDone: () => {
        setStreaming(false);
        setRetryStatus(null);
        controllerRef.current = null;
      },
    });
  }

  function handleSend() {
    if (!input.trim() || !projectId || streaming) return;
    const question = input.trim();
    setInput("");
    sendQuestion(question);
  }

  function handleCancel() {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setStreaming(false);
    setRetryStatus(null);
    setLastChatStopped(projectId);
  }

  function handleRetry(messageId: string, content: string) {
    if (streaming) return;
    // Roll history back to (and including) the user message we're
    // retrying, then re-send. This makes "retry" act like "edit-and-resend
    // the same prompt" rather than appending a duplicate turn.
    truncateChatAfter(projectId, messageId);
    // Remove the user message itself -- we'll re-add it inside sendQuestion.
    const msgs = useWikiStore.getState().chatHistory[projectId] ?? [];
    if (msgs.length > 0 && msgs[msgs.length - 1].id === messageId) {
      // pop the user message (truncateChatAfter kept it)
      useWikiStore.setState((s) => ({
        chatHistory: {
          ...s.chatHistory,
          [projectId]: (s.chatHistory[projectId] ?? []).slice(0, -1),
        },
      }));
    }
    sendQuestion(content);
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      <header className="flex items-center gap-4 px-6 py-3 bg-white border-b border-slate-200">
        <button
          onClick={() => navigate(`/project/${projectId}`)}
          className="text-slate-500 hover:text-slate-700"
        >
          &larr; Back to Wiki
        </button>
        <h1 className="text-lg font-semibold text-slate-800">
          Ask about this codebase
        </h1>
        {retryStatus && (
          <span className="text-xs text-amber-600">
            Reconnecting ({retryStatus.attempt}/{retryStatus.total})…
          </span>
        )}
        {messages.length > 0 && (
          <button
            onClick={() => clearChat(projectId)}
            className="ml-auto text-xs text-slate-400 hover:text-slate-700"
          >
            Clear chat
          </button>
        )}
      </header>

      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="flex-1 overflow-y-auto px-6 py-4 space-y-4 relative"
      >
        {messages.length === 0 && (
          <div className="text-center text-slate-400 mt-20">
            <p className="text-lg mb-2">Ask anything about the codebase</p>
            <p className="text-sm">
              e.g. &quot;How does the authentication flow work?&quot;
            </p>
            <p className="text-xs mt-4 text-slate-300">
              Enter to send · Shift+Enter for newline
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble
            key={msg.id}
            msg={msg}
            projectId={projectId}
            isStreaming={streaming && i === messages.length - 1}
            onRetry={handleRetry}
          />
        ))}

        {hasNewBelow && (
          <button
            onClick={jumpToBottom}
            className="sticky bottom-2 ml-auto block px-3 py-1 bg-slate-700 text-white text-xs rounded-full shadow hover:bg-slate-800"
          >
            New content ↓
          </button>
        )}
      </div>

      <div className="px-6 py-4 bg-white border-t border-slate-200">
        <div className="max-w-2xl mx-auto flex gap-3 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask a question..."
            rows={1}
            className="flex-1 px-4 py-2.5 rounded-lg border border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none text-sm resize-none max-h-40"
            disabled={streaming}
          />
          {streaming ? (
            <button
              onClick={handleCancel}
              className="px-5 py-2.5 bg-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-300 transition-colors"
            >
              Cancel
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              Send
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface BubbleProps {
  msg: ChatMessage;
  projectId: string;
  isStreaming: boolean;
  onRetry: (messageId: string, content: string) => void;
}

function MessageBubble({ msg, projectId, isStreaming, onRetry }: BubbleProps) {
  const isUser = msg.role === "user";
  // Skip markdown rendering during the stream -- repeatedly re-parsing the
  // whole growing body causes visible reflow / flicker on long answers.
  // Once the stream finishes we render the full body once with markdown.
  const html = useMemo(() => {
    if (isUser || isStreaming) return "";
    return markdownToHtml(msg.content, { projectId });
  }, [isUser, isStreaming, msg.content, projectId]);

  const showCaret = isStreaming && !msg.content;
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(msg.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // clipboard API may be unavailable on insecure contexts; nothing to
      // do beyond suppressing the unhandled rejection.
    }
  }

  return (
    <div className={`max-w-2xl ${isUser ? "ml-auto" : "mr-auto"}`}>
      <div
        className={`relative rounded-lg px-4 py-3 ${
          msg.error
            ? "bg-red-50 border border-red-300 text-red-800"
            : isUser
            ? "bg-blue-600 text-white"
            : "bg-white border border-slate-200 text-slate-700"
        }`}
      >
        {isUser ? (
          <pre className="whitespace-pre-wrap font-sans text-sm pr-8">{msg.content}</pre>
        ) : (
          <>
            {msg.error && (
              <div className="text-sm font-medium mb-1">⚠️ {msg.error}</div>
            )}
            {msg.content && isStreaming ? (
              // Lightweight pass-through while tokens stream in. Mermaid /
              // code-block formatting catches up once `isStreaming` flips.
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                {msg.content}
                <span className="inline-block w-2 h-4 bg-slate-400 align-text-bottom animate-pulse ml-1" />
              </pre>
            ) : (
              msg.content && (
                <div
                  className="prose prose-slate prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: html }}
                />
              )
            )}
            {showCaret && (
              <span className="inline-block w-2 h-4 bg-slate-400 align-text-bottom animate-pulse" />
            )}
            {msg.stopped && (
              <div className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-full bg-slate-100 text-slate-600">
                ⏹ Stopped
              </div>
            )}
            {msg.references && msg.references.length > 0 && (
              <ReferenceList refs={msg.references} projectId={projectId} />
            )}
          </>
        )}

        {/* per-bubble action buttons (always visible but discreet) */}
        {!isStreaming && (
          <div className="absolute top-1.5 right-1.5 flex gap-1">
            {!isUser && msg.content && (
              <button
                onClick={handleCopy}
                title="Copy response"
                className="text-[11px] px-1.5 py-0.5 rounded hover:bg-slate-100 text-slate-500 bg-white/80 border border-slate-200"
              >
                {copied ? "Copied" : "Copy"}
              </button>
            )}
            {isUser && (
              <button
                onClick={() => onRetry(msg.id, msg.content)}
                title="Resend this question"
                className="text-[11px] px-1.5 py-0.5 rounded hover:bg-blue-700 text-white bg-blue-500/80"
              >
                Retry
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ReferenceList({ refs, projectId }: { refs: FileReference[]; projectId: string }) {
  return (
    <details className="mt-3 text-xs border-t border-slate-100 pt-2">
      <summary className="cursor-pointer text-slate-500 select-none">
        {refs.length} source{refs.length === 1 ? "" : "s"}
      </summary>
      <ul className="mt-2 space-y-2">
        {refs.map((r, i) => {
          const href =
            `/project/${encodeURIComponent(projectId)}/source` +
            `?path=${encodeURIComponent(r.path)}` +
            `&line=${r.line_start}` +
            `&end=${r.line_end}`;
          return (
            <li key={i} className="bg-slate-50 rounded p-2">
              <a
                href={href}
                target="_blank"
                rel="noopener"
                className="font-mono text-slate-700 hover:text-blue-700 hover:underline"
              >
                {r.path}:{r.line_start}-{r.line_end}
              </a>
              {r.snippet && (
                <pre className="mt-1 text-[11px] text-slate-500 whitespace-pre-wrap overflow-x-auto max-h-48">
                  {r.snippet}
                </pre>
              )}
            </li>
          );
        })}
      </ul>
    </details>
  );
}
