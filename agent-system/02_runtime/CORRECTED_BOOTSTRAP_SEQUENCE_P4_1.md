# CORRECTED_BOOTSTRAP_SEQUENCE_P4_1

## Purpose

This document summarizes the corrected P4.1 bootstrap/runtime sequence for
workspace initialization, first profile-agent dispatch, derived runtime views,
and post-RESULT lifecycle routing. It is a cross-reference aid for the
authoritative rules in `ORCHESTRATOR_RUNTIME_LOOP.md`,
`PROFILE_AGENT_LIFECYCLE.md`, `FILESYSTEM_GOVERNANCE.md`, and
`WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_HOTFIX_CONTRACT.md`.

## Package Repository Checks

The package repository is checked in package mode:

```bash
python3 agent-system/tools/aso/aso.py status --root . --mode package
python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
```

Root-level `project-input/`, `project-runtime/`, `project-archive/`, and
`.venv/` are local artifacts and must not become tracked package state.

## Workspace Bootstrap Checks

Generated or initialized project workspaces are checked in workspace mode:

```bash
aso state render --root /path/to/project --confirm-write
aso status --root /path/to/project --mode workspace
aso lint --root /path/to/project --mode workspace --strict
aso doctor --root /path/to/project --mode workspace --strict
```

Package mode against a workspace root is invalid. The operator must switch to
`--mode workspace` instead of adding package-only files such as
`pyproject.toml` or `.github/workflows/` to the generated workspace.

## Runtime State Materialization

Runtime Schema `3.1.0` JSON sidecars under `project-runtime/state/` are
canonical. Human-readable `project-runtime/*.md` files are derived
compatibility views.

After state initialization or sidecar repair, materialize views with:

```bash
aso state render --root /path/to/project --confirm-write
```

Derived views must declare their source JSON sidecar and must not be edited as
canonical state.

## First Bootstrap Dispatch

The first profile-agent dispatch requires exactly one valid bootstrap task
packet:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

If owner input is incomplete, ambiguous, or the orchestrator is unsure, the
first target is `requirements_analyst`:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md
```

If owner input is sufficiently structured for direct design without guessing,
the first target may be `solution_architect`:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_SOLUTION_ARCHITECT_001.md
```

`TASK_PACKET: NONE` is forbidden for first profile-agent dispatch.
`project-runtime/HANDOFF_BOOTSTRAP.md` is not a task packet substitute.

## RESULT To Audit Route

After a profile-agent RESULT is recorded, the orchestrator must record logical
agent termination before audit routing:

```bash
aso lifecycle terminate-agent \
  --root /path/to/project \
  --from-result project-runtime/results/worker/RESULT_TASK_ID_ATTEMPT_001.md \
  --confirm-write
```

The required order is:

```text
RESULT_RECEIVED
AGENT_TERMINATED
AUDIT_ROUTE_READY
```

`LINT_AGENT_003` must remain a blocker when the termination event is missing,
has the wrong task ID, has the wrong result reference, or is created without a
valid RESULT.
