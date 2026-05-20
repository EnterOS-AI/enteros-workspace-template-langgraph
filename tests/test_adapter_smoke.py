"""Smoke test: adapter.py imports cleanly under the conftest stubs.

This pins the contract that `from adapter import LangGraphAdapter` works
with only the minimal stub shims in conftest.py — i.e. without any
production runtime dependency (molecule_runtime, a2a-sdk, langgraph)
being pip-installed. The corresponding production-deps import path is
exercised by the validate-runtime job, which DOES `pip install -r
requirements.txt` before importing adapter.py.

If a future change to adapter.py introduces a new top-level import not
covered by the conftest stubs, this test fails before any other test in
the suite even collects — surfacing the gap immediately.
"""

from __future__ import annotations


def test_adapter_imports() -> None:
    from adapter import LangGraphAdapter

    assert LangGraphAdapter.name() == "langgraph"
    assert LangGraphAdapter.display_name() == "LangGraph"
