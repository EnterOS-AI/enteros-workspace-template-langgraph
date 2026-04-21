# Known Issues — langgraph Workspace Template

This document tracks unresolved and partially-resolved issues that are known to
occur when running this workspace template. Each entry includes the symptom,
affected versions, workaround, and (where applicable) a link to the upstream or
internal tracker.

---

## 1. langgraph Version Drift Between Template and Platform

**Severity:** High
**Affects:** All template versions prior to aligning `langgraph` pin in
`requirements.txt` with the platform's bundled langgraph runtime.

**Symptom:**
The adapter initialises the langgraph `StateGraph` and immediately crashes with:

```
AttributeError: module 'langgraph' has no attribute 'prebuilt'
```

or, in newer platform releases that bundle langgraph 0.4+:

```
ValueError: Unexpected keyword argument 'store' — this graph does not use checkpointers
```

**Root cause:**
The template pins `langgraph>=0.2.0,<0.3.0` but the platform runtime ships with
`langgraph 0.4.x`. The graph API (constructor args, `checkpointer` vs `store`,
prebuilt agent) changed between 0.2 and 0.4.

**Workaround:**
Edit `requirements.txt` to match the platform's bundled langgraph version:

```bash
# Query the platform for its runtime version
curl -s https://platform.molecule.ai/api/v1/workspaces/{id}/runtime-info \
  -H "Authorization: Bearer $MOLECULE_TOKEN" | jq '.langgraph_version'
```

Then update `requirements.txt`:

```
langgraph==<reported_version>
```

**Fix:** The template maintainer will update the pin in every template release that
aligns with a platform upgrade. Always check the release notes before updating the
platform.

---

## 2. `system-prompt.md` Gets Reset on Template Update

**Severity:** Medium
**Affects:** Users who customise `system-prompt.md` directly in the workspace.

**Symptom:**
After pulling a new template version (e.g. `git pull`), the agent's behaviour
changes unexpectedly even though no `config.yaml` changes were made. On inspection,
`system-prompt.md` has been overwritten with the template version.

**Root cause:**
`system-prompt.md` is a template-managed file. When the platform rebuilds the
workspace container it copies the file from the registered template tag, overwriting
any local customisations.

**Workaround — Option A (recommended):**
Do not edit `system-prompt.md` directly. Instead, inject custom instructions via
the `MOLECULE_SYSTEM_PROMPT_OVERRIDE` environment variable. The adapter prepends
this value to the loaded `system-prompt.md` at startup:

```bash
export MOLECULE_SYSTEM_PROMPT_OVERRIDE="You are a helpful assistant with the following additional context: ..."
```

**Workaround — Option B:**
Fork the template and pin to a specific tag. Apply your customisations as patches
on top of that tag.

**Fix:** A future platform release will support a `system_prompt_overlay` field in
`config.yaml` so customisation survives template updates (tracked in internal
ticket MOL-4821).

---

## 3. HEARTBEAT Not Wired in Some langgraph Versions

**Severity:** Medium
**Affects:** Template versions `≤ v1.0.3` running against `langgraph < 0.3.8`.

**Symptom:**
The platform's activity dashboard shows the workspace as "silent" even though the
agent is actively processing tasks. No HEARTBEAT events arrive at the platform.

The adapter log shows:

```
HEARTBEAT emitter disabled: no 'interrupt' channel in graph channels
```

**Root cause:**
In langgraph < 0.3.8, the mechanism to emit out-of-band events from within a graph
step required using a dedicated `"heartbeat"` channel on the `StateGraph`. The adapter
code looked for this channel but did not create it automatically. In 0.3.8+ the
preferred approach is to use `Interrupts`.

**Workaround:**
Add the heartbeat channel explicitly when constructing the graph in `adapter.py`:

```python
builder = StateGraph(AgentState, channels=["heartbeat"])
# ...
graph = builder.compile(interrupt_before=["heartbeat_node"])
```

Or upgrade langgraph to `≥ 0.3.8` where the adapter's auto-wiring logic handles this.

**Fix:** Merged in template v1.0.4. Upgrade to v1.0.4 or later to resolve.

---

## 4. `config.yaml` Schema Mismatch After Platform Upgrade

**Severity:** High
**Affects:** Any workspace that pins `schema_version` below the minimum supported by
the platform after a platform upgrade.

**Symptom:**
The adapter fails to start with:

```
ValidationError: config schema version '1.0' is not supported.
Minimum supported version: '1.1'. Please update config.yaml.
```

**Root cause:**
The Molecule platform increments the minimum supported `schema_version` when it makes
backward-incompatible changes to the config format. Workspaces that pin an older
schema version will fail validation.

**Workaround:**
Immediately after a platform upgrade, edit `config.yaml` and update the
`schema_version` field to the new minimum reported in the platform's release notes:

```yaml
schema_version: "1.1"   # change from "1.0" to "1.1"
```

**Prevention:**
The release checklist in `CLAUDE.md` includes a step to review the platform's
minimum schema version before tagging a new template release. Always test against
the target platform version before releasing.

**Fix:** Once `schema_version` is updated, the adapter starts normally. No adapter
code changes are required for schema-only bumps.
