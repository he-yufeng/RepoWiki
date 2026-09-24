import { useEffect, useState } from "react";
import { useWikiStore } from "../stores/wiki";
import {
  listProtocols,
  listModelPresets,
  checkProtocol,
  discoverModels,
  bareModelId,
  type Protocol,
  type ModelPreset,
  type CheckResult,
  type DiscoveredModel,
} from "../lib/protocols";

type DiscState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; count: number }
  | { kind: "none"; msg: string }
  | { kind: "error"; msg: string };

function saveLocal(key: string, value: string): void {
  try {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
  } catch {
    // localStorage unavailable (private mode etc.) — keep in-memory only
  }
}

const inputCls =
  "w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:border-blue-500 outline-none";
const labelCls = "block text-sm font-medium text-slate-700 mb-1";
const stepCls = "text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2";

export default function ProviderWizard({ onSaved }: { onSaved: () => void }) {
  const { settings, updateSettings } = useWikiStore();
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [presets, setPresets] = useState<ModelPreset[]>([]);
  const [presetId, setPresetId] = useState(() =>
    settings.model.includes("/") ? "" : settings.model
  );
  const [protocolId, setProtocolId] = useState(settings.protocol || "");
  const [baseUrl, setBaseUrl] = useState(settings.baseUrl || "");
  const [apiKey, setApiKey] = useState(settings.apiKey || "");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState(settings.model || "");
  const [manualModel, setManualModel] = useState(() => bareModelId(settings.model || ""));
  const [manualMode, setManualMode] = useState(false);
  const [disc, setDisc] = useState<DiscState>({ kind: "idle" });
  const [models, setModels] = useState<DiscoveredModel[]>([]);
  const [checking, setChecking] = useState(false);
  const [check, setCheck] = useState<CheckResult | null>(null);

  useEffect(() => {
    listProtocols()
      .then((ps) => {
        setProtocols(ps);
        setProtocolId((cur) => cur || ps[0]?.id || "");
      })
      .catch(() => setProtocols([]));
    // a stored model that is not a known alias falls back to the gateway path
    listModelPresets()
      .then((ps) => {
        setPresets(ps);
        setPresetId((cur) => (cur && ps.some((p) => p.id === cur) ? cur : ""));
      })
      .catch(() => setPresets([]));
  }, []);

  const selected = protocols.find((p) => p.id === protocolId) ?? null;
  const preset = presets.find((p) => p.id === presetId) ?? null;
  // Presets route through MODEL_ALIASES, so they need no base URL and no probe.
  const isPreset = preset !== null;

  function qualify(p: Protocol | null, id: string): string {
    if (!p || !id) return id;
    if (id.includes("/")) return id;
    return `${p.litellm_prefix}${id}`;
  }

  /** Bare id sent to the backend so it can ping exactly that model. */
  const bareModel = isPreset
    ? ""
    : manualMode
      ? manualModel.trim()
      : bareModelId(model);

  function persist(next: { protocol?: string; baseUrl?: string; apiKey?: string; model?: string }) {
    const protocol = next.protocol ?? protocolId;
    const base = next.baseUrl ?? baseUrl;
    const key = next.apiKey ?? apiKey;
    const mod = next.model ?? model;
    updateSettings({ protocol, baseUrl: base, apiKey: key, model: mod });
    saveLocal("repowiki_protocol", protocol);
    saveLocal("repowiki_api_base", base.trim());
    saveLocal("repowiki_api_key", key.trim());
    saveLocal("repowiki_model", mod);
  }

  async function runDiscover() {
    if (!baseUrl.trim() || !protocolId) {
      setDisc({ kind: "error", msg: "Fill in the Base URL and pick an API format first." });
      return;
    }
    setDisc({ kind: "loading" });
    setModels([]);
    try {
      const r = await discoverModels(protocolId, baseUrl.trim(), apiKey.trim() || undefined);
      if (r.discoverable && (r.models?.length ?? 0) > 0) {
        setModels(r.models ?? []);
        setDisc({ kind: "ok", count: r.count });
        setManualMode(false);
      } else if (r.discoverable) {
        setManualMode(true);
        setDisc({ kind: "none", msg: "Endpoint reachable but returned no models; enter a model ID." });
      } else if (r.status_code === 401 || r.status_code === 403) {
        setDisc({
          kind: "error",
          msg: "The endpoint rejected the API key (401/403); check the key and fetch again.",
        });
      } else {
        setManualMode(true);
        setDisc({
          kind: "none",
          msg: "This endpoint exposes no models list (common for Anthropic-compatible gateways); enter a model ID.",
        });
      }
    } catch {
      setDisc({ kind: "error", msg: "Could not reach the RepoWiki server." });
    }
    setCheck(null);
  }

  async function runCheck() {
    setChecking(true);
    setCheck(null);
    try {
      const res = await checkProtocol({
        protocol: protocolId || undefined,
        api_base: baseUrl.trim() || undefined,
        api_key: apiKey.trim() || undefined,
        model: bareModel || undefined,
      });
      setCheck(res);
    } catch {
      setCheck({
        ok: false,
        base_url: baseUrl,
        status_code: null,
        masked_key: "",
        diagnosis: "Could not reach the RepoWiki server.",
      });
    } finally {
      setChecking(false);
    }
  }

  function onProtocolChange(id: string) {
    setProtocolId(id);
    setCheck(null);
    setDisc({ kind: "idle" });
    setModels([]);
    persist({ protocol: id });
  }

  function onBaseChange(v: string) {
    setBaseUrl(v);
    setCheck(null);
    setDisc({ kind: "idle" });
    setModels([]);
    persist({ baseUrl: v });
  }

  function onKeyChange(v: string) {
    setApiKey(v);
    setCheck(null);
    persist({ apiKey: v });
  }

  function pickPreset(id: string) {
    setPresetId(id);
    setModel(id);
    setManualModel("");
    setManualMode(false);
    setDisc({ kind: "idle" });
    setModels([]);
    setCheck(null);
    persist({ model: id });
  }

  function pickModel(m: DiscoveredModel) {
    setPresetId("");
    setModel(m.litellm_model);
    setManualModel(m.id);
    setCheck(null);
    persist({ model: m.litellm_model });
  }

  function onManual(v: string) {
    setPresetId("");
    setManualModel(v);
    const q = qualify(selected, v.trim());
    setModel(q);
    setCheck(null);
    persist({ model: q });
  }

  return (
    <div>
      {/* Step 1 — endpoint */}
      <div className={stepCls}>1 · Endpoint</div>
      <div className="mb-3">
        <label className={labelCls}>Base URL</label>
        <input
          className={inputCls}
          value={baseUrl}
          onChange={(e) => onBaseChange(e.target.value)}
          placeholder={selected?.base_hint || "https://api.example.com/v1"}
        />
        <p className="text-xs text-slate-400 mt-1">
          {isPreset
            ? "Not needed for a built-in preset — RepoWiki routes it to the vendor."
            : "OpenAI-style ends with /v1, Anthropic-style uses the root; auto-normalised."}
        </p>
      </div>
      <div className="mb-3">
        <label className={labelCls}>API format</label>
        <select
          className={inputCls}
          value={protocolId}
          onChange={(e) => onProtocolChange(e.target.value)}
        >
          {protocols.length === 0 && <option value="">Loading…</option>}
          {protocols.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
        {selected && <p className="text-xs text-slate-400 mt-1">{selected.wire}</p>}
      </div>
      <div className="mb-4">
        <label className={labelCls}>API Key</label>
        <div className="relative">
          <input
            className={inputCls + " pr-10"}
            type={showKey ? "text" : "password"}
            value={apiKey}
            onChange={(e) => onKeyChange(e.target.value)}
            placeholder="Enter API Key"
            autoComplete="off"
          />
          <button
            onClick={() => setShowKey((s) => !s)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            aria-label="Show/hide key"
          >
            {showKey ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Step 2 — model */}
      <div className={stepCls}>2 · Model</div>
      {presets.length > 0 && (
        <div className="mb-3">
          <label className={labelCls}>Built-in preset</label>
          <select
            className={inputCls}
            value={presetId}
            onChange={(e) => pickPreset(e.target.value)}
          >
            <option value="">Custom gateway — discover or type a model below</option>
            {presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          {preset && (
            <p className="text-xs text-slate-400 mt-1">
              Routes to {preset.model} — no Base URL needed, just the vendor's API key.
            </p>
          )}
        </div>
      )}
      <button
        onClick={runDiscover}
        disabled={disc.kind === "loading"}
        className="w-full py-2 mb-2 rounded-lg text-sm font-medium border border-blue-600 text-blue-700 hover:bg-blue-50 disabled:opacity-50 transition-colors"
      >
        {disc.kind === "loading" ? "Probing…" : "Fetch model list"}
      </button>

      {disc.kind === "ok" && (
        <div className="mb-2 rounded-lg px-3 py-2 text-sm bg-green-50 text-green-800">
          Auto-discovery available · {disc.count} models
        </div>
      )}
      {disc.kind === "none" && (
        <div className="mb-2 rounded-lg px-3 py-2 text-sm bg-amber-50 text-amber-800">{disc.msg}</div>
      )}
      {disc.kind === "error" && (
        <div className="mb-2 rounded-lg px-3 py-2 text-sm bg-red-50 text-red-700">{disc.msg}</div>
      )}
      {disc.kind === "idle" && (
        <p className="text-xs text-slate-400 mb-2">
          Probe whether this endpoint can list its models; otherwise enter a model ID.
        </p>
      )}

      {disc.kind === "ok" && !manualMode && (
        <div className="mb-2">
          <select
            className={inputCls}
            value={model}
            onChange={(e) => {
              const m = models.find((x) => x.litellm_model === e.target.value);
              if (m) pickModel(m);
            }}
          >
            <option value="">Select a model…</option>
            {models.map((m) => (
              <option key={m.litellm_model} value={m.litellm_model} disabled={!m.chat}>
                {m.id}
                {m.chat ? "" : ` — ${m.chat_reason}`}
              </option>
            ))}
          </select>
          <button
            onClick={() => setManualMode(true)}
            className="text-xs text-blue-600 hover:underline mt-1"
          >
            Enter a model ID manually instead
          </button>
        </div>
      )}

      {(manualMode || disc.kind === "none") && (
        <div className="mb-2">
          <label className={labelCls}>
            {disc.kind === "ok" ? "Manual model ID" : "Model ID (required)"}
          </label>
          <input
            className={inputCls}
            value={manualModel}
            onChange={(e) => onManual(e.target.value)}
            placeholder="e.g. qwen3.8-flash"
          />
          {disc.kind === "ok" && (
            <button
              onClick={() => setManualMode(false)}
              className="text-xs text-blue-600 hover:underline mt-1"
            >
              Pick from the discovered list
            </button>
          )}
        </div>
      )}

      {/* Step 3 — verify */}
      <div className={stepCls + " mt-4"}>3 · Verify</div>
      {isPreset ? (
        <p className="text-xs text-slate-400 mb-3">
          Nothing to probe: a preset uses RepoWiki's built-in routing, so add the
          vendor's API key in step 1 and press Done.
        </p>
      ) : (
        <>
          <button
            onClick={runCheck}
            disabled={checking || !bareModel}
            className="w-full py-2 mb-3 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {checking ? "Testing…" : "Test connection"}
          </button>
          {!bareModel && (
            <p className="text-xs text-slate-400 -mt-2 mb-3">
              Choose or enter a model in step 2 first.
            </p>
          )}
        </>
      )}

      {check && (
        <div
          className={
            "mb-3 rounded-lg px-3 py-2 text-sm " +
            (check.ok ? "bg-green-50 text-green-800" : "bg-red-50 text-red-700")
          }
        >
          {check.ok ? (
            <span>Connected{check.masked_key && ` · ${check.masked_key}`}</span>
          ) : (
            <span>{check.diagnosis}</span>
          )}
        </div>
      )}

      <button
        onClick={onSaved}
        disabled={!isPreset && !check?.ok}
        className="w-full py-2 rounded-lg text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 disabled:hover:bg-slate-100 transition-colors"
      >
        Done
      </button>
      {!isPreset && !check?.ok && (
        <p className="text-xs text-slate-400 text-center mt-2">
          Test the connection successfully to finish.
        </p>
      )}
    </div>
  );
}
