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
@click.option(
    "-c", "--concurrency", default=None, type=int,
    help="Parallel LLM calls (default 5; lower if your provider rate-limits)",
)
@click.option(
    "--max-context-tokens", default=None, type=int,
    help="Token budget for project-wide prompts. 0 = unlimited (default 32000)",
)
@click.option(
    "--since", default=None,
    help="Incremental mode: only re-analyse modules touching files changed "
         "since this git ref (e.g. HEAD~10, main). Local-path scans only.",
)
@click.option("--open", "open_browser", is_flag=True, help="Open HTML output in browser")
def scan(path_or_url: str, output: str | None, fmt: str, lang: str | None,
         model: str | None, concurrency: int | None,
         max_context_tokens: int | None, since: str | None, open_browser: bool):
    """Scan a local directory or GitHub URL and generate wiki documentation."""
    cfg = Config.load()
    if lang:
        cfg.language = lang
    if model:
        cfg.model = resolve_model(model)
    if output:
        cfg.output_dir = output
    if concurrency is not None:
        cfg.concurrency = max(1, concurrency)
    if max_context_tokens is not None:
        cfg.max_context_tokens = max(0, max_context_tokens)

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

    # incremental: resolve --since into a set of changed paths
    changed_paths: set[str] | None = None
    if since:
        if _is_url(path_or_url):
            console.print(
                "[yellow]--since is only supported for local paths "
                "(remote scans always do a full analysis).[/]"
            )
        else:
            from repowiki.ingest.git_diff import changed_paths_since
            changed_paths = changed_paths_since(path_or_url, since)
            if changed_paths:
                console.print(
                    f"[bold green]Incremental:[/] {len(changed_paths)} "
                    f"file(s) changed since {since}"
                )
            else:
                console.print(
                    f"[yellow]--since {since}: no changes detected (or git unavailable). "
                    "Falling back to full analysis.[/]"
                )
                changed_paths = None

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
    asyncio.run(_run_analysis(project, cfg, fmt, open_browser, changed_paths))


