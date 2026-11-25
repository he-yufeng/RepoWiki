import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getSymbols } from "../lib/api";
import type { SymbolEntry } from "../lib/api";
import { useWikiStore } from "../stores/wiki";

export default function SymbolsView() {
  const { id } = useParams<{ id: string }>();
  const [symbols, setSymbols] = useState<SymbolEntry[] | null>(null);
  const [projectName, setProjectName] = useState("");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("all");
  const navigate = useNavigate();
  const setCurrentPage = useWikiStore((s) => s.setCurrentPage);

  useEffect(() => {
    if (!id) return;
    getSymbols(id).then((r) => {
      if (!r || r.error) setError(r?.error ?? "failed to load symbols");
      else {
        setSymbols(r.symbols);
        setProjectName(r.project_name);
      }
    });
  }, [id]);

  const kinds = useMemo(
    () => Array.from(new Set((symbols ?? []).map((symbol) => symbol.kind))),
    [symbols],
  );
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (symbols ?? []).filter(
      (symbol) =>
        (kind === "all" || symbol.kind === kind) &&
        (!needle ||
          `${symbol.name} ${symbol.module} ${symbol.description}`.toLowerCase().includes(needle)),
    );
  }, [symbols, query, kind]);

  const openModule = (pageId: string) => {
    setCurrentPage(pageId);
    navigate(`/project/${id}`);
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <div className="px-6 py-3 border-b border-slate-200 flex items-center gap-4">
        <Link to={`/project/${id}`} className="text-sm text-slate-500 hover:text-slate-700">
          ← wiki
        </Link>
        <Link to={`/project/${id}/cards`} className="text-sm text-slate-500 hover:text-slate-700">
          knowledge cards
        </Link>
        <span className="text-sm font-medium text-slate-800">Symbol Index</span>
        {symbols && (
          <span className="text-xs text-slate-400">
            {projectName} · {filtered.length} of {symbols.length} symbols
          </span>
        )}
      </div>

      <div className="flex-1 overflow-auto px-6 py-4">
        {error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : !symbols ? (
          <p className="text-sm text-slate-400 animate-pulse">Loading symbols...</p>
        ) : (
          <>
            <div className="mb-4 flex flex-col gap-2 sm:flex-row">
              <input
                type="search"
                aria-label="Search symbols"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search name, module, or description"
                className="w-full max-w-xl rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
              <select
                aria-label="Filter by kind"
                value={kind}
                onChange={(event) => setKind(event.target.value)}
                className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
              >
                <option value="all">All kinds</option>
                {kinds.map((entryKind) => (
                  <option key={entryKind} value={entryKind}>
                    {entryKind}
                  </option>
                ))}
              </select>
            </div>

            {symbols.length === 0 ? (
              <p className="text-sm text-slate-500">
                No symbols: the wiki analysis produced no documented symbols.
              </p>
            ) : filtered.length === 0 ? (
              <p className="text-sm text-slate-500">No symbols match these filters.</p>
            ) : (
              <div className="space-y-2">
                {filtered.map((symbol) => (
                  <button
                    key={`${symbol.kind}:${symbol.module}:${symbol.name}`}
                    onClick={() => openModule(symbol.page_id)}
                    className="w-full rounded-lg border border-slate-200 px-4 py-3 text-left hover:border-slate-300 hover:shadow-sm transition"
                  >
                    <span className="flex flex-wrap items-center gap-2">
                      <code className="font-mono text-sm font-semibold text-slate-800">
                        {symbol.name}
                      </code>
                      <span className="text-[10px] font-medium uppercase tracking-wide text-slate-600 bg-slate-100 rounded px-1.5 py-0.5">
                        {symbol.kind}
                      </span>
                      <span className="font-mono text-xs text-blue-600">{symbol.module}</span>
                    </span>
                    {symbol.description && (
                      <span className="mt-1 block text-sm text-slate-600">
                        {symbol.description}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
