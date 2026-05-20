// shared markdown -> HTML rendering. Intentionally tiny and dependency-free
// to keep the bundle small; WikiContent and ChatView both consume it so
// fixes show up in both places.

export interface ContentPart {
  type: "text" | "mermaid";
  content: string;
}

export function splitMermaid(md: string): ContentPart[] {
  const parts: ContentPart[] = [];
  const regex = /```mermaid\n([\s\S]*?)```/g;
  let lastIdx = 0;
  let match;
  while ((match = regex.exec(md)) !== null) {
    if (match.index > lastIdx) {
      parts.push({ type: "text", content: md.slice(lastIdx, match.index) });
    }
    parts.push({ type: "mermaid", content: match[1].trim() });
    lastIdx = match.index + match[0].length;
  }
  if (lastIdx < md.length) {
    parts.push({ type: "text", content: md.slice(lastIdx) });
  }
  return parts;
}

// Path-with-line citations the analyzer emits as `path/file.ext:42` or
// `path/file.ext:42-67`. We restrict the file-extension whitelist so we
// don't mangle innocuous `something:42` notation in prose.
const CITATION_EXTS = "py|ts|tsx|js|jsx|mjs|cjs|go|rs|java|kt|cpp|c|h|hpp|rb|php|swift|scala|sh|css|html|md|yml|yaml|json|toml";
const CITATION_RE = new RegExp(
  // `<code ...>path/with.ext:42(-67)?</code>` (the inline-code transform
  // runs before this, so we match the rendered <code> tag).
  String.raw`(<code[^>]*>)([\w./@\-]+\.(?:${CITATION_EXTS})):(\d+)(?:-(\d+))?(</code>)`,
  "g",
);

function linkifyCitations(html: string, projectId: string | undefined): string {
  if (!projectId) return html;
  return html.replace(CITATION_RE, (_m, openTag, path, start, end, closeTag) => {
    const endParam = end ? `&end=${end}` : "";
    // hash-style href so anyone with their own router doesn't accidentally
    // get a full page navigation; the SourceView is a regular route inside
    // react-router so the standard /project/{id}/source link below also
    // works -- we use that one because it lets the OS open a new tab.
    const href = `/project/${encodeURIComponent(projectId)}/source?path=${encodeURIComponent(path)}&line=${start}${endParam}`;
    const label = end ? `${path}:${start}-${end}` : `${path}:${start}`;
    return (
      `<a href="${href}" target="_blank" rel="noopener" ` +
      `class="text-blue-600 hover:underline font-mono text-[0.95em]" ` +
      `data-citation="${escapeHtml(path)}">${escapeHtml(label)}</a>`
    );
  });
}

export function markdownToHtml(md: string, opts?: { projectId?: string }): string {
  let html = md;

  // code blocks (non-mermaid)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre class="bg-slate-800 text-slate-100 p-4 rounded-lg overflow-x-auto text-sm"><code class="language-${lang || "text"}">${escapeHtml(code.trim())}</code></pre>`;
  });

  // headings
  html = html.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-6 mb-2">$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold mt-8 mb-3 pb-2 border-b border-slate-200">$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mb-4 pb-2 border-b border-slate-200">$1</h1>');

  // blockquotes
  html = html.replace(/^> (.+)$/gm, '<blockquote class="border-l-4 border-blue-400 pl-4 py-2 bg-blue-50 rounded-r text-blue-800 my-3">$1</blockquote>');

  // bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // inline code
  html = html.replace(/`([^`]+)`/g, '<code class="bg-slate-100 px-1.5 py-0.5 rounded text-sm text-slate-700">$1</code>');

  // links
  html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="text-blue-600 hover:underline">$1</a>');

  // list items
  html = html.replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>');
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal">$1</li>');

  // paragraphs (lines that aren't already wrapped)
  html = html.replace(/^(?!<[hblup]|<li|<code|<pre|<div|<strong|<a)(.+)$/gm, '<p class="my-2 leading-relaxed">$1</p>');

  // Convert `path:line` inline-code spans into source-view links. This
  // runs LAST so it sees the rendered <code> wrappers.
  html = linkifyCitations(html, opts?.projectId);

  return html;
}

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
