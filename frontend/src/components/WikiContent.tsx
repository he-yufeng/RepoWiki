import { useRef } from "react";
import { useParams } from "react-router-dom";
import MermaidDiagram from "./MermaidDiagram";
import { markdownToHtml, splitMermaid } from "../lib/markdown";

interface Props {
  content: string;
  title: string;
}

export default function WikiContent({ content }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const parts = splitMermaid(content);
  const { id: projectId } = useParams<{ id: string }>();

  return (
    <div ref={ref} className="max-w-4xl mx-auto px-8 py-8">
      <div className="prose prose-slate max-w-none">
        {parts.map((part, i) =>
          part.type === "mermaid" ? (
            <MermaidDiagram key={i} code={part.content} />
          ) : (
            <div
              key={i}
              dangerouslySetInnerHTML={{
                __html: markdownToHtml(part.content, { projectId }),
              }}
            />
          ),
        )}
      </div>
    </div>
  );
}
