import type { ScanRequest } from "./api";

const GIT_URL = /^(?:(?:https?|ssh|git\+ssh|git):\/\/|(?:www\.)?(?:github\.com|gitlab\.com|bitbucket\.org)\/)/i;

export function buildScanSourceRequest(input: string): Pick<ScanRequest, "path" | "url"> {
  const source = input.trim();
  if (!source) return {};
  return GIT_URL.test(source) ? { url: source } : { path: source };
}
