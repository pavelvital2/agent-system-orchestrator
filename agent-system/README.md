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

Profile-agent reuse is forbidden. The mandatory one agent = one task = one
RESULT policy, lifecycle states, required termination event, and logical
termination rules are documented in
[PROFILE_AGENT_LIFECYCLE.md](02_runtime/PROFILE_AGENT_LIFECYCLE.md).

The filesystem is the source of truth. Runtime state, gates, registries, logs, task packets, results, audit results, handoffs, and accepted artifacts are represented as files governed by the package rules.
The top-level taxonomy is documented in
[RUNTIME_FILE_TAXONOMY.md](02_runtime/RUNTIME_FILE_TAXONOMY.md):
`project-docs` is stable documentation, `project-runtime` is execution
state/artifacts, `project-input` is owner input, TZ, and upgrade packages, and
`project-archive` is superseded or deprecated workspace material.

Root-level `project-runtime/`, `project-input/`, and `project-archive/` are
generated workspace artifacts. They are expected in target workspaces or local
orchestration sessions. They are not shipped as active state in the package
repository.

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
- canonical JSON state preparation;
- runtime loop behavior;
- profile-agent lifecycle and termination;
- filesystem governance;
- runtime file taxonomy;
- handoff protocol;
- accepted-state locking;
- violation recovery;
- post-audit Git checkpoint requirements.

Validation rules live in the [09_validators/](09_validators/) package
directory and define checks for task packets, results, transitions, runtime
consistency, Git checkpoint readiness, cross-link coverage, and validator
specification. Cross-link validation is documented in
[CROSS_LINK_VALIDATION_RULES.md](09_validators/CROSS_LINK_VALIDATION_RULES.md).
Workspace identity validation is documented in
[WORKSPACE_IDENTITY_VALIDATION_RULES.md](09_validators/WORKSPACE_IDENTITY_VALIDATION_RULES.md).
Research return validation is documented in
[RESEARCH_RETURN_VALIDATION_RULES.md](09_validators/RESEARCH_RETURN_VALIDATION_RULES.md).
Reasoning-level validation is documented in
[REASONING_LEVEL_VALIDATION_RULES.md](09_validators/REASONING_LEVEL_VALIDATION_RULES.md).
Profile-agent lifecycle validation is documented in
[AGENT_LIFECYCLE_VALIDATION_RULES.md](09_validators/AGENT_LIFECYCLE_VALIDATION_RULES.md).
Solution architect design traceability and audit scoring are documented in
[DESIGN_TRACEABILITY_RULES.md](09_validators/DESIGN_TRACEABILITY_RULES.md)
and [DESIGN_REVIEW_RUBRIC.md](09_validators/DESIGN_REVIEW_RUBRIC.md).
Product capability gates, MVP readiness, and final acceptance distinctions are
documented in
[PRODUCT_CAPABILITY_GATE_POLICY.md](09_validators/PRODUCT_CAPABILITY_GATE_POLICY.md).

Future migration from Markdown runtime state to canonical JSON state is
specified in
[CANONICAL_JSON_STATE_PREPARATION.md](02_runtime/CANONICAL_JSON_STATE_PREPARATION.md).
In v0, Markdown runtime files remain authoritative and compatible.

## Safe workspace initialization

Use the governed initializer when copying the package into a new project
workspace:

```text
agent-system/scripts/init_project_workspace.sh \
  --target /path/to/project-workspace \
  --project-name "Example Project" \
  --project-slug example-project \
  --expected-remote https://github.com/OWNER/REPO.git \
  --expected-branch main
```

The initializer copies `agent-system/`, creates local bootstrap directories,
creates local generated workspace artifact roots such as `project-input/`,
`project-runtime/`, and `project-archive/`, and writes
`project-runtime/WORKSPACE_IDENTITY.md` plus `project-runtime/REPOSITORY_LOCK.md`.
It does not copy or reuse `.git`.

Do not clone or rename this package repository as a project workspace. If the
target already has `.git`, its origin and branch must match the expected remote
and branch before package files are copied. Repository lock acceptance requires
explicit expected remote and branch inputs; push remains disabled unless an
accepted repository lock explicitly allows it.

## ASO helper CLI

The package includes an experimental read-only ASO helper CLI at
`agent-system/tools/aso/aso.py`.

