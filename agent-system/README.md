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

The package includes a filesystem-governed ASO helper CLI at
`agent-system/tools/aso/aso.py`. Most commands are read-only diagnostics or
dry-run proposals, while Project Factory commands may create generated
projects only within explicit target paths.

This P5.5 stabilization package records the active package metadata as the
governed `3.7.5` package/governance tuple with runtime schema `3.1.1` and
artifact package schema `1.1.0`. It preserves the Project Factory P1 command
boundary, Runtime Schema `3.1.1`, and Artifact Package Schema `1.1.0` while
retaining the P5.4 planner Dispatchability Gate. `plan-next` may recommend
`CREATE_AGENT` only after proving the current next action can dispatch a
profile agent with a valid role, task id, task packet, task registry entry,
gate state, and workspace/repository baseline.

ASO remains a deterministic governance/control conveyor. It validates and
gates artifacts produced by profile agents and detects contradictory bootstrap
state; it does not semantically read TZ, replace project designer reasoning,
generate product questions from TZ, install product-intake code or a
product-intake engine, run a daemon, dispatch live agents, execute
checkpoints, generate products, collect secrets, or run external workers.

The Runtime Schema `3.1.1` contract is documented in
`agent-system/02_runtime/RUNTIME_STATE_P2_CONTRACT.md` and packaged as
`agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json`.
It defines the sidecar envelope, required and optional sidecars, allowed
lifecycle/checkpoint/action/compatibility statuses, migration compatibility
for legacy `2.0.0` and `3.0.0` sidecars, and fixture expectations. Contract
validation is Python stdlib only and does not add a runtime `jsonschema`
dependency.

The corrected P4 governance boundary is documented in
`agent-system/02_runtime/PROJECT_DESIGN_GAP_GOVERNANCE_P4_CONTRACT.md`.
The P4.1 hotfix boundary is documented in
`agent-system/02_runtime/WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_HOTFIX_CONTRACT.md`.
It supersedes the non-authoritative
`upgrade/product-intake-capability-p4-v3.6.0` branch without deleting it.
The corrected bootstrap sequence is summarized in
`agent-system/02_runtime/CORRECTED_BOOTSTRAP_SEQUENCE_P4_1.md`, with release
validation evidence under
`agent-system/11_release/ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_VALIDATION_REPORT.md`.
The P5.2 bootstrap state reconciliation contract is documented in
`agent-system/02_runtime/BOOTSTRAP_STATE_RECONCILIATION_P5_2_CONTRACT.md`.
The P5.4 planner Dispatchability Gate contract is documented in
`agent-system/02_runtime/PLANNER_DISPATCHABILITY_GATE_P5_4_CONTRACT.md`.

The canonical installable ASO package source is:

```text
agent-system/tools/aso/agent_system_orchestrator_aso/
```

The former root-level duplicate package path
`agent_system_orchestrator_aso/` is not canonical package source and must remain
absent from tracked files. `pyproject.toml` package discovery points to
`agent-system/tools/aso`.

Install the local console command from the repository root with:

```text
bash install.sh
source .venv/bin/activate
make verify-install
```

The user installer creates `.venv`, installs the package in editable mode, and
verifies the installed `aso` command. It does not require secrets, GitHub
credentials, remote repository access, dispatch authority, checkpoint
execution, commit, push, or publication rights. Activation, update,
verification, and cleanup commands are documented in the repository-root
`README_INSTALL.md`.

Manual editable install remains available:

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

Runtime State P2 command surfaces are local and offline. JSON sidecars under
`project-runtime/state/` are canonical for P2+ runtime state. Markdown and
report outputs are compatibility views generated from JSON, not the canonical
state source. The active package version is `3.7.5` and the active runtime
schema version is `3.1.1`.

