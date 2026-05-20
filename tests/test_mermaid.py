"""tests for repowiki.core.mermaid sanitizer."""

from __future__ import annotations

from repowiki.core.mermaid import describe_components, sanitize_mermaid
from repowiki.core.models import ArchitectureDiagram, Component


def test_component_well_formed_passthrough():
    text = "graph TD\n  A[Hello] --> B[World]"
    out = sanitize_mermaid(text, kind="component")
    assert out is not None
    assert out.splitlines()[0].startswith("graph TD")


def test_component_missing_header_gets_prefixed():
    text = "A[Foo] --> B[Bar]"
    out = sanitize_mermaid(text, kind="component")
    assert out is not None
    assert out.splitlines()[0].startswith("graph TD")
    assert "A[Foo] --> B[Bar]" in out


def test_sequence_well_formed_passthrough():
    text = "sequenceDiagram\n  A->>B: hi"
    out = sanitize_mermaid(text, kind="sequence")
    assert out is not None
    assert out.startswith("sequenceDiagram")


def test_sequence_missing_header_gets_prefixed():
    text = "  A->>B: hi"
    out = sanitize_mermaid(text, kind="sequence")
    assert out is not None
    assert out.startswith("sequenceDiagram")


def test_kind_mismatch_returns_none():
    # claimed "component" but body is a sequence diagram -> unrecoverable
    out = sanitize_mermaid("sequenceDiagram\n  A->>B: hi", kind="component")
    assert out is None


def test_empty_input_returns_none():
    assert sanitize_mermaid("", kind="component") is None
    assert sanitize_mermaid("   \n  ", kind="sequence") is None


def test_node_ids_with_dots_get_underscored():
    text = "graph TD\n  src.a[A] --> src.b[B]"
    out = sanitize_mermaid(text, kind="component")
    assert out is not None
    # the bracketed labels are preserved verbatim
    assert "[A]" in out and "[B]" in out
    # the dotted IDs are no longer present as-is
    assert "src.a" not in out
    assert "src.b" not in out


def test_describe_components_renders_components_and_flow():
    arch = ArchitectureDiagram(
        components=[
            Component(name="api", purpose="HTTP layer"),
            Component(name="db"),  # no purpose
        ],
        data_flow="Requests enter via api and persist through db.",
    )
    out = describe_components(arch)
    assert "**Components:**" in out
    assert "`api` — HTTP layer" in out
    assert "`db`" in out
    assert "**Flow:**" in out
    assert "persist through db" in out


def test_describe_components_empty_returns_empty_string():
    # No components and no data_flow -> nothing to render.
    arch = ArchitectureDiagram()
    assert describe_components(arch) == ""