async def _run_analysis(project, cfg: Config, fmt: str, open_browser: bool,
                        changed_paths: set[str] | None = None):
    """run the full LLM analysis pipeline."""
    from repowiki.core.analyzer import Analyzer
    from repowiki.core.cache import Cache
    from repowiki.llm.client import LLMClient

    llm = LLMClient(model=cfg.model, api_key=cfg.api_key, api_base=cfg.api_base)
    cache = Cache()
    await cache.init()

    analyzer = Analyzer(
        llm=llm,
        cache=cache,
        language=cfg.language,
        concurrency=cfg.concurrency,
        max_context_tokens=cfg.max_context_tokens,
        changed_paths=changed_paths,
    )

    # Build the dependency graph upfront so PageRank is available both to
    # the analyzer (reading guide ordering) and to the wiki builder
    # (dependency page).
    from repowiki.core.graph import DependencyGraph
    from repowiki.core.wiki_builder import WikiBuilder

    graph = DependencyGraph.build_from_project(project)
    rankings = graph.rank_files()

    from rich.progress import Progress, SpinnerColumn, TextColumn
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing project...", total=None)

        def on_progress(step: str):
            progress.update(task, description=step)

        wiki_data = await analyzer.analyze(
            project, on_progress=on_progress, rankings=rankings,
        )

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

    if analyzer.skipped_modules:
        console.print(
            f"[dim]Incremental: skipped {len(analyzer.skipped_modules)} unchanged "
            f"module(s) -> {', '.join(analyzer.skipped_modules[:5])}"
            f"{'...' if len(analyzer.skipped_modules) > 5 else ''}[/]"
        )

    if analyzer.errors:
        console.print()
        console.print("[bold yellow]Some analysis steps failed:[/]")
        for err in analyzer.errors:
            console.print(f"  [red]•[/] {err}")
        console.print(
            "[dim]Wiki was generated with placeholders for failed sections. "
            "Re-run to retry — successful sections are cached.[/]"
        )

    if builder.warnings:
        console.print()
        console.print("[bold yellow]Content sanity warnings:[/]")
        for w in builder.warnings[:10]:
            console.print(f"  [yellow]•[/] {w}")
        if len(builder.warnings) > 10:
            console.print(f"  [dim](+{len(builder.warnings) - 10} more)[/]")

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

    # warn if the bundled web UI isn't present
    from pathlib import Path as _Path

    import repowiki.server as _server_pkg
    static_dir = _Path(_server_pkg.__file__).parent / "static"
    if not (static_dir / "index.html").exists():
        console.print(
            "[yellow]Web UI not bundled in this install.[/] "
            "API endpoints will work, but / will 404.\n"
            "[dim]To build the UI from source:[/] "
            "[bold]cd frontend && npm install && npm run build[/]\n"
            "[dim]Or reinstall with the published wheel: "
            "[bold]pip install --upgrade repowiki[web][/][/]"
        )

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
@click.argument("path_or_url", default=".")
@click.option("-m", "--model", default=None, help="LLM model name or alias")
@click.option("-l", "--lang", default=None, help="Language for replies (en/zh/ja/ko)")
@click.option(
    "-k", "--top-k", default=5, type=click.IntRange(1, 50),
    help="Number of code chunks to retrieve (1-50)",
)
def chat(path_or_url: str, model: str | None, lang: str | None, top_k: int):
    """Ask questions about a codebase in the terminal.

    Indexes the project with TF-IDF on first question, then streams
    the LLM's answer with a list of source files used for context.
    """
    cfg = Config.load()
    if model:
        cfg.model = resolve_model(model)
    if lang:
        cfg.language = lang

    if not cfg.api_key:
        console.print(
            "[red]No API key configured.[/] Set one with "
            "[bold]repowiki config set api_key YOUR_KEY[/] "
            "or via DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY."
        )
        raise SystemExit(1)

    with console.status("[bold cyan]Loading project..."):
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

    with console.status("[bold cyan]Building TF-IDF index..."):
        from repowiki.core.rag import SimpleRAG
        rag = SimpleRAG()
        rag.index(project)

    console.print()
    console.print(
        f"[bold green]RepoWiki Chat[/] - {project.name} "
        f"({len(project.files)} files, {len(rag.chunks)} chunks)"
    )
    console.print(f"[dim]Model: {cfg.model}  Lang: {cfg.language}  Top-K: {top_k}[/]")
    console.print("[dim]Type your question, or 'exit' / Ctrl-D to quit.[/]\n")

    import asyncio

    from repowiki.llm.client import LLMClient, LLMError
    from repowiki.llm.prompts import build_chat_prompt

    llm = LLMClient(model=cfg.model, api_key=cfg.api_key, api_base=cfg.api_base)

    # multi-turn history kept in process memory; cleared with ":clear"
    history: list[dict] = []

    async def ask_once(question: str) -> None:
        from rich.markdown import Markdown
        from rich.table import Table as RichTable

        chunks = rag.retrieve(question, top_k=top_k)
        if not chunks:
            console.print("[yellow]No relevant code found in the index.[/]\n")
            return

        sources = RichTable(show_header=False, box=None, pad_edge=False)
        sources.add_column(style="cyan")
        sources.add_column(style="dim")
        context_parts = []
        for chunk in chunks:
            sources.add_row(
                f"{chunk.file_path}:{chunk.line_start}-{chunk.line_end}",
                f"(score {chunk.score:.2f})",
            )
            context_parts.append(
                f"### {chunk.file_path} (lines {chunk.line_start}-{chunk.line_end})\n"
                f"```\n{chunk.content}\n```"
            )
        console.print("[dim]Sources:[/]")
        console.print(sources)
        console.print()

        messages = build_chat_prompt(
            question, "\n\n".join(context_parts), cfg.language, history=history,
        )
        # buffer the stream so we can render the final answer as Markdown
        # in one pass (Rich's Markdown doesn't support incremental render).
        # Print a heartbeat dot every chunk so the user sees progress.
        buffer = []
        try:
            async for piece in llm.stream(messages):
                buffer.append(piece)
                console.print(".", end="", soft_wrap=True)
        except LLMError as e:
            console.print(f"\n[red]LLM error:[/] {e}\n")
            return
        console.print()  # newline after the dots
        answer = "".join(buffer)
        if answer.strip():
            console.print(Markdown(answer))
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
        console.print()

    while True:
        try:
            q = click.prompt("you", prompt_suffix="> ", default="", show_default=False).strip()
        except (EOFError, click.exceptions.Abort):
            console.print("\n[dim]bye[/]")
            return
        if not q:
            continue
        if q.lower() in ("exit", "quit", ":q"):
            console.print("[dim]bye[/]")
            return
        if q.lower() in (":clear", "/clear"):
            history.clear()
            console.print("[dim](history cleared)[/]\n")
            continue
        try:
            asyncio.run(ask_once(q))
        except KeyboardInterrupt:
            console.print("\n[dim](interrupted)[/]\n")


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