```text
python3 agent-system/tools/aso/aso.py validate-rules --root . --strict
python3 agent-system/tools/aso/aso.py state --help
python3 agent-system/tools/aso/aso.py state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --dry-run --json-out /tmp/aso-state-init-plan.json
python3 agent-system/tools/aso/aso.py state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --confirm-write --json-out /tmp/aso-state-init-receipt.json
python3 agent-system/tools/aso/aso.py state render --root /tmp/aso-state-demo --confirm-write
python3 agent-system/tools/aso/aso.py state verify --root /tmp/aso-state-demo --strict --json-out /tmp/aso-state-verify.json
python3 agent-system/tools/aso/aso.py state render --root /tmp/aso-state-demo --format markdown --out /tmp/aso-state-render.md
python3 agent-system/tools/aso/aso.py lifecycle terminate-agent --root /tmp/aso-state-demo --from-result project-runtime/results/worker/RESULT_TASK_ID_ATTEMPT_001.md --confirm-write
python3 agent-system/tools/aso/aso.py state migrate --root agent-system/tests/fixtures/state/valid_workspace --to 3.1.1 --dry-run --json-out /tmp/aso-state-migrate-plan.json
python3 agent-system/tools/aso/aso.py plan-next --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-plan.json
python3 agent-system/tools/aso/aso.py dashboard --root agent-system/tests/fixtures/state/valid_workspace --out /tmp/aso-stage2-dashboard.html
python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict --json-out /tmp/aso-stage2-checkpoint-preflight.json
```

`aso validate-rules` checks the packaged governance rule registry. `aso state
init --dry-run` writes no files; confirmed initialization requires
`--confirm-write` and writes only local ignored workspace sidecars under the
selected root. `aso state migrate --dry-run` emits a deterministic migration
plan for compatible legacy `2.0.0`/`3.0.0` sidecars; confirmed migration
requires `--confirm-write`, fails closed on malformed or ambiguous state, and
writes migration receipts under allowed runtime report paths. `aso state
render` is read-only except for explicit output to `/tmp`,
`project-runtime/reports`, or `project-runtime/rendered`. `aso state verify`
validates Runtime Schema `3.1.1` envelopes, sidecar types, required fields,
schema alignment, task references, and compatibility diagnostics, then emits
optional JSON evidence. `aso plan-next` recommends the next orchestrator action
as a dry-run report only. `aso dashboard` renders escaped static HTML to
stdout, `/tmp`, or an explicit workspace `project-runtime/dashboard` path.
`aso dag render`, `aso context-pack build`, and `aso incident fixture` likewise
write generated render/proposal artifacts only to stdout, `/tmp`, or explicit
workspace runtime report/proposal directories; tracked package paths are
rejected with `ASO_OUTPUT_PATH_FORBIDDEN`. `aso checkpoint-preflight` inspects
checkpoint eligibility without staging, committing, pushing, or changing
runtime state.
The corrected state examples use
`agent-system/tests/fixtures/state/valid_workspace`; the dry-run plan evidence
may use the canonical next action value `CREATE_AGENT` only for a dispatchable
route and does not dispatch an agent.

Safe Proposal / Apply P3 command surfaces are local and guarded. They run
under the current package/governance `3.7.5` tuple with Runtime Schema `3.1.1`
and preserve the P3 contract; they do not
dispatch agents, do not commit or push, and do not publish runtime artifacts.
Proposal commands default to dry-run. `--confirm-write` may write only proposal
artifacts under `project-runtime/proposals/`. `aso apply --dry-run` validates
a proposal and writes no state. `aso apply --confirm-apply` is required before
any supported runtime-state mutation and must emit a receipt under
`project-runtime/receipts/`. Checkpoint proposal is not checkpoint execution.

```text
python3 agent-system/tools/aso/aso.py propose --help
python3 agent-system/tools/aso/aso.py propose next-task --root agent-system/tests/fixtures/state/valid_workspace --dry-run --json-out /tmp/aso-p3-next-task-proposal.json
python3 agent-system/tools/aso/aso.py propose transition --root agent-system/tests/fixtures/state/valid_workspace --to TESTING --dry-run --json-out /tmp/aso-p3-transition-proposal.json
python3 agent-system/tools/aso/aso.py propose checkpoint --root agent-system/tests/fixtures/state/valid_workspace --dry-run --json-out /tmp/aso-p3-checkpoint-proposal.json
python3 agent-system/tools/aso/aso.py apply --root agent-system/tests/fixtures/state/valid_workspace --proposal /tmp/aso-p3-next-task-proposal.json --dry-run --json-out /tmp/aso-p3-apply-plan.json
python3 -m json.tool /tmp/aso-p3-next-task-proposal.json >/dev/null
python3 -m json.tool /tmp/aso-p3-apply-plan.json >/dev/null
```

Stage 3 command surfaces are local, read-only, dry-run, or proposal-only. The
package-layout guard checks active package metadata, command surface coherence,
canonical package placement, entrypoint configuration, and repository hygiene:

```text
python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
```

