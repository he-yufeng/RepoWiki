"""tiny, dependency-free Mermaid syntax sanitizer.

LLMs occasionally emit Mermaid that won't render: missing diagram type
prefix, parentheses inside node IDs, or a wrong diagram kind (sequence
markup inside what's claimed to be a flowchart). This module patches the
common cases and returns ``None`` only when the input is hopeless, in
which case the caller is expected to skip rendering rather than display
a blank box.

We deliberately do NOT pull in a real Mermaid parser -- this is a
forgiving best-effort fixer, not a validator.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from repowiki.core.models import ArchitectureDiagram

_GRAPH_TYPES = ("graph", "flowchart")
_GRAPH_DIRECTIONS = ("TD", "TB", "LR", "RL", "BT")

# Anything that's plausibly a node label: a single identifier in
# brackets/parens/curlies. We rewrite only the *ID* (before the bracket)
# so the visible label is preserved.
_NODE_ID_RE = re.compile(r"(^|[\s;>])([A-Za-z0-9_]*[^\sA-Za-z0-9_\[\(\{][^\s\[\(\{]*?)(\[|\(|\{)")


def sanitize_mermaid(text: str, *, kind: Literal["component", "sequence"]) -> str | None:
    """return a cleaned Mermaid string, or ``None`` if it's beyond saving.

    For ``kind="component"`` we ensure the body starts with
    ``graph <direction>`` (defaulting to ``TD``). For ``kind="sequence"``
    we ensure the body starts with ``sequenceDiagram``.
    """
    if not text or not text.strip():
        return None

    body = text.strip()
    first_line = body.splitlines()[0].strip().lower()

    if kind == "sequence":
        if not first_line.startswith("sequencediagram"):
            # mismatch: caller expected sequence, LLM emitted flowchart.
            # Only auto-prepend if there is *no* graph header (otherwise
            # we'd produce nested headers and confuse the renderer).
            if first_line.startswith(_GRAPH_TYPES):
                return None
            body = "sequenceDiagram\n" + body
        return body

    # kind == "component"
    if first_line.startswith(_GRAPH_TYPES):
        # already has a header; leave direction alone
        return _sanitize_node_ids(body)
    if first_line.startswith("sequencediagram"):
        return None  # caller expected component, can't recover
    return "graph TD\n" + _sanitize_node_ids(body)


def _sanitize_node_ids(text: str) -> str:
    """replace any non-[A-Za-z0-9_] characters inside node IDs with underscores.

    Mermaid is fine with ``Foo[Some Display Label]`` but chokes on
    ``foo.bar[Some Label]`` because the dot ends the ID. We only touch
    the ID -- the bracketed/parenthesized/braced label is preserved
    verbatim.
    """
    out_lines: list[str] = []
    for line in text.splitlines():
        out_lines.append(_sanitize_line(line))
    return "\n".join(out_lines)


_TOKEN_SPLIT = re.compile(r"(\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\}|-->|<--|---|==>|-->\|[^|]*\||[\s;]+)")


def _sanitize_line(line: str) -> str:
    """tokenize a single line and clean node IDs without touching labels."""
    parts = _TOKEN_SPLIT.split(line)
    cleaned: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith(("[", "(", "{")) or part.strip() in (
            "-->", "<--", "---", "==>", ""
        ) or part.startswith("-->|"):
            cleaned.append(part)
            continue
        # whitespace / separator chunks
        if part.strip() == "":
            cleaned.append(part)
            continue
        # If this looks like an ID (no spaces, leading letter), clean it.
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", part):
            cleaned.append(part)
        else:
            cleaned.append(re.sub(r"[^A-Za-z0-9_]", "_", part))
    return "".join(cleaned)


def describe_components(arch: ArchitectureDiagram) -> str:
    """fallback text description when a Mermaid diagram can't be rendered.

    When ``sanitize_mermaid`` returns ``None`` the wiki page would otherwise
    just say "diagram unavailable" -- a dead end for the reader. We instead
    render the component list and data flow as a structured Markdown block so
    the information the LLM produced is still useful.

    Returns an empty string when there is nothing salvageable.
    """
    parts: list[str] = []
    if arch.components:
        parts.append("**Components:**\n")
        for c in arch.components:
            purpose = f" — {c.purpose}" if c.purpose else ""
            parts.append(f"- `{c.name}`{purpose}")
        parts.append("")
    if arch.data_flow:
        parts.append("**Flow:** " + arch.data_flow)
    return "\n".join(parts).strip()
