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

Research dependencies use a controlled extension of the same sequence:

```text
requester -> research_dependency task -> research RESULT -> auditor -> audit pass -> requester continuation
```

Research output must not return to requester continuation before independent
audit pass. Requester return routing is governed by
[REQUESTER_RETURN_PROTOCOL.md](02_runtime/REQUESTER_RETURN_PROTOCOL.md), and
design-specific research is governed by
[DESIGN_RESEARCH_LOOP.md](07_lifecycle/DESIGN_RESEARCH_LOOP.md).

## Lifecycle

The universal lifecycle is documented in:

```text
agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
```

The lifecycle order is:

```text
BOOTSTRAP -> REQUIREMENTS -> DESIGN -> IMPLEMENTATION -> AUDIT -> TESTING -> SETUP -> RUN -> LAUNCH -> DOCUMENTATION -> HANDOVER -> FINAL_ACCEPTANCE
```

The documentation stage is defined in [DOCUMENTATION_STAGE.md](07_lifecycle/DOCUMENTATION_STAGE.md).

Dedicated stage documents define gates and responsibilities where a stage is represented by a lifecycle file. The lifecycle supports universal project flow without embedding a business domain. Setup, run, launch, documentation, and handover have dedicated gates and checklist templates so operational readiness and accepted documentation are tracked separately from implementation.

## Roles

Role instructions live in the [01_roles/](01_roles/) package directory.

The package includes the orchestrator role, implementation and review roles, documentation and testing roles, plus lifecycle roles for requirements analysis, setup/operations, and release management. Role files define authority boundaries. Profile agents must follow their task packet, read only required docs, change only allowed files, and return the current `AGENT_RESULT_TEMPLATE` structure.

## Runtime governance

Runtime and governance rules live in the [02_runtime/](02_runtime/) package
directory.

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

Validation rules live in the [09_validators/](09_validators/) package
directory and define checks for task packets, results, transitions, runtime
consistency, Git checkpoint readiness, cross-link coverage, and validator
specification. Cross-link validation is documented in
[CROSS_LINK_VALIDATION_RULES.md](09_validators/CROSS_LINK_VALIDATION_RULES.md).
Research return validation is documented in
[RESEARCH_RETURN_VALIDATION_RULES.md](09_validators/RESEARCH_RETURN_VALIDATION_RULES.md).
Reasoning-level validation is documented in
[REASONING_LEVEL_VALIDATION_RULES.md](09_validators/REASONING_LEVEL_VALIDATION_RULES.md).

## Templates, state, and logs

Templates in the [03_templates/](03_templates/) package directory define task
packets, agent results, handoffs, owner decisions, evidence matrices, findings
registers, setup tasks, smoke checks, launch readiness checks, handover checks,
research requests, research results, and design continuation tasks.

Runtime state templates in the [04_state/](04_state/) package directory define
the project state, current gate, next action, accepted artifacts registry, and
task registry. Log templates in the [06_logs/](06_logs/) package directory
define agent results, orchestrator events, and status summaries.

## Profiles

Project profiles are optional extensions in the
[08_profiles/](08_profiles/) package directory.

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

Canonical Git authority rule:

```text
Profile agents never commit or push.
Task packets cannot grant commit/push authority to profile agents.
Git checkpoint is orchestrator-owned only and runs only after auditor STATUS: pass.
```

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

Current v1.3.0 tuple:

```text
CURRENT_PACKAGE_VERSION: 1.3.0
CURRENT_GOVERNANCE_RULESET_VERSION: 1.3.0
CURRENT_RUNTIME_SCHEMA_VERSION: 1.2.0
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

Documentation-only examples and the final smoke checklist live in:

```text
agent-system/10_examples/MINIMAL_EXAMPLE_FIXTURE.md
agent-system/10_examples/EXPECTED_FLOW_EXAMPLE.md
agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
```

These examples demonstrate the generic TZ -> requirements/design -> task ->
audit -> checkpoint -> setup/run/launch/handover flow without requiring actual
deployment, credentials, external source repositories, or business-specific
implementation.

Final smoke coverage explicitly checks bootstrap requirements/design routing,
profile-role audit transitions, research dependency return routing, reasoning
level floors, minimal fixture schema alignment, profile-agent Git authority
prohibition, changelog traceability, schema sidecar linkage, STATUS_SUMMARY
sidecar policy, PROJECT_STATE semantic field parity, and runtime tuple
validation for `CURRENT_GATE.ACTION_SEMANTIC` and
`NEXT_ACTION.ACTION_SEMANTIC`.

This repository package does not claim a separate CLI wrapper. It is an instruction, governance, template, lifecycle, and validation package for Codex CLI orchestration.