`aso package-layout verify` is an inspection command. It reports layout,
version, entrypoint, workflow, or hygiene drift and exits nonzero on strict
mismatches. It checks that the root duplicate package is absent and the
canonical package is under `agent-system/tools/aso/agent_system_orchestrator_aso/`.

For DAG readiness, `audit_passed` is not a completed dependency. Downstream
work that depends on accepted task output requires `checkpoint_done` with
checkpoint evidence, or another explicitly completed terminal state allowed by
the governance rules.

Repeatable root targets are:

```text
make install
make install-user
make verify-install
make test
make smoke
make doctor
make lint
make ci
```

`make test` runs the ASO command unit tests and package governance tests.
`make smoke` runs CLI help, package status, strict package lint, strict package
doctor, read-only package-layout verification, valid design/context-pack
fixtures, rule validation, state sidecar verification, dry-run next-action
planning, static dashboard rendering to `/tmp`, checkpoint preflight, and the
local Stage 3 diagnostics. `make ci` runs `test`, `smoke`, `doctor`, `lint`,
and `git diff --check`. The smoke and CI surfaces are local and diagnostic:
they must not require secrets, network credentials, real remotes, publishing
permissions, live service access, or live automation authority.

`make install-user` runs `install.sh` against `.venv`. `make verify-install`
uses the installed `.venv/bin/aso` command for package status, strict lint,
strict doctor, and strict package-layout verification.

The helper supports status, lint, doctor, package-layout verification, design
validation, context pack validation, rule validation, Runtime Schema `3.1.1`
state init/migrate/render/verify, dry-run next-action planning, static
dashboard rendering, checkpoint eligibility preflight, archive verify
inspection, P5 artifact package validation and classification, lifecycle
receipt materialization, and Project Factory scoped generated-project helpers.
Diagnostic, validator, planning, dashboard, archive, and checkpoint-preflight
surfaces remain read-only, dry-run, or proposal-only. State writes are limited to
explicit `state init --confirm-write`, `state migrate --confirm-write`, and
generated-project local initialization under ignored workspace roots. Project
Factory commands may create generated projects and, when a later publish flow
is explicitly confirmed, publish only clean generated-project files from
explicit target paths. Outside the P3 local runtime-state proposal/apply
boundary, ASO does not provide a runtime daemon, live agent dispatch,
checkpoint execution, general package/runtime mutation, commit, or push
authority. For package lint compatibility, this scoped boundary is also
stated as: ASO diagnostic surfaces do not provide general mutation, dispatch, or checkpoint authority.

Profile-agent completion follows the P5 artifact package sequence:

```text
RESULT_RECEIVED -> ARTIFACT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY
```

Profile-agent output starts as a candidate artifact package under
`project-runtime/artifacts/candidates/`. The orchestrator accepts the candidate
into `project-runtime/artifacts/accepted/`, records the acceptance receipt and
`ARTIFACT_ACCEPTED` lifecycle event, and only then terminates the agent
instance and marks audit routing ready. Context handed to later agents must
cite accepted artifact packages or rendered views under
`project-runtime/rendered/`; raw chat context, raw artifacts, rejected
artifacts, and local runtime scratch files are not accepted context.
`AUDIT_ROUTE_READY` is a readiness marker only and does not dispatch live
agents or execute checkpoints.

## Project Factory P1

Project Factory P1 supports local vendored creation, local reference creation,
GitHub dry-run planning, confirmed GitHub publish, and a guided wizard. It
remains available in package version `3.7.5`; existing P1/P0 generated-project
lockfiles remain compatible when they satisfy the accepted publication-boundary
and engine-mode rules.

Local vendored mode preserves the P0 behavior of copying safe `agent-system/`
package content into the generated project:

```text
python3 agent-system/tools/aso/aso.py project create --local --engine-mode vendored --target /tmp/demo-vendored --name "Demo Vendored" --slug demo-vendored --profile generic --repo-url none --branch main
python3 agent-system/tools/aso/aso.py project verify-clean --root /tmp/demo-vendored --strict
python3 agent-system/tools/aso/aso.py lint --root /tmp/demo-vendored --mode workspace --strict
python3 agent-system/tools/aso/aso.py doctor --root /tmp/demo-vendored --mode workspace --strict
```

Local reference mode records the external ASO engine in `aso.lock` and does not
vendor `agent-system/`:

