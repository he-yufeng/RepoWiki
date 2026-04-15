"""repowiki command-line interface."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from repowiki import __version__
from repowiki.config import Config, resolve_model
from repowiki.ingest.github import parse_git_url

console = Console()


def _is_url(s: str) -> bool:
    return s.startswith("http") or parse_git_url(s) is not None


@click.group()
@click.version_option(__version__, prog_name="repowiki")
def cli():
    """RepoWiki - generate wiki documentation for any codebase."""
    pass


@cli.command()
@click.argument("path_or_url")
@click.option("-o", "--output", default=None, help="Output directory (default: ./wiki)")
@click.option(
    "-f", "--format", "fmt",
    type=click.Choice(["markdown", "json", "html"]),
    default="markdown",
    help="Output format",
)
@click.option("-l", "--lang", default=None, help="Output language (en/zh/ja/ko)")
@click.option("-m", "--model", default=None, help="LLM model name or alias")
@click.option("--open", "open_browser", is_flag=True, help="Open HTML output in browser")
def scan(path_or_url: str, output: str | None, fmt: str, lang: str | None,
         model: str | None, open_browser: bool):
    """Scan a local directory or GitHub URL and generate wiki documentation."""
    cfg = Config.load()
    if lang:
        cfg.language = lang
    if model:
        cfg.model = resolve_model(model)
    if output:
        cfg.output_dir = output

    with console.status("[bold cyan]Scanning project..."):
        if _is_url(path_or_url):
            from repowiki.ingest.github import ingest_github
            project = ingest_github(
                path_or_url,
                max_file_size=cfg.max_file_size,
                max_files=cfg.max_files,
            )
        else:
            from repowiki.ingest.local import ingest_local
            project = ingest_local(
                path_or_url,
                max_file_size=cfg.max_file_size,
                max_files=cfg.max_files,
            )

    # display scan results
    console.print()
    console.print(f"[bold green]Project:[/] {project.name}")
    console.print(f"[bold green]Files:[/]   {len(project.files)}")
    console.print(f"[bold green]Lines:[/]   {project.total_lines:,}")

    # language breakdown
    lang_counts: dict[str, int] = {}
    for f in project.files:
        lang_counts[f.language] = lang_counts.get(f.language, 0) + 1

    if lang_counts:
        table = Table(title="Languages", show_header=True, header_style="bold")
        table.add_column("Language", style="cyan")
        table.add_column("Files", justify="right")
        for language, count in sorted(lang_counts.items(), key=lambda x: -x[1])[:10]:
            table.add_row(language, str(count))
        console.print(table)

    # file tree (top 30 entries)
    tree_widget = Tree(f"[bold]{project.name}/[/]")
    _build_rich_tree(tree_widget, project.files, max_entries=30)
    console.print(tree_widget)

    # if we have an API key, run the LLM analysis
    if not cfg.api_key:
        console.print()
        console.print(
            "[yellow]No API key configured. Showing scan results only.[/]\n"
            "Set one with: [bold]repowiki config set api_key YOUR_KEY[/]\n"
            "Or set DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY env var."
        )
        return

    # phase 2 will add LLM analysis here
    import asyncio
    asyncio.run(_run_analysis(project, cfg, fmt, open_browser))


async def _run_analysis(project, cfg: Config, fmt: str, open_browser: bool):
    """run the full LLM analysis pipeline."""
    from repowiki.core.analyzer import Analyzer
    from repowiki.core.cache import Cache
    from repowiki.llm.client import LLMClient

    llm = LLMClient(model=cfg.model, api_key=cfg.api_key, api_base=cfg.api_base)
    cache = Cache()
    await cache.init()

    analyzer = Analyzer(llm=llm, cache=cache, language=cfg.language, concurrency=cfg.concurrency)

    from rich.progress import Progress, SpinnerColumn, TextColumn
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing project...", total=None)

        def on_progress(step: str):
            progress.update(task, description=step)

        wiki_data = await analyzer.analyze(project, on_progress=on_progress)

    # export
    from repowiki.core.graph import DependencyGraph
    from repowiki.core.wiki_builder import WikiBuilder

    graph = DependencyGraph.build_from_project(project)
    builder = WikiBuilder()
    wiki = builder.build(project, wiki_data, graph)

    output_dir = cfg.output_dir
    if fmt == "markdown":
        from repowiki.export.markdown import export_markdown
        export_markdown(wiki, output_dir)
        console.print(f"\n[bold green]Wiki generated:[/] {output_dir}/")
    elif fmt == "json":
        from repowiki.export.json_export import export_json
        out_path = f"{output_dir}/repowiki.json"
        export_json(wiki, out_path)
        console.print(f"\n[bold green]Wiki generated:[/] {out_path}")
    elif fmt == "html":
        from repowiki.export.html import export_html
        out_path = f"{output_dir}/repowiki.html"
        export_html(wiki, out_path)
        console.print(f"\n[bold green]Wiki generated:[/] {out_path}")
        if open_browser:
            import webbrowser
            webbrowser.open(f"file://{out_path}")

    # show token usage
    if llm.total_input_tokens or llm.total_output_tokens:
        console.print(
            f"[dim]Tokens used: {llm.total_input_tokens:,} in / "
            f"{llm.total_output_tokens:,} out"
            f"{f' (${llm.total_cost:.4f})' if llm.total_cost else ''}[/]"
        )

    await cache.close()


def _build_rich_tree(tree: Tree, files, max_entries: int = 30):
    """add files to a Rich tree widget, grouped by directory."""
    dirs: dict[str, list] = {}
    for f in files[:max_entries]:
        from pathlib import Path as P
        parts = P(f.path).parts
        if len(parts) == 1:
            icon = "📄" if not f.is_config else "⚙️"
            tree.add(f"{icon} {f.path} [dim]({f.language})[/]")
        else:
            top = parts[0]
            if top not in dirs:
                dirs[top] = tree.add(f"📁 {top}/")
            # just show the filename under the dir
            icon = "📄" if not f.is_config else "⚙️"
            dirs[top].add(f"{icon} {'/'.join(parts[1:])} [dim]({f.language})[/]")

    remaining = len(files) - max_entries
    if remaining > 0:
        tree.add(f"[dim]... and {remaining} more files[/]")


@cli.command()
@click.argument("path_or_url", default=".")
@click.option("-p", "--port", default=8000, help="Port to serve on")
def serve(path_or_url: str, port: int):
    """Start the RepoWiki web interface."""
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        console.print(
            "[red]Web dependencies not installed.[/]\n"
            "Install with: [bold]pip install repowiki[web][/]"
        )
        raise SystemExit(1)

    console.print(f"[bold cyan]Starting RepoWiki server on port {port}...[/]")
    console.print(f"[bold]Open:[/] http://localhost:{port}")

    import uvicorn
    uvicorn.run(
        "repowiki.server.app:create_app",
        host="0.0.0.0",
        port=port,
        factory=True,
        log_level="info",
    )


@cli.command()
@click.argument("path_or_url")
def chat(path_or_url: str):
    """Ask questions about a codebase in the terminal."""
    console.print("[bold cyan]RepoWiki Chat[/] (type 'exit' to quit)\n")
    # phase 4 will implement this
    console.print("[yellow]Chat mode coming soon. Use `repowiki scan` for now.[/]")


@cli.group("config")
def config_group():
    """Manage RepoWiki configuration."""
    pass


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a config value (e.g., repowiki config set model deepseek)."""
    cfg = Config.load()
    if key == "model":
        value = resolve_model(value)

    if not hasattr(cfg, key):
        console.print(f"[red]Unknown config key: {key}[/]")
        console.print(f"Valid keys: {', '.join(cfg.__dataclass_fields__.keys())}")
        raise SystemExit(1)

    setattr(cfg, key, value)
    cfg.save()
    console.print(f"[green]Set {key} = {value}[/]")


@config_group.command("get")
@click.argument("key")
def config_get(key: str):
    """Get a config value."""
    cfg = Config.load()
    if not hasattr(cfg, key):
        console.print(f"[red]Unknown config key: {key}[/]")
        raise SystemExit(1)
    val = getattr(cfg, key)
    # mask API key
    if key == "api_key" and val:
        val = val[:8] + "..." + val[-4:]
    console.print(f"{key} = {val}")


@config_group.command("list")
def config_list():
    """Show all config values."""
    cfg = Config.load()
    table = Table(title="Configuration", show_header=True, header_style="bold")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_column("Source", style="dim")

    for key in cfg.__dataclass_fields__:
        val = getattr(cfg, key)
        if key == "api_key" and val:
            val = val[:8] + "..." + val[-4:]
        source = "default"
        import os
        env_key = f"REPOWIKI_{key.upper()}"
        if os.getenv(env_key):
            source = f"env ({env_key})"
        table.add_row(key, str(val), source)

    console.print(table)
