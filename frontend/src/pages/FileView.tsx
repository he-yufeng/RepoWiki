import { useEffect, useMemo, useState } from "react";
import { useParams, useLocation, Link } from "react-router-dom";
import type { BundledLanguage, ThemedToken } from "shiki";
import { getFileContent } from "../lib/api";

interface FilePayload {
  path: string;
  language: string;
  content: string;
  lines: number;
  error?: string;
}

// repowiki scanner names that differ from shiki's grammar ids
const LANG_ALIAS: Record<string, string> = {
  shell: "bash",
  "c++": "cpp",
  "c#": "csharp",
  "objective-c": "objective-c",
  plaintext: "text",
  text: "text",
};

function parseHash(hash: string): [number, number] | null {
  const m = /^#L(\d+)(?:-L(\d+))?$/.exec(hash);
  if (!m) return null;
  const start = parseInt(m[1], 10);
  const end = m[2] ? parseInt(m[2], 10) : start;
  return start <= end ? [start, end] : [end, start];
}

export default function FileView() {
  const { id, "*": filePath } = useParams<{ id: string; "*": string }>();
  const { hash } = useLocation();
  const [file, setFile] = useState<FilePayload | null>(null);
  const [lines, setLines] = useState<ThemedToken[][] | null>(null);
  const [notFound, setNotFound] = useState(false);

  const range = useMemo(() => parseHash(hash), [hash]);

  useEffect(() => {
    if (!id || !filePath) return;
    setFile(null);
    setLines(null);
    setNotFound(false);
    getFileContent(id, filePath).then((f: FilePayload) => {
      if (!f || f.error) {
        setNotFound(true);
        return;
      }
      setFile(f);
      // shiki is heavy; load it only when a file page is actually viewed
      void import("shiki").then(({ codeToTokens }) => {
        // scanner languages are close to but not exactly shiki's grammar ids;
        // an unknown one rejects and falls back to plain text below
        const lang = (LANG_ALIAS[f.language] ?? f.language ?? "text") as BundledLanguage;
        codeToTokens(f.content ?? "", { lang, theme: "github-light" })
          .then((res) => setLines(res.tokens))
          .catch(() =>
            codeToTokens(f.content ?? "", { lang: "text", theme: "github-light" }).then(
              (res) => setLines(res.tokens),
            ),
          );
      });
    });
  }, [id, filePath]);

  useEffect(() => {
    if (!lines || !range) return;
    document.getElementById(`L${range[0]}`)?.scrollIntoView({ block: "center" });
  }, [lines, range]);

  if (notFound) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3 text-slate-500">
        <p>File not found in this project: <code className="font-mono text-xs">{filePath}</code></p>
        <Link to={`/project/${id}`} className="text-blue-600 hover:underline text-sm">
          back to wiki
        </Link>
      </div>
    );
  }

  if (!file || !lines) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-500">
        Loading file...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <div className="px-6 py-3 border-b border-slate-200 flex items-center gap-4">
        <Link to={`/project/${id}`} className="text-sm text-slate-500 hover:text-slate-700">
          ← wiki
        </Link>
        <Link to={`/project/${id}/chat`} className="text-sm text-slate-500 hover:text-slate-700">
          chat
        </Link>
        <span className="font-mono text-sm text-slate-800">{file.path}</span>
        <span className="text-xs text-slate-400">
          {file.lines} lines{range ? ` · showing L${range[0]}-L${range[1]}` : ""}
        </span>
      </div>
      <div className="flex-1 overflow-auto">
        <pre className="text-xs font-mono leading-5 py-4 min-w-max">
          {lines.map((tokens, i) => {
            const lineNo = i + 1;
            const inRange = range !== null && lineNo >= range[0] && lineNo <= range[1];
            return (
              <div
                key={lineNo}
                id={`L${lineNo}`}
                className={`flex ${inRange ? "bg-yellow-50" : ""}`}
              >
                <span className="w-12 shrink-0 select-none pr-4 text-right text-slate-300">
                  {lineNo}
                </span>
                <code className="whitespace-pre">
                  {tokens.map((t, j) => (
                    <span key={j} style={{ color: t.color }}>
                      {t.content}
                    </span>
                  ))}
                </code>
              </div>
            );
          })}
        </pre>
      </div>
    </div>
  );
}
