"""tests for repowiki.llm.prompts: history handling, repair flow."""

from __future__ import annotations

from repowiki.llm.prompts import (
    _trim_history,
    build_architecture_prompt,
    build_chat_prompt,
    build_repair_prompt,
    missing_required_keys,
)


def test_chat_prompt_includes_recent_history():
    history = [
        {"role": "user", "content": "what is foo"},
        {"role": "assistant", "content": "foo is a bar"},
        {"role": "user", "content": "and bar?"},
        {"role": "assistant", "content": "bar is baz"},
    ]
    msgs = build_chat_prompt("what about qux", "ctx", history=history)
    roles = [m["role"] for m in msgs]
    assert roles[0] == "system"
    assert roles[-1] == "user"  # the new question
    # history is preserved in chronological order
    user_turns = [m for m in msgs if m["role"] == "user"]
    assert user_turns[0]["content"] == "what is foo"
    assert user_turns[-1]["content"].endswith("what about qux")


def test_chat_prompt_filters_empty_turns():
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": ""},  # streaming placeholder
        {"role": "user", "content": "anyone there"},
        {"role": "assistant", "content": "yes"},
    ]
    msgs = build_chat_prompt("q", "ctx", history=history)
    contents = [m["content"] for m in msgs]
    assert "" not in contents  # placeholder dropped


def test_trim_history_keeps_n_pairs():
    history = []
    for i in range(10):
        history.append({"role": "user", "content": f"u{i}"})
        history.append({"role": "assistant", "content": f"a{i}"})

    kept = _trim_history(history, max_turns=3)
    # should retain the last 3 user+assistant pairs
    users = [m for m in kept if m["role"] == "user"]
    assert len(users) == 3
    assert users[0]["content"] == "u7"


def test_missing_required_keys_detects_blank_strings():
    data = {"name": "foo", "one_liner": "", "description": "x"}
    assert missing_required_keys(data, ["name", "one_liner"]) == ["one_liner"]


def test_missing_required_keys_non_dict_returns_all():
    assert missing_required_keys(None, ["a", "b"]) == ["a", "b"]
    assert missing_required_keys("oops", ["a", "b"]) == ["a", "b"]


def test_build_repair_prompt_carries_original_context():
    original = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    repaired = build_repair_prompt(original, "bad output", ["name"])
    assert repaired[0:2] == original
    assert repaired[2]["role"] == "assistant"
    assert repaired[2]["content"] == "bad output"
    assert repaired[3]["role"] == "user"
    assert "name" in repaired[3]["content"]


def test_architecture_prompt_omits_file_tree():
    # The architecture prompt now relies solely on module summaries -- the
    # file_tree argument is accepted for signature compatibility but must not
    # leak into the actual user message (or the LLM hallucinates components
    # that aren't represented by any analyzed module).
    file_tree = "src/\n  foo.py\n  bar.py\n"
    summaries = "- **core** (3 files): does core stuff"
    msgs = build_architecture_prompt(file_tree, summaries)
    user_content = next(m["content"] for m in msgs if m["role"] == "user")
    assert "## Module Summaries" in user_content
    assert summaries in user_content
    assert "File Tree" not in user_content
    assert "foo.py" not in user_content
    # The system message enforces module-derived components.
    sys_content = next(m["content"] for m in msgs if m["role"] == "system")
    assert "module summaries" in sys_content.lower()
