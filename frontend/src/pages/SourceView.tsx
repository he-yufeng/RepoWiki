import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { codeToHtml } from "shiki";
import { getFileContent, type FileContent } from "../lib/api";

/**
 * Source viewer reached from any path:line citation.
 *
 * We deliberately do the syntax-highlight work in the browser via Shiki so
 * the backend stays simple (no server-side renderer to maintain). The view
 * also lets the user scroll to / highlight a target line range supplied
 * by the citation query string.
 */
export default function SourceView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const path = params.get("path") || "";
  const line = parseInt(params.get("line") || "0", 10) || 0;
  const end = parseInt(params.get("end") || "0", 10) || 0;

  const [file, setFile] = useState<FileContent | null>(null);
  const [html, setHtml] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (!id || !path) {
      setError("Missing path or project id");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await getFileContent(id, path, { start: line, end: end || line });
        if (cancelled) return;
        if (data.error) {
          setError(data.error);
          return;
        }
        setFile(data);
        const lang = mapLanguage(data.language);
        // When the server returned a focused snippet we render that; the
        // alternative (full file) is fine for small files but Shiki gets
        // slow on >5k-line bodies.
        const body = data.snippet ?? data.content ?? "";
        const rendered = await codeToHtml(body, {
          lang,
          theme: "github-light",
        });
        if (!cancelled) setHtml(rendered);
      } catch (e) {
        if (!cancelled) setError((e as Error).message || "Failed to load file");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, path, line, end]);

  // After the HTML lands, scroll the target line into view + decorate it.
  useEffect(() => {
    if (!html || !line) return;
    // Shiki emits one <span class="line"> per line; index relative to the
    // snippet's first line.
    const offset = file?.snippet_start ? file.snippet_start - 1 : 0;
    const target = line - 1 - offset;
    const lineEls = document.querySelectorAll<HTMLElement>(".shiki .line");
    if (target < 0 || target >= lineEls.length) return;
    const lastTarget = end ? end - 1 - offset : target;
    for (let i = target; i <= Math.min(lastTarget, lineEls.length - 1); i++) {
      lineEls[i].style.background = "rgba(250, 240, 137, 0.4)";
      lineEls[i].style.display = "inline-block";
      lineEls[i].style.width = "100%";
    }
    lineEls[target]?.scrollIntoView({ block: "center", behavior: "auto" });
  }, [html, line, end, file]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="flex items-center gap-4 px-6 py-3 bg-white border-b border-slate-200 sticky top-0 z-10">
        <button
          onClick={() => navigate(`/project/${id}`)}
          className="text-slate-500 hover:text-slate-700"
        >
          ← Back to Wiki
        </button>
        <h1 className="text-base font-mono text-slate-800 truncate">{path}</h1>
        {line > 0 && (
          <span className="text-xs text-slate-500">
            line {line}
            {end && end !== line ? `-${end}` : ""}
          </span>
        )}
      </header>

      <main className="flex-1 px-6 py-4 overflow-x-auto">
        {error && (
          <div className="text-red-700 bg-red-50 border border-red-200 rounded p-3 text-sm">
            {error}
          </div>
        )}
        {!error && !html && <div className="text-slate-400 text-sm">Loading…</div>}
        {html && (
          <div
            className="text-sm font-mono leading-relaxed"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        )}
      </main>
    </div>
  );
}

// Shiki's grammar list keys on lowercase short names; we normalise a couple
// of repowiki-side labels that don't match (e.g. our scanner emits
// "javascript" but Shiki prefers "js"). Unknown languages fall back to
// plaintext rather than throwing.
function mapLanguage(repowikiLang: string): string {
  const l = (repowikiLang || "").toLowerCase();
  const map: Record<string, string> = {
    javascript: "js",
    typescript: "ts",
    markdown: "md",
    shell: "bash",
    "c++": "cpp",
    csharp: "cs",
    plaintext: "txt",
    unknown: "txt",
    "": "txt",
  };
  return map[l] ?? l;
}
