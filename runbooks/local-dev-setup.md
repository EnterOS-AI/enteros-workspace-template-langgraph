# Runbook: Local Development Setup — langgraph Workspace Template

Use this runbook to set up a local development environment for the langgraph workspace
template. It covers cloning, dependency installation, running the adapter outside
Docker, overriding config for dev, building the container, and diagnosing common
problems.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | 3.12 recommended |
| pip | 23+ | |
| Docker | 24+ | |
| Docker Compose | v2 (standalone or compose plugin) | |
| Git | 2.40+ | |
| Access to Molecule platform | Token with `workspace:dev` scope | |

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/your-org/molecule-ai-workspace-template-langgraph.git
cd molecule-ai-workspace-template-langgraph
```

Always branch off `main` for local development:

```bash
git checkout -b feat/your-feature-name
```

---

## Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

If you encounter dependency conflicts with an existing virtual environment, create an
isolated one:

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

Verify langgraph is importable:

```bash
python -c "import langgraph; print(langgraph.__version__)"
```

---

## Step 3 — Configure Environment Variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env.local
```

Edit `.env.local`:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
MOLECULE_PLATFORM_URL=https://platform.molecule.ai
MOLECULE_WORKSPACE_ID=ws-dev-local

# Optional — needed only when using persisted checkpointing
CHECKPOINT_DB_URL=postgresql://langgraph:langgraph@localhost:5432/langgraph_checkpoint

# Optional — override adapter log level
LOG_LEVEL=DEBUG
```

> **Security note:** Never commit `.env.local` to version control. It is gitignored
> by the template's `.gitignore`.

---

## Step 4 — Dev Overrides in `config.yaml`

The `config.yaml` shipped in the repo is production-oriented. For local dev,
create `config.dev.yaml` that overrides specific fields:

```yaml
# config.dev.yaml — local development overrides
# Merge with config.yaml using the adapter's --config flag

runtime:
  checkpoint:
    backend: memory          # avoids needing postgres for local dev

model:
  temperature: 0.9           # more creative for exploration
  max_tokens: 4096           # faster turns, lower cost

observability:
  log_level: DEBUG
  heartbeat_interval_seconds: 10  # faster feedback during development
```

Apply dev overrides when running locally:

```bash
python adapter.py --config config.yaml --config-override config.dev.yaml
```

The adapter merges `config.dev.yaml` on top of `config.yaml`, with dev values winning
for any conflicting keys.

---

## Step 5 — Run the Adapter Locally

Start the adapter in foreground mode:

```bash
python adapter.py
```

Expected startup output:

```
[molecule.adapter] INFO  — resolved config schema_version=1.1
[molecule.adapter] INFO  — initialising langgraph runtime version=0.4.2
[molecule.adapter] INFO  — loading skills from: /opt/molecule/skills
[molecule.adapter] DEBUG — skill manifest loaded: code_interpreter (langgraph)
[molecule.adapter] DEBUG — skill manifest loaded: browser_search (langgraph)
[molecule.adapter] INFO  — HEARTBEAT emitter active (interval=10s)
[molecule.adapter] INFO  — workspace ready, polling https://platform.molecule.ai/api/v1/tasks
```

Press `Ctrl+C` to stop. For background operation:

```bash
nohup python adapter.py > adapter.log 2>&1 &
```

---

## Step 6 — Test the Docker Build

Build the dev image:

```bash
docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t molecule-langgraph-workspace:dev \
  .
```

Run a smoke test (adapter starts and emits heartbeat):

```bash
docker run --rm \
  --env-file .env.local \
  -e LANGGRAPH_CHECKPOINT_NS=local-dev \
  molecule-langgraph-workspace:dev \
  python -c "
from adapter import MoleculeLanggraphAdapter
a = MoleculeLanggraphAdapter()
a.load_config()
print('smoke test PASSED')
"
```

Full Docker Compose stack (adapter + postgres for checkpointing):

```bash
docker compose up --build
```

Logs:

```bash
docker compose logs -f workspace
```

Teardown:

```bash
docker compose down -v
```

---

## Common Issues Table

| Symptom | Likely Cause | Resolution |
|---|---|---|
| `ModuleNotFoundError: No module named 'langgraph'` | `requirements.txt` not installed | Run `pip install -r requirements.txt` |
| `ValidationError: config schema version '1.0' is not supported` | `schema_version` in `config.yaml` is too old | Update `schema_version` to match platform minimum |
| `AttributeError: module 'langgraph' has no attribute 'prebuilt'` | langgraph version mismatch | Verify `langgraph` version: `pip show langgraph`; align with platform runtime |
| Adapter starts but never receives tasks | Wrong `MOLECULE_PLATFORM_URL` or token expired | Check URL; refresh token: `echo $MOLECULE_TOKEN \| head -c 20` |
| HEARTBEAT never emitted (platform shows "silent") | langgraph < 0.3.8 without heartbeat channel | Upgrade langgraph or add `channels=["heartbeat"]` to StateGraph |
| `postgresql.errors.ConnectionRefused` on startup | `CHECKPOINT_DB_URL` points to unreachable postgres | Ensure postgres is running (`docker compose up -d checkpoint-db`) or set `backend: memory` in dev overrides |
| `docker build` fails with `Step 5/12: RUN pip install...` | Network / pip index issue | Proxy through corporate firewall or mirror: `pip install --index-url https://pypi.org/simple/ -r requirements.txt` |
| `docker run` exits immediately with code 0 | `ANTHROPIC_API_KEY` not set | Pass `--env-file .env.local` or `-e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY` |

---

## IDE Setup (VS Code)

```json
// .vscode/settings.json — create in workspace root
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "files.insertFinalNewline": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff"
  }
}
```

The template includes a `.vscode/launch.json` for attaching the debugger to the
running adapter process (requires `debugpy` in dev dependencies).
