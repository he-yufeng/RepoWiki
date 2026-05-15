"""Validate the bundled GitHub composite action and example workflow.

These tests don't actually run the action -- they verify the YAML parses,
the inputs match what the embedded shell command consumes, and every CLI
flag the action passes is one repowiki.cli.scan actually accepts."""
from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from repowiki.cli import cli

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTION_YML = REPO_ROOT / ".github" / "actions" / "repowiki-scan" / "action.yml"
EXAMPLE_WF = REPO_ROOT / ".github" / "workflows" / "wiki-on-pr.yml"


def _load(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def test_action_yaml_parses_and_has_required_keys():
    data = _load(ACTION_YML)
    assert data["name"] == "RepoWiki Scan"
    assert data["runs"]["using"] == "composite"
    assert "api-key" in data["inputs"]
    assert data["inputs"]["api-key"]["required"] is True


def test_action_inputs_all_used_in_run_steps():
    data = _load(ACTION_YML)
    inputs = set(data["inputs"].keys())
    # collect all `${{ inputs.X }}` references across the steps' run scripts
    used: set[str] = set()
    for step in data["runs"]["steps"]:
        run = step.get("run") or ""
        env = step.get("env") or {}
        with_ = step.get("with") or {}
        for chunk in (run, *env.values(), *with_.values()):
            text = str(chunk)
            for name in inputs:
                if f"inputs.{name}" in text:
                    used.add(name)
    # python-version is consumed by setup-python's `with`, count it
    setup = next(s for s in data["runs"]["steps"] if "setup-python" in s.get("uses", ""))
    if "python-version" in str(setup.get("with", {})):
        used.add("python-version")
    missing = inputs - used
    assert not missing, f"declared inputs never used: {missing}"


def test_action_passes_only_real_cli_flags():
    """every --flag in the action's run script must be one `repowiki scan` accepts."""
    data = _load(ACTION_YML)
    run_script = next(
        s["run"] for s in data["runs"]["steps"] if "repowiki scan" in (s.get("run") or "")
    )
    flags_used = {
        token.lstrip("$").rstrip("\\")
        for token in run_script.split()
        if token.startswith("--")
    }
    # remove placeholder flags
    flags_used = {f for f in flags_used if not any(c in f for c in "{}$")}

    help_text = CliRunner().invoke(cli, ["scan", "--help"]).output
    for flag in flags_used:
        assert flag in help_text, f"action passes {flag} but `repowiki scan` doesn't accept it"


def test_example_workflow_parses():
    data = _load(EXAMPLE_WF)
    assert data["name"] == "Update wiki on PR"
    # PyYAML parses bare 'on' as boolean True; check both spellings
    triggers = data.get("on") or data.get(True)
    assert triggers is not None and "pull_request" in triggers
    assert "permissions" in data
    assert data["permissions"]["contents"] == "write"


def test_example_workflow_references_local_action():
    data = _load(EXAMPLE_WF)
    job = data["jobs"]["update-wiki"]
    uses_action = next(
        s["uses"] for s in job["steps"] if s.get("uses", "").endswith("repowiki-scan")
    )
    # path-relative use of the composite action shipped in this repo
    assert uses_action == "./.github/actions/repowiki-scan"
