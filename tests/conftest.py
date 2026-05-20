"""Shared pytest fixtures + import shims for the LangGraph adapter test suite.

`adapter.py` imports at module load:
  - molecule_runtime.adapters.base (BaseAdapter, AdapterConfig)
  - a2a.server.agent_execution (AgentExecutor)

In production those arrive transitively via molecule-ai-workspace-runtime.
The CI runner only installs `pytest pytest-asyncio pyyaml`, so the import
chain would fail with ModuleNotFoundError before any test collects.

Pattern mirrors molecule-ai-workspace-template-claude-code/tests/conftest.py
(canonical), stripped of claude-code-specific stubs.
"""

import os
import sys
import types
from dataclasses import dataclass


@dataclass
class _StubAdapterConfig:
    runtime_config: object = None
    config_path: str = "/tmp/configs"
    system_prompt: str = ""
    heartbeat: object = None
    model: str = ""


class _StubBaseAdapter:
    pass


def _install_stubs() -> None:
    """Install the smallest set of import shims that adapter.py needs."""
    if "molecule_runtime" not in sys.modules:
        mr = types.ModuleType("molecule_runtime")
        mr.adapters = types.ModuleType("molecule_runtime.adapters")
        mr.adapters.base = types.ModuleType("molecule_runtime.adapters.base")
        mr.adapters.base.BaseAdapter = _StubBaseAdapter
        mr.adapters.base.AdapterConfig = _StubAdapterConfig
        sys.modules["molecule_runtime"] = mr
        sys.modules["molecule_runtime.adapters"] = mr.adapters
        sys.modules["molecule_runtime.adapters.base"] = mr.adapters.base
    if "a2a" not in sys.modules:
        a2a = types.ModuleType("a2a")
        a2a.server = types.ModuleType("a2a.server")
        a2a.server.agent_execution = types.ModuleType("a2a.server.agent_execution")
        a2a.server.agent_execution.AgentExecutor = type("AgentExecutor", (), {})
        sys.modules["a2a"] = a2a
        sys.modules["a2a.server"] = a2a.server
        sys.modules["a2a.server.agent_execution"] = a2a.server.agent_execution


# Run at conftest import time — pytest collects conftest.py before any
# test module, so the stubs are in sys.modules before `from adapter
# import ...` ever executes.
_install_stubs()

# adapter.py lives in the parent dir of tests/. pytest's
# `--import-mode=importlib` + tests/pytest.ini anchoring rootdir at
# tests/ means the parent isn't on sys.path automatically.
_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)