This Stage 3 safe automation diagnostics branch updates the active package
metadata to the governed `3.1.0` package/governance tuple with runtime schema
`3.0.0`. It preserves the read-only Stage 2 command surfaces and adds Stage 3
package synchronization diagnostics without adding live dispatch, mutation,
governed checkpoint execution, autonomous owner-decision approval, commit,
push, or publication authority.

Install the local console command from the repository root with:

```text
python3 -m pip install -e .
aso --help
```

The installed `aso` command is additive. Direct script execution remains
supported and should be used by compatibility checks:

```text
python3 agent-system/tools/aso/aso.py --help
```

Package repository checks use explicit package mode:

```text
python3 agent-system/tools/aso/aso.py status --root . --mode package
python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
```

Initialized project workspaces use explicit workspace mode:

```text
python3 agent-system/tools/aso/aso.py status --root /path/to/project --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /path/to/project --mode workspace --strict
python3 agent-system/tools/aso/aso.py doctor --root /path/to/project --mode workspace --strict
```

`aso doctor` inspects package command readiness in package mode and workspace
runtime, identity, repository lock, and checkpoint readiness signals in
workspace mode. It emits text output by default, supports `--json-out`, and
uses nonzero exit status for hard failures. `--strict` treats warnings as a
failed result.

The design validator checks solution architect design Markdown:

```text
python3 agent-system/tools/aso/aso.py validate-design path/to/DESIGN.md --root . --strict
```

It validates design contract coverage, traceability, assumptions/GAP
separation, downstream task readiness, acceptance criteria, testing strategy,
and product capability evidence. The context-pack validator checks bounded JSON
context packs:

```text
python3 agent-system/tools/aso/aso.py validate-context-pack path/to/CONTEXT_PACK.json --root . --strict
```

It validates required shape, context budget, archive/deprecated path rejection,
forbidden document checks, and required document existence under `--root`.

Stage 2 command surfaces are local, read-only, and offline:

```text
python3 agent-system/tools/aso/aso.py validate-rules --root . --strict
python3 agent-system/tools/aso/aso.py state verify --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-state.json
python3 agent-system/tools/aso/aso.py plan-next --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-plan.json
python3 agent-system/tools/aso/aso.py dashboard --root agent-system/tests/fixtures/state/valid_workspace --out /tmp/aso-stage2-dashboard.html
python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict --json-out /tmp/aso-stage2-checkpoint-preflight.json
```

`aso validate-rules` checks the packaged governance rule registry. `aso state
verify` compares Markdown runtime files with JSON sidecars and emits optional
JSON evidence. `aso plan-next` recommends the next orchestrator action as a
dry-run report only. `aso dashboard` renders escaped static HTML to stdout,
`/tmp`, or an explicit workspace `project-runtime/dashboard` path. `aso dag
render`, `aso context-pack build`, and `aso incident fixture` likewise write
generated render/proposal artifacts only to stdout, `/tmp`, or explicit
workspace runtime report/proposal directories; tracked package paths are
rejected with `ASO_OUTPUT_PATH_FORBIDDEN`. `aso checkpoint-preflight` inspects
checkpoint eligibility without staging, committing, pushing, or changing
runtime state.
The corrected state examples use
`agent-system/tests/fixtures/state/valid_workspace`; the dry-run plan evidence
uses the canonical next action value `CREATE_AGENT` without dispatching an
agent.

Stage 3 command surfaces are local, read-only, dry-run, or proposal-only. The
package-sync guard checks active package metadata and command surface
coherence:

```text
python3 agent-system/tools/aso/aso.py package-sync verify --root . --strict
```

`aso package-sync verify` is an inspection command. It reports version or
documentation drift and exits nonzero on strict mismatches. It does not repair
files, edit package state, initialize workspaces, stage changes, commit, push,
publish release artifacts, or approve cleanup.

Repeatable root targets are:

```text
make install
make test
make smoke
make doctor
make lint
make ci
```

`make test` runs the ASO command unit tests and package governance tests.
`make smoke` runs CLI help, package status, strict package lint, strict package
doctor, read-only package-sync verification, valid design/context-pack
fixtures, rule validation, state sidecar verification, dry-run next-action
planning, static dashboard rendering to `/tmp`, checkpoint preflight, and the
local Stage 3 diagnostics. `make ci` runs `test`, `smoke`, `doctor`, `lint`,
and `git diff --check`. The smoke and CI surfaces are local and diagnostic:
they must not require secrets, network credentials, real remotes, publishing
permissions, live service access, or live automation authority.

