import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, theme: "default" });

let mermaidId = 0;

interface Props {
  code: string;
}

export default function MermaidDiagram({ code }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  const [svg, setSvg] = useState("");

  useEffect(() => {
    const id = `mermaid-${++mermaidId}`;
    mermaid
      .render(id, code)
      .then(({ svg }) => {
        setSvg(svg);
        setError("");
      })
      .catch((e) => {
        setError(`Diagram render failed: ${e.message}`);
        setSvg("");
      });
  }, [code]);

  if (error) {
    return (
      <div className="my-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-sm text-amber-700 mb-2">{error}</p>
        <pre className="text-xs text-slate-600 bg-slate-50 p-2 rounded overflow-x-auto">
          {code}
        </pre>
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className="my-6 flex justify-center overflow-x-auto"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