```text
python3 agent-system/tools/aso/aso.py project create --local --engine-mode reference --target /tmp/demo-reference --name "Demo Reference" --slug demo-reference --profile generic --repo-url https://github.com/OWNER/demo-reference.git --branch main
python3 agent-system/tools/aso/aso.py project verify-clean --root /tmp/demo-reference --strict
python3 agent-system/tools/aso/aso.py lint --root /tmp/demo-reference --mode workspace --strict
python3 agent-system/tools/aso/aso.py doctor --root /tmp/demo-reference --mode workspace --strict
```

GitHub dry-run and confirmed publish use the selected `vendored` or
`reference` engine mode. In reference mode, the generated repository must not
track `agent-system/`; in vendored mode, it may publish only safe
generated-project `agent-system/` content that passes the clean boundary.

GitHub dry-run mode emits a deterministic publication plan only. It performs no
generated-project target writes, Git commands, GitHub CLI calls, network
actions, repository creation, commits, or pushes:

```text
python3 agent-system/tools/aso/aso.py project create --github --dry-run --engine-mode reference --target /tmp/demo-github --name "Demo GitHub" --slug demo-github --profile generic --branch main --owner OWNER --repo demo-github --private --json-out /tmp/demo-github-plan.json
```

Confirmed GitHub publish requires explicit `--confirm-publish`, exactly one
visibility flag, Git, GitHub CLI (`gh`), and authenticated GitHub access. It is
target-scoped to the generated project and publishes only files that pass the
generated-project clean boundary:

```text
python3 agent-system/tools/aso/aso.py project create --github --confirm-publish --engine-mode reference --target /tmp/demo-github --name "Demo GitHub" --slug demo-github --profile generic --branch main --owner OWNER --repo demo-github --private
```

The wizard exposes the same bounded flows:

```text
python3 agent-system/tools/aso/aso.py wizard
python3 agent-system/tools/aso/aso.py wizard --answers path/to/answers.json --dry-run --json-out /tmp/aso-wizard-plan.json
```

Generated projects may initialize Runtime Schema `3.1.1` JSON sidecars under
their ignored local `project-runtime/state/` root. Those sidecars are local
runtime state for the generated workspace and are not package or
generated-project publication artifacts. Generated projects must not track or
publish `project-input/`, `project-runtime/`, `project-archive/`, virtual
environments, caches, logs, secret-like files, local upgrade packages, or ASO
engine `.git` metadata. Reference-mode generated repositories must not track
`agent-system/`. Vendored-mode generated repositories may track only safe
generated-project `agent-system/` content that passes the publication
boundary.

Safe Proposal / Apply P3 and Project Factory P1 do not implement a runtime
daemon, dashboard control plane, distributed workers, live agent dispatch,
checkpoint executor, commit/push automation, or multi-project registry. P4
dashboard/control-plane work, P5 queue/dispatcher work, P6 checkpoint executor
work, daemon mode, and distributed workers are deferred to later bounded
package upgrades.

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
The Stage 3 v3.1.0 release notes are historical Task 007 documentation
evidence only. Current pre-main package layout cleanup evidence belongs in:

```text
agent-system/11_release/STAGE3_PRE_MAIN_PACKAGE_LAYOUT_CLEANUP_VALIDATION_REPORT.md
```

That report records command evidence for the `3.1.2 / 3.1.2 / 3.0.0` package
tuple, the canonical package layout under `agent-system/tools/aso/`, and the
absence of tracked `agent_system_orchestrator_aso/**`,
`project-input/**`, `project-runtime/**`, and `project-archive/**` files. It
must record `VALIDATION_COMMAND_HEAD`, `FINAL_COMMIT_PENDING: yes`, and
`REMOTE_HEAD_VERIFICATION_REQUIRED_AFTER_PUSH: yes` instead of claiming a
self-referential final commit.

Merge readiness must follow `09_MAIN_MERGE_READINESS_PROCEDURE.md` or accepted
package merge-readiness docs after audit pass, orchestrator-owned checkpoint,
push, and remote CI evidence. This package does not merge to `main`.

After all accepted upgrade tasks are committed and pushed by the orchestrator,
cleanup is local:

```text
rm -rf project-input/<stage-upgrade-package>
git status --short project-input project-runtime project-archive .venv
git ls-files project-input project-runtime project-archive .venv
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

Current active tuple and package markers:

```text
CURRENT_PACKAGE_VERSION: 3.7.5
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.5
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
PROJECT_FACTORY_RELEASE_MARKER: project-factory-p1
RUNTIME_STATE_RELEASE_MARKER: artifact-package-model-p5
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
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
