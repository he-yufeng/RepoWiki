import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { streamChat } from "../lib/api";
import { useWikiStore } from "../stores/wiki";

export default function ChatView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { chatMessages, addChatMessage, appendToLastChat } = useWikiStore();
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  function handleSend() {
    if (!input.trim() || !id || streaming) return;
    const question = input.trim();
    setInput("");
    addChatMessage({ role: "user", content: question });
    addChatMessage({ role: "assistant", content: "" });
    setStreaming(true);

    streamChat(
      id,
      question,
      (data) => {
        if (data.content) appendToLastChat(data.content);
      },
      () => setStreaming(false),
    );
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* header */}
      <header className="flex items-center gap-4 px-6 py-3 bg-white border-b border-slate-200">
        <button
          onClick={() => navigate(`/project/${id}`)}
          className="text-slate-500 hover:text-slate-700"
        >
          &larr; Back to Wiki
        </button>
        <h1 className="text-lg font-semibold text-slate-800">Ask about this codebase</h1>
      </header>

      {/* messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {chatMessages.length === 0 && (
          <div className="text-center text-slate-400 mt-20">
            <p className="text-lg mb-2">Ask anything about the codebase</p>
            <p className="text-sm">e.g. "How does the authentication flow work?"</p>
          </div>
        )}
        {chatMessages.map((msg, i) => (
          <div
            key={i}
            className={`max-w-2xl ${msg.role === "user" ? "ml-auto" : "mr-auto"}`}
          >
            <div
              className={`rounded-lg px-4 py-3 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-slate-200 text-slate-700"
              }`}
            >
              <pre className="whitespace-pre-wrap font-sans text-sm">{msg.content}</pre>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* input */}
      <div className="px-6 py-4 bg-white border-t border-slate-200">
        <div className="max-w-2xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask a question..."
            className="flex-1 px-4 py-2.5 rounded-lg border border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none text-sm"
            disabled={streaming}
          />
          <button
            onClick={handleSend}
            disabled={streaming || !input.trim()}
            className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