The helper supports read-only status, lint, doctor, package-sync verification,
design validation, context pack validation, rule validation, state
verification, dry-run next-action planning, static dashboard rendering,
checkpoint eligibility preflight, and archive verify inspection. Its read-only
behavior is part of the ASO boundary. It does not dispatch agents, mutate
package or workspace state, perform checkpoints, commit, or push. For package
lint compatibility, this boundary is also stated as: ASO does not provide
mutation, dispatch, or checkpoint commands.

## Publication and cleanup boundary

Stage 1, Stage 2, and Stage 3 working upgrade packages and generated execution
artifacts are local inputs/evidence, not public package documentation. Do not
publish or checkpoint the working upgrade package, generated runtime task
packets, profile results, audit results, local scratch notes, command logs,
Codex artifacts, or `project-runtime`/`project-archive` material as accepted
package docs.

Accepted stable summaries may be added under package-controlled paths such as:

```text
agent-system/11_release/STAGE1_UPGRADE_VALIDATION_REPORT.md
agent-system/11_release/STAGE2_UPGRADE_VALIDATION_REPORT.md
agent-system/11_release/STAGE3_SAFE_AUTOMATION_DIAGNOSTICS_RELEASE_NOTES.md
```

The Stage 1 final validation report is accepted evidence and must remain
intact. The original Stage 2 validation report remains historical evidence but
is superseded for current acceptance by the Stage 2 state-contract correction.
That historical Stage 2 evidence used `CURRENT_PACKAGE_VERSION: 3.0.1`; the
correction report is the current acceptance source for the governed `3.0.2`
package/governance tuple.
The final correction validation report is:

```text
agent-system/11_release/STAGE2_STATE_CONTRACT_CORRECTION_VALIDATION_REPORT.md
```

Task 006 supplied final local command evidence in that report, including the
current validation blocker status.
The Stage 3 release notes are Task 007 documentation evidence only. They record
the intended `3.1.0 / 3.1.0 / 3.0.0` package tuple and safety boundary, but
they do not claim final Stage 3 validation before Task 008 supplies its command
evidence.

After all accepted upgrade tasks are committed and pushed by the orchestrator,
cleanup is local:

```text
rm -rf project-input/<stage-upgrade-package>
git status --short project-input project-runtime project-archive
git ls-files project-input project-runtime project-archive
```

Expected tracked output for those roots is empty. If any file from those roots
is staged or tracked, stop and treat it as a governance incident.

## Templates, state, and logs

Templates in the [03_templates/](03_templates/) package directory define task
packets, agent results, handoffs, owner decisions, evidence matrices, findings
registers, setup tasks, smoke checks, launch readiness checks, handover checks,
research requests, research results, and design continuation tasks.

Runtime state templates in the [04_state/](04_state/) package directory define
the project state, current gate, next action, accepted artifacts registry, and
task registry. Log templates in the [06_logs/](06_logs/) package directory
define agent results, orchestrator events, and status summaries.

Do not confuse package templates with workspace instance data:

```text
agent-system/04_state/       = package state templates
project-runtime/             = generated runtime state
agent-system/03_templates/   = package task/result templates
project-input/               = local owner input
```

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

## Governance smoke tests

Run standalone package governance smoke tests with:

```text
./agent-system/scripts/run_governance_smoke_tests.sh
```

The smoke runner creates temporary local Git repositories and uses dry-run
preflight checks only. It does not stage, commit, push, contact a real remote,
or require real secrets.

Expected pass behavior after the standalone fixture expectations are aligned
with the active package tuple:

```text
SMOKE_RESULT: passed
```

Each fixture is a negative test: wrong remote, wrong branch, package repository
project-doc pollution, invalid task packet, push without accepted lock, and
secret-file exposure must all be blocked by the validator or preflight script.
The smoke runner exits nonzero if any blocked fixture unexpectedly passes or if
the patch coverage assertion is not `25/25`.

## Package version

Active package version constants are defined in:

```text
agent-system/PACKAGE_VERSIONING.md
```

Governance and package changes are recorded in:

```text
agent-system/GOVERNANCE_CHANGELOG.md
```

Current active tuple and Stage 3 marker:

```text
CURRENT_PACKAGE_VERSION: 3.1.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.1.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
STAGE3_RELEASE_MARKER: safe-automation-diagnostics
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
agent-system/10_examples/STAGE3_SAFE_AUTOMATION_DIAGNOSTICS_COMMANDS.md
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

This repository package is an instruction, governance, template, lifecycle, and validation package for Codex CLI orchestration.
