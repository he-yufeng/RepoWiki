from repowiki.core.scanner import scan_directory


def test_scan_skips_minified_suffixes(tmp_path):
    (tmp_path / "app.min.js").write_text("console.log('packed');", encoding="utf-8")
    (tmp_path / "app.js").write_text("console.log('source');\n", encoding="utf-8")

    files = scan_directory(tmp_path)
    paths = {f.path for f in files}

    assert "app.js" in paths
    assert "app.min.js" not in paths


def test_scan_skips_generated_bundle_lines(tmp_path):
    assets = tmp_path / "src" / "server" / "static" / "assets"
    assets.mkdir(parents=True)
    (assets / "chunk-ABC123.js").write_text("const bundle='" + ("x" * 5000) + "';", encoding="utf-8")
    source = tmp_path / "src" / "main.js"
    source.write_text("export function main() {\n  return 42;\n}\n", encoding="utf-8")

    files = scan_directory(tmp_path)
    paths = {f.path.replace("\\", "/") for f in files}

    assert "src/main.js" in paths
    assert "src/server/static/assets/chunk-ABC123.js" not in paths


def test_scan_respects_gitignore_and_repowikiignore(tmp_path):
    (tmp_path / ".gitignore").write_text("dist/\n*.log\n", encoding="utf-8")
    (tmp_path / ".repowikiignore").write_text("private.md\n", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "bundle.js").write_text("console.log('built');\n", encoding="utf-8")
    (tmp_path / "debug.log").write_text("noise\n", encoding="utf-8")
    (tmp_path / "private.md").write_text("local notes\n", encoding="utf-8")
    (tmp_path / "src.py").write_text("print('source')\n", encoding="utf-8")

    paths = {f.path.replace("\\", "/") for f in scan_directory(tmp_path)}

    assert "src.py" in paths
    assert "dist/bundle.js" not in paths
    assert "debug.log" not in paths
    assert "private.md" not in paths


def test_scan_skips_real_env_files_but_keeps_example(tmp_path):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=real-secret\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text("TOKEN=secret\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("OPENAI_API_KEY=\n", encoding="utf-8")

    paths = {f.path for f in scan_directory(tmp_path)}

    assert ".env" not in paths
    assert ".env.local" not in paths
    assert ".env.example" in paths
