# agent-system

Universal filesystem-based orchestration package for Codex CLI profile agents.

The package defines a deterministic operating model for taking a project from initial TZ intake through requirements, design, implementation, audit, testing, setup, run, launch, documentation, handover, and final acceptance. It is project-agnostic: project details belong in project input, runtime state, task packets, and profile-specific work products, not in the universal core.

## Start file

Start an orchestrator with:

```text
agent-system/00_start/ORCHESTRATOR_START.md
```

That file is the package entry point. It directs the orchestrator to load its role, runtime loop, filesystem governance, state transition rules, current runtime state, and next action before dispatching any profile agent.

## Operating model

The core execution pattern is:

```text
TASK_PACKET -> profile agent -> RESULT -> auditor agent -> AUDIT_RESULT -> POST_AUDIT_GIT_CHECKPOINT
```

The orchestrator coordinates work, but it does not perform profile-agent tasks or audit its own output. Each bounded task is assigned to exactly one fresh-context profile agent. The agent returns a structured `RESULT`, the matching auditor reviews it, and only an audit pass can advance accepted package or project state.

The filesystem is the source of truth. Runtime state, gates, registries, logs, task packets, results, audit results, handoffs, and accepted artifacts are represented as files governed by the package rules.

## Lifecycle

The universal lifecycle is documented in:

```text
agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
```

Stage documents define the gates and responsibilities for:

```text
BOOTSTRAP -> REQUIREMENTS -> DESIGN -> IMPLEMENTATION -> TESTING -> SETUP -> RUN -> LAUNCH -> HANDOVER
```

The lifecycle supports universal project flow without embedding a business domain. Setup, run, launch, and handover have dedicated gates and checklist templates so operational readiness is tracked separately from implementation.

## Roles

Role instructions live in `agent-system/01_roles/`.

The package includes the orchestrator role, implementation and review roles, documentation and testing roles, plus lifecycle roles for requirements analysis, setup/operations, and release management. Role files define authority boundaries. Profile agents must follow their task packet, read only required docs, change only allowed files, and return the current `AGENT_RESULT_TEMPLATE` structure.

## Runtime governance

Runtime and governance rules live in `agent-system/02_runtime/`.

Key rules cover:

- allowed orchestrator actions;
- action/state semantics;
- state transitions;
- runtime loop behavior;
- filesystem governance;
- handoff protocol;
- accepted-state locking;
- violation recovery;
- post-audit Git checkpoint requirements.

Validation rules live in `agent-system/09_validators/` and define checks for task packets, results, transitions, runtime consistency, Git checkpoint readiness, and validator specification.

## Templates, state, and logs

Templates in `agent-system/03_templates/` define task packets, agent results, handoffs, owner decisions, evidence matrices, findings registers, setup tasks, smoke checks, launch readiness checks, and handover checks.

Runtime state templates in `agent-system/04_state/` define the project state, current gate, next action, accepted artifacts registry, and task registry. Log templates in `agent-system/06_logs/` define agent results, orchestrator events, and status summaries.

## Profiles

Project profiles are optional extensions in `agent-system/08_profiles/`.

Profiles help the orchestrator select relevant role emphasis, evidence expectations, and lifecycle checks for common project types. They do not replace the core runtime, do not weaken governance, and do not introduce domain terms into the universal package.

Available profile documents include:

```text
generic
backend_api
frontend_app
fullstack_app
cli_tool
browser_automation
data_pipeline
infra
parser
documentation_only
telegram_bot
```

## Git checkpoint

Accepted work requires a post-audit Git checkpoint. The checkpoint is orchestrator-owned and runs only after the matching auditor returns `STATUS: pass`.

Required checkpoint behavior:

```text
auditor pass -> commit accepted changes -> push -> record commit hash -> proceed
auditor fail -> no commit -> no push -> correction task
blocked -> wait for owner or prerequisite task
gap -> owner decision protocol
```

Profile agents do not commit or push. Auditors do not replace the checkpoint. Failed audit artifacts are not committed as accepted package state.

## Package version

Active package version constants are defined in:

```text
agent-system/PACKAGE_VERSIONING.md
```

Governance and package changes are recorded in:

```text
agent-system/GOVERNANCE_CHANGELOG.md
```

Current v1.2.0 tuple:

```text
CURRENT_PACKAGE_VERSION: 1.2.0
CURRENT_GOVERNANCE_RULESET_VERSION: 1.2.0
CURRENT_RUNTIME_SCHEMA_VERSION: 1.1.0
```

## Examples

Use the package by giving the orchestrator the start file and owner-provided input, then letting the orchestrator dispatch bounded tasks:

```text
START_FILE: agent-system/00_start/ORCHESTRATOR_START.md
PROJECT_INPUT: owner-provided TZ or other input outside agent-system/
NEXT_ACTION: create_agent with a bounded task packet
```

Example task flow:

```text
1. Orchestrator reads runtime state and next action.
2. Orchestrator dispatches one profile agent with one task packet.
3. Profile agent reads required docs, changes only allowed files, and returns RESULT.
4. Orchestrator validates RESULT shape and dispatches the matching auditor.
5. Auditor returns audit result.
6. On audit pass, orchestrator runs the post-audit Git checkpoint.
7. On audit fail, orchestrator creates a correction task without committing failed work.
```

This repository package does not claim a separate CLI wrapper. It is an instruction, governance, template, lifecycle, and validation package for Codex CLI orchestration.
