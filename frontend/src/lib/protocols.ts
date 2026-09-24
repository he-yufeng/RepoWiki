const BASE = "/api";

export interface Protocol {
  id: string;
  label: string;
  /** plain description of the request shape, shown under the format picker */
  wire: string;
  litellm_prefix: string;
  models_path: string;
  base_hint: string;
}

export interface CheckResult {
  ok: boolean;
  base_url: string;
  status_code: number | null;
  masked_key: string;
  diagnosis: string | null;
}

export interface DiscoveredModel {
  id: string;
  litellm_model: string;
  chat: boolean;
  chat_reason: string;
  mode: string | null;
  max_input_tokens: number | null;
  max_output_tokens: number | null;
  input_cost_per_token: number | null;
  output_cost_per_token: number | null;
  metadata_source: string;
}

export interface ModelsResponse {
  models: DiscoveredModel[];
  count: number;
  /** false when the gateway exposes no models list (e.g. 404) */
  discoverable?: boolean;
  /** HTTP status of the models probe when it failed */
  status_code?: number | null;
  error?: string;
}

export interface ModelPreset {
  /** alias id, e.g. "deepseek" — what the backend resolves to a real model */
  id: string;
  label: string;
  /** the model the alias routes to, shown as a hint */
  model: string;
}

/** Fetch the supported wire protocols (no secrets). */
export async function listProtocols(): Promise<Protocol[]> {
  const res = await fetch(`${BASE}/protocols`);
  const data = await res.json();
  return (data.protocols ?? []) as Protocol[];
}

/** Fetch the built-in model aliases, which need no Base URL of their own. */
export async function listModelPresets(): Promise<ModelPreset[]> {
  const res = await fetch(`${BASE}/model-presets`);
  const data = await res.json();
  return (data.presets ?? []) as ModelPreset[];
}

/** Strip a litellm provider prefix: the bare id a gateway is pinged with. */
export function bareModelId(id: string): string {
  const slash = id.indexOf("/");
  return slash === -1 ? id : id.slice(slash + 1);
}

/** Ping the gateway with the selected model before credentials are saved. */
export async function checkProtocol(req: {
  protocol?: string;
  api_base?: string;
  api_key?: string;
  model?: string;
}): Promise<CheckResult> {
  const res = await fetch(`${BASE}/protocols/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return res.json();
}

/** Discover the models an endpoint serves, merged with capability metadata. */
export async function discoverModels(
  protocol: string,
  apiBase?: string,
  apiKey?: string,
): Promise<ModelsResponse> {
  const params = new URLSearchParams();
  if (protocol) params.set("protocol", protocol);
  if (apiBase) params.set("api_base", apiBase);
  const headers: Record<string, string> = {};
  if (apiKey) headers["x-api-key"] = apiKey;
  const res = await fetch(`${BASE}/models?${params.toString()}`, { headers });
  return res.json();
}
