import { useEffect, useRef } from "react";
import MermaidDiagram from "./MermaidDiagram";

interface Props {
  content: string;
  title: string;
}

export default function WikiContent({ content, title }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  // split content at mermaid blocks and render them as components
  const parts = splitMermaid(content);

  return (
    <div ref={ref} className="max-w-4xl mx-auto px-8 py-8">
      <div className="prose prose-slate max-w-none">
        {parts.map((part, i) =>
          part.type === "mermaid" ? (
            <MermaidDiagram key={i} code={part.content} />
          ) : (
            <div key={i} dangerouslySetInnerHTML={{ __html: markdownToHtml(part.content) }} />
          ),
        )}
      </div>
    </div>
  );
}

interface ContentPart {
  type: "text" | "mermaid";
  content: string;
}

function splitMermaid(md: string): ContentPart[] {
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

function markdownToHtml(md: string): string {
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
  html = html.replace(/^(?!<[hblup]|<li|<code|<pre|<div|<strong)(.+)$/gm, '<p class="my-2 leading-relaxed">$1</p>');

  return html;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
