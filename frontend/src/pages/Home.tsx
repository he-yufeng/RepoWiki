import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { scanProject, streamScanProgress, getWiki } from "../lib/api";
import { useWikiStore } from "../stores/wiki";
import SettingsModal from "../components/SettingsModal";

export default function Home() {
  const [url, setUrl] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const { loading, setLoading, scanProgress, addProgress, setProjectId, setProject, setWiki, setError, reset, settings } = useWikiStore();
  const navigate = useNavigate();

  async function handleScan() {
    if (!url.trim()) return;
    reset();
    setLoading(true);

    // save API key to localStorage for header injection
    if (settings.apiKey) {
      localStorage.setItem("repowiki_api_key", settings.apiKey);
    }

    try {
      const info = await scanProject({
        url: url.trim(),
        language: settings.language,
        model: settings.model || undefined,
      });
      setProjectId(info.id);
      setProject(info);

      // stream progress
      streamScanProgress(
        info.id,
        (step) => addProgress(step),
        async (status) => {
          if (status === "done") {
            const wiki = await getWiki(info.id);
            setWiki(wiki);
            setLoading(false);
            navigate(`/project/${info.id}`);
          } else {
            setError("Scan failed");
            setLoading(false);
          }
        },
      );
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex flex-col">
      {/* header */}
      <header className="flex items-center justify-between px-8 py-4">
        <h1 className="text-2xl font-bold text-slate-800">
          <span className="text-blue-600">Repo</span>Wiki
        </h1>
        <button
          onClick={() => setShowSettings(true)}
          className="text-slate-500 hover:text-slate-700 text-sm"
        >
          Settings
        </button>
      </header>

      {/* main content */}
      <main className="flex-1 flex flex-col items-center justify-center px-4">
        <div className="max-w-2xl w-full text-center mb-12">
          <h2 className="text-4xl font-bold text-slate-900 mb-4">
            Understand any codebase
          </h2>
          <p className="text-lg text-slate-600">
            Generate comprehensive wiki documentation with architecture diagrams,
            reading guides, and interactive Q&A.
          </p>
        </div>

        <div className="max-w-xl w-full">
          <div className="flex gap-3">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleScan()}
              placeholder="Paste a GitHub URL or local path..."
              className="flex-1 px-4 py-3 rounded-lg border border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none text-slate-700"
              disabled={loading}
            />
            <button
              onClick={handleScan}
              disabled={loading || !url.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Scanning..." : "Generate Wiki"}
            </button>
          </div>

          {/* progress display */}
          {scanProgress.length > 0 && (
            <div className="mt-6 bg-white rounded-lg border border-slate-200 p-4 max-h-48 overflow-y-auto">
              {scanProgress.map((step, i) => (
                <div key={i} className="text-sm text-slate-600 py-1 flex items-center gap-2">
                  <span className="text-green-500">&#10003;</span> {step}
                </div>
              ))}
              {loading && (
                <div className="text-sm text-blue-600 py-1 animate-pulse">Processing...</div>
              )}
            </div>
          )}
        </div>

        {/* features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mt-16">
          {[
            { title: "Wiki Generation", desc: "Project overview, module docs, setup instructions" },
            { title: "Architecture Diagrams", desc: "Auto-detected architecture with Mermaid visuals" },
            { title: "Reading Guide", desc: "PageRank-based file ranking + guided reading path" },
          ].map((f) => (
            <div key={f.title} className="bg-white rounded-lg border border-slate-200 p-5">
              <h3 className="font-semibold text-slate-800 mb-2">{f.title}</h3>
              <p className="text-sm text-slate-500">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="text-center py-4 text-xs text-slate-400">
        <a href="https://github.com/he-yufeng/RepoWiki" className="hover:text-slate-600">
          RepoWiki
        </a>{" "}
        - Open-source DeepWiki alternative
      </footer>

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}
