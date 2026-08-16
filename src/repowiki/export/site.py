"""GitHub Pages-ready site loader for a markdown-exported wiki."""

from __future__ import annotations

from pathlib import Path

# docsify loads the exported README.md as the landing page and _sidebar.md as
# the sidebar; docsify-mermaid renders the architecture diagrams.
_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/docsify@4/lib/themes/vue.css">
</head>
<body>
<div id="app">Loading...</div>
<script>
window.$docsify = {{
  name: "{title}",
  homepage: "README.md",
  loadSidebar: true,
  subMaxLevel: 2,
}};
</script>
<script src="https://cdn.jsdelivr.net/npm/docsify@4"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/docsify-mermaid@2/dist/docsify-mermaid.js"></script>
<script>mermaid.initialize({{ startOnLoad: false }});</script>
</body>
</html>
"""


def write_site_loader(output_dir: str | Path, title: str) -> None:
    """Make a markdown-exported wiki servable as-is on GitHub Pages.

    Writes a docsify ``index.html`` (so Pages serves a real site, not a file
    listing) and an empty ``.nojekyll`` (so Pages stops ignoring the
    underscore-prefixed ``_sidebar.md``).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(_INDEX_HTML.format(title=title), encoding="utf-8")
    (out / ".nojekyll").touch()
