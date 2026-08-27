"""per-output-directory state for incremental wiki regeneration."""

from __future__ import annotations

import json
from pathlib import Path

STATE_FILENAME = ".repowiki-state.json"
STATE_VERSION = 1


def load_state(output_dir: str | Path) -> dict | None:
    """read the state file; None means the next run falls back to a full build."""
    try:
        state = json.loads((Path(output_dir) / STATE_FILENAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION:
        return None
    if not isinstance(state.get("pages"), dict):
        return None
    return state


def save_state(output_dir: str | Path, state: dict) -> None:
    path = Path(output_dir) / STATE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
