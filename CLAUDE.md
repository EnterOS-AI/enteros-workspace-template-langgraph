# Molecule AI Workspace Template — langgraph

## Purpose

This is a **workspace template** for the langgraph runtime. It provides a pre-configured
workspace environment (Dockerfile, config.yaml, adapter.py, system-prompt.md, and
supporting files) that Molecule AI agents run inside. It is NOT a plugin — it has no
`plugin.yaml` and no `rules/` directory.

Use this template when you want to bootstrap a langgraph-based agentic workflow within
the Molecule platform.

---

## Key Files and Their Roles

| File | Role |
|---|---|
| `config.yaml` | Runtime configuration: schema version, model, runtime (langgraph), tool registry, skill paths, env-var bindings |
| `adapter.py` | Thin bridge between the Molecule platform and the langgraph runtime. Responsible for initialising the graph, routing messages, streaming results, and forwarding HEARTBEAT events |
| `system-prompt.md` | System-level instructions injected into every agent turn (identity, constraints, output format) |
| `AGENTS.md` | Defines the set of named agents (nodes) in the langgraph graph, their roles, and how they are wired together |
| `BOOTSTRAP.md` | Startup sequence: how the adapter initialises state, loads persisted checkpoints, and validates the graph |
| `HEARTBEAT.md` | Describes the HEARTBEAT protocol — when the adapter emits a heartbeat, what payload it carries, and how the platform consumes it |
| `SOUL.md` | Core philosophy / "identity document" for the workspace — values, reasoning style, tone |
| `TOOLS.md` | Catalog of tools available to agents, including descriptions, parameter schemas, and usage conventions |
| `requirements.txt` | Python dependencies (langgraph SDK, platform client, LLM client, utilities) |
| `Dockerfile` | Container image definition for the runtime environment |

---

## Runtime Configuration Conventions

- All runtime configs live in `config.yaml` at the workspace root.
- The top-level `schema_version` field must match the platform's supported schema range
  (e.g. `1.0` – `1.2`; see the platform release notes).
- Environment-variable substitution uses `${VAR_NAME}` syntax inside string values.
- Sections: `runtime`, `model`, `tools`, `skills`, `checkpoint`, `observability`.

```yaml
schema_version: "1.1"

runtime:
  name: langgraph
  version: "0.4"          # must match installed langgraph package major.minor
  checkpoint:
    backend: memory       # "memory" for dev, "postgres" for prod
    conn: "${CHECKPOINT_DB_URL}"

model:
  provider: anthropic
  name: claude-sonnet-4-6
  max_tokens: 8192
  temperature: 0.7
  system_prompt_file: system-prompt.md

tools:
  registry: builtin
  allowed_tools:
    - browser_search
    - code_interpreter
    - file_read
    - file_write
    - bash

skills:
  load_paths:
    - /opt/molecule/skills
  auto_init: true

observability:
  heartbeat_interval_seconds: 30
  log_level: INFO
```

---

## Environment Variables Expected

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | API key for the LLM provider |
| `CHECKPOINT_DB_URL` | No | Postgres connection string for langgraph checkpoint persistence (defaults to in-memory) |
| `MOLECULE_PLATFORM_URL` | Yes | Base URL of the Molecule platform (e.g. `https://platform.molecule.ai`) |
| `MOLECULE_WORKSPACE_ID` | Yes | Workspace instance ID assigned by the platform |
| `LANGGRAPH_CHECKPOINT_NS` | No | Namespace string used to prefix checkpoint keys |
| `LOG_LEVEL` | No | Python log level override (`DEBUG`, `INFO`, `WARNING`) |

---

## Skill Loading

Skills are loaded at startup from paths declared in `config.yaml` under `skills.load_paths`.
The adapter calls `molecule.skills.load(path)` for each path before entering the run loop.
Only skills whose manifest (`skill.yaml`) declares compatibility with `langgraph` runtime
are activated. Skills that declare `runtime: "*"` are always loaded.

Auto-initialisation is controlled by `skills.auto_init: true` (default). Set to `false`
to disable automatic skill loading and manage loading manually in `BOOTSTRAP.md`.

---

## Development Setup

### Prerequisites

- Python 3.11+
- Docker 24+ / Docker Compose v2
- Git

### Clone and install

```bash
git clone https://github.com/your-org/molecule-ai-workspace-template-langgraph.git
cd molecule-ai-workspace-template-langgraph
pip install -r requirements.txt
```

### Run adapter locally (outside Docker)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export MOLECULE_PLATFORM_URL="https://platform.molecule.ai"
export MOLECULE_WORKSPACE_ID="ws-dev-local"

python adapter.py
```

The adapter will print the resolved config on startup and begin polling for agent tasks.

### Test the Docker build

```bash
docker build -t molecule-langgraph-workspace:dev .
docker run --rm \
  -e ANTHROPIC_API_KEY \
  -e MOLECULE_PLATFORM_URL \
  -e MOLECULE_WORKSPACE_ID \
  molecule-langgraph-workspace:dev
```

### Docker Compose (full local stack)

```yaml
# docker-compose.yml (add to workspace root)
version: "3.9"
services:
  workspace:
    build: .
    env_file: .env.local
    volumes:
      - ./config.yaml:/workspace/config.yaml:ro
    depends_on:
      - checkpoint-db
  checkpoint-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: langgraph_checkpoint
      POSTGRES_USER: langgraph
      POSTGRES_PASSWORD: langgraph
    ports:
      - "5432:5432"
```

Run with:

```bash
docker compose up --build
```

---

## Testing

| Test type | Command | Notes |
|---|---|---|
| Unit (adapter) | `pytest tests/test_adapter.py -v` | Mocks the platform API; tests config parsing, graph init |
| Unit (graph wiring) | `pytest tests/test_graph.py -v` | Verifies agent nodes and edges are correctly wired |
| Integration | `docker compose -f compose.test.yml up --abort-on-container-exit` | Full stack; requires `.env.test` with live API keys |
| Lint | `ruff check .` | Must pass before release |

---

## Release Process

1. **Update `config.yaml` schema version** to match the target platform release:

   ```yaml
   schema_version: "1.2"   # bump to match platform
   ```

2. **Bump runtime version pin** in `requirements.txt`:

   ```
   langgraph>=0.4.0,<0.5.0
   ```

3. **Run the full test suite** — all tests must pass.

4. **Tag the release**:

   ```bash
   git tag -a v1.2.0 -m "release: align with platform schema 1.2"
   git push origin main
   git push origin v1.2.0
   ```

5. **Update CHANGELOG.md** with a summary of config/schema changes and any adapter API
   changes.

---

## Note: This Is a Workspace Template, Not a Plugin

This template does **not** contain a `plugin.yaml` or a `rules/` directory. Those
artifacts belong to Molecule plugins (which extend the agent's capability set at
runtime). A workspace template only provides the **environment** in which the agent
runs. If you need to add new capabilities, create a plugin and reference it via the
`skills` section of `config.yaml`.
