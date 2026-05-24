# agent-system-orchestrator

Repository for the universal `agent-system/` orchestration package.

Start from:

```text
agent-system/00_start/ORCHESTRATOR_START.md
```

Package documentation is in:

```text
agent-system/README.md
```

The package is a filesystem-governed instruction, template, lifecycle, and
validation system for Codex CLI orchestration. It includes a
filesystem-governed ASO helper CLI at `agent-system/tools/aso/aso.py`: most
commands are read-only diagnostics or dry-run proposals, while Project Factory
commands may create generated projects only within explicit target paths.

This P57 governance documentation authority sync records the active package
metadata as the governed `3.7.8` package/governance tuple with runtime schema
`3.1.1` and artifact package schema `1.1.0`. It preserves installed real-TZ
intake guidance, release validation evidence, clean install semantics, source
hygiene, and CI E2E smoke coverage;
the P5.4 planner Dispatchability Gate remains the active authority:
`plan-next` may recommend `CREATE_AGENT` only after proving the current next
action can dispatch a profile agent with a valid role, task id, task packet,
task registry entry, gate state, and workspace/repository baseline. ASO
remains a governance and control conveyor: it validates bootstrap state
consistency and repair routes, but it does not interpret raw TZ content,
replace project designer reasoning, generate product questions from TZ,
install product-intake code or a product-intake engine, run a daemon, dispatch
live agents, execute checkpoints, generate products, collect secrets, or run
external workers.
The orchestrator does not write profile-agent changes and does not check
changes semantically; it routes one fresh agent per bounded task, requires
`TASK_COMPLEXITY`, `REASONING_LEVEL_REQUIRED`, and
`AGENT_LIFECYCLE_POLICY`, and enforces agent termination/context deletion
after RESULT before any next task route.

The Runtime Schema sidecar contract is documented in
`agent-system/02_runtime/RUNTIME_STATE_P2_CONTRACT.md` and packaged as
`agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json`.
The historical `3_1_0` filename remains the active base envelope contract for
Runtime Schema `3.1.1`; no duplicate `3_1_1` contract file is authoritative.
The P5-family authority chain and override map are documented in
`agent-system/02_runtime/CONTRACT_AUTHORITY_MAP.md`. The contract defines
required and optional sidecars, the P2 envelope, allowed
lifecycle/checkpoint/action/compatibility statuses, legacy `2.0.0`, `3.0.0`,
and `3.1.0` migration compatibility behavior, and fixture expectations. The
validator contract checks use Python stdlib JSON/data validation only.

P57 release evidence is recorded in
`agent-system/11_release/ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_RELEASE_NOTES.md`
and
`agent-system/11_release/ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_VALIDATION_REPORT.md`.
Post-push remote CI evidence for the final pushed HEAD is recorded separately
in
`agent-system/11_release/ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_REMOTE_CI_EVIDENCE.md`
after GitHub Actions completes. P57 documents final real-TZ readiness criteria
but does not claim final real-TZ acceptance beyond the required smoke target.

The corrected P4 governance boundary is documented in
`agent-system/02_runtime/PROJECT_DESIGN_GAP_GOVERNANCE_P4_CONTRACT.md`.
The P4.1 hotfix boundary is documented in
`agent-system/02_runtime/WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_HOTFIX_CONTRACT.md`.
The P5 artifact package model boundary is documented in
`agent-system/02_runtime/ARTIFACT_PACKAGE_MODEL_P5_CONTRACT.md`.
The P5.2 bootstrap state reconciliation correction is documented in
`agent-system/02_runtime/BOOTSTRAP_STATE_RECONCILIATION_P5_2_CONTRACT.md`.
The P5.4 planner Dispatchability Gate correction is documented in
`agent-system/02_runtime/PLANNER_DISPATCHABILITY_GATE_P5_4_CONTRACT.md`.
It supersedes the non-authoritative
`upgrade/product-intake-capability-p4-v3.6.0` branch without deleting it.

The canonical ASO Python package is:

```text
agent-system/tools/aso/agent_system_orchestrator_aso/
```

The former root-level duplicate package path
`agent_system_orchestrator_aso/` is not a package source or runtime source and
must remain absent from tracked files before merge. Package-layout verification
replaces duplicate copy synchronization checks for this cleanup.
`aso package-sync verify` remains only as a deprecated compatibility alias for
`aso package-layout verify`; it performs no copy synchronization and must not
reintroduce duplicate package trees.

## Local install and command surface

For clean source-hygiene validation from the repository root:

```text
bash agent-system/scripts/install_aso_clean.sh --source . --venv /tmp/aso_clean_install_venv --fresh --with-test
source /tmp/aso_clean_install_venv/bin/activate
aso --help
aso status --root . --mode package
```

The clean installer archives the tracked source into an isolated temporary
copy, installs from that copy, and verifies the live repository git status is
unchanged before and after installation. The target virtual environment must
be outside the source repository. By default, the clean installer fails if
`--venv` already exists and is non-empty; use `--fresh` to recreate it or
`--reuse-venv` only when reuse is intentional. Direct `pip install .` and
`pip install -e .` are development shortcuts, not the official clean-source
validation path for this package.

The supported installed-orchestrator bootstrap workflow for a real project TZ
file is:

```text
ASO_ROOT=$(pwd)
WORK=/tmp/aso-real-tz-workspace
rm -rf "$WORK" /tmp/aso_clean_install_venv /tmp/aso_clean_install_src
mkdir -p "$WORK/project-input"
cp /path/to/TZ_REAL_E2E_TELEGRAM_BOT.md "$WORK/project-input/TZ_REAL_E2E_TELEGRAM_BOT.md"
bash agent-system/scripts/install_aso_clean.sh --source "$ASO_ROOT" --venv /tmp/aso_clean_install_venv --fresh --source-copy /tmp/aso_clean_install_src --with-test
. /tmp/aso_clean_install_venv/bin/activate
aso state init --root "$WORK" --tz project-input/TZ_REAL_E2E_TELEGRAM_BOT.md --confirm-write
aso intake bootstrap --root "$WORK" --tz project-input/TZ_REAL_E2E_TELEGRAM_BOT.md --target-role requirements_analyst --confirm-write
aso state verify --root "$WORK" --strict
aso plan-next --root "$WORK" --strict
```

Confirmed runtime bootstrap commands record factual UTC timestamps ending in
`Z`. Use `--deterministic-timestamps` on `aso state init` or
`aso intake bootstrap` only for tests, golden fixtures, and reproducible
documentation captures that need the fixed regression timestamp.

`plan-next` is read-only. It should recommend dispatch-capable `CREATE_AGENT`
for the bootstrap requirements analyst task. The first profile-agent then
creates a candidate package under `project-runtime/artifacts/candidates/<TASK_ID>/`
with `artifact_package_manifest.json`; the operator accepts that package,
records the `ARTIFACT_ACCEPTED` lifecycle event, and only then follows audit
routing, correction, and checkpoint steps outside ASO's read-only planner.
Dispatch readiness is governed by canonical `PROJECT_STATE` enum values:
`identity_validation_status` is `not_checked | passed | failed | blocked`, and
`repository_lock_status` is `draft | accepted | revoked | blocked | absent`.
`WORKSPACE_IDENTITY` keeps compatibility diagnostics; it does not override
`PROJECT_STATE` for dispatchability. Invalid `PROJECT_STATE` readiness values
block `plan-next`, even when a corresponding `NEXT_ACTION` requirement flag is
false.

For an editable user install from the repository root:

```text
bash install.sh
source .venv/bin/activate
make verify-install
```

The editable installer creates `.venv`, installs this checkout in editable
mode, and verifies the installed `aso` command. It does not require secrets,
GitHub credentials, remote repository access, dispatch authority, checkpoint
execution, commit, push, or publication rights. See
`README_INSTALL.md` for activation, verification, update, and cleanup
commands.

CI also runs reproducible clean install smoke paths:

```text
make install-smoke
make install-test-smoke
```

`make install-smoke` creates a temporary virtual environment, installs from an
isolated source archive with `agent-system/scripts/install_aso_clean.sh`,
verifies `aso --help`, `aso status --root . --mode package`, strict
package-layout verification, and imports the installed
`agent_system_orchestrator_aso` package from virtualenv `site-packages`.
`make install-test-smoke` repeats the clean install with `--with-test` and
imports `jsonschema` from that temporary virtual environment, proving the
supported test extra rather than relying on an ambient global package.

For local console-script use from this repository:

```text
python3 -m pip install -e .
aso --help
```

For local test runs, install the supported test extra so schema contract tests
have `jsonschema` available instead of relying on environment-specific
packages:

```text
python3 -m pip install -e ".[test]"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s agent-system/tools/aso/tests
```

Direct script execution remains supported and is the compatibility baseline:

```text
python3 agent-system/tools/aso/aso.py --help
```

Package repository checks use explicit package mode:

```text
python3 agent-system/tools/aso/aso.py status --root . --mode package
python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
```

Omitted `--mode` is guarded. The CLI auto-detects package roots from
`pyproject.toml` plus `agent-system/`, detects initialized workspace roots from
`project-runtime/state/`, and fails with `ASO_MODE_AMBIGUOUS` when both signals
are present. Package checks should still pass `--mode package` explicitly.

Initialized project workspaces use explicit workspace mode:

```text
python3 agent-system/tools/aso/aso.py state render --root /path/to/project --confirm-write
python3 agent-system/tools/aso/aso.py status --root /path/to/project --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /path/to/project --mode workspace --strict
python3 agent-system/tools/aso/aso.py doctor --root /path/to/project --mode workspace --strict
python3 agent-system/tools/aso/aso.py lifecycle receive-result --root /path/to/project --from-result project-runtime/results/worker/RESULT_TASK_ID_ATTEMPT_001.md --confirm-write
python3 agent-system/tools/aso/aso.py artifact accept --root /path/to/project --package project-runtime/artifacts/candidates/TASK_ID/artifact_package_manifest.json --confirm-write
python3 agent-system/tools/aso/aso.py lifecycle terminate-agent --root /path/to/project --from-result project-runtime/results/worker/RESULT_TASK_ID_ATTEMPT_001.md --confirm-write
```

Run `state render --confirm-write` after manual state materialization changes.
`intake bootstrap --confirm-write` synchronizes generated Markdown
compatibility views for all canonical Runtime Schema sidecars from JSON
sidecars before returning.
After a profile-agent RESULT is recorded, the governed completion sequence is:

```text
RESULT_RECEIVED -> ARTIFACT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY
```

Profile-agent output is first a candidate artifact package under
`project-runtime/artifacts/candidates/`. Context for later task packets should
come from accepted artifact packages under `project-runtime/artifacts/accepted/`
or rendered state views under `project-runtime/rendered/`, not from raw agent
chat context. `AUDIT_ROUTE_READY` is only a deterministic readiness marker; it
does not dispatch a live auditor or execute a checkpoint.

Design and context-pack validators are read-only:

```text
python3 agent-system/tools/aso/aso.py validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict
python3 agent-system/tools/aso/aso.py validate-context-pack agent-system/tests/fixtures/context_pack/valid_context_pack.json --root . --strict
```

Runtime State P2 command surfaces formalize JSON sidecars under
`project-runtime/state/`. `project-runtime/state/*.json` sidecars are canonical
for Runtime Schema `3.1.1`; Markdown runtime files are generated compatibility
views and report outputs are diagnostics generated from JSON. The active package
version is `3.7.8` and the active runtime schema version is `3.1.1`.

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

`aso state init --dry-run` writes no files. Confirmed initialization requires
`--confirm-write` and writes only local ignored workspace state under the
selected root. Confirmed runtime writes use current UTC timestamps by default;
`--deterministic-timestamps` is reserved for tests and fixtures. `aso state
migrate --dry-run` emits a deterministic migration plan for compatible legacy
sidecars; confirmed migration requires
`--confirm-write`, fails closed on malformed or ambiguous input, and writes
migration receipts under allowed `project-runtime/` report paths. Without
`--confirm-write`, `aso state render` is read-only except for explicit report
output to `/tmp` or workspace `project-runtime/reports` or
`project-runtime/rendered` paths. With `--confirm-write`, it writes generated
Markdown compatibility views for every canonical JSON sidecar.

Corrected P4 design governance commands validate and route
project-designer-authored artifacts. They do not interpret raw TZ content,
select product capabilities, or generate owner questions:

```text
python3 agent-system/tools/aso/aso.py design --help
python3 agent-system/tools/aso/aso.py design verify --root agent-system/tests/fixtures/design_gap/valid_workspace --strict
python3 agent-system/tools/aso/aso.py design questions next --root agent-system/tests/fixtures/design_gap/valid_workspace --json-out /tmp/aso-dg4-next-question.json
python3 agent-system/tools/aso/aso.py design gate verify --root agent-system/tests/fixtures/design_gap/valid_workspace --stage DESIGN --strict
```

`design verify` checks gap records, owner question cards, audit status, answer
links, one-question-at-a-time routing, and cross-links. `design questions
next` returns the next existing audited question card and writes only to
`/tmp` or an allowed runtime report path. `design decision record --dry-run`
writes nothing; confirmed decision recording writes only ignored local
owner-decision records under the selected workspace after a question has been
presented. Example owner-answer validation after presentation:

```text
python3 agent-system/tools/aso/aso.py design decision record --root /path/to/project --question-id Q-001 --answer A --dry-run
```

`design gate verify` fails closed when an unanswered gap blocks the requested
lifecycle stage.

Safe Proposal / Apply P3 adds local guarded proposal and apply commands for
Runtime Schema `3.1.1` state. Proposal commands do not dispatch agents, do not
write canonical state sidecars, and do not commit or push. Checkpoint proposal
is checkpoint eligibility evidence only; it is not checkpoint execution.
Confirmed apply requires `--confirm-apply`, re-runs guards, and may write only
supported runtime-state changes plus receipts under ignored workspace runtime
roots.

```text
python3 agent-system/tools/aso/aso.py propose --help
python3 agent-system/tools/aso/aso.py propose next-task --root agent-system/tests/fixtures/state/valid_workspace --dry-run --json-out /tmp/aso-p3-next-task-proposal.json
python3 agent-system/tools/aso/aso.py propose transition --root agent-system/tests/fixtures/state/valid_workspace --to TESTING --dry-run --json-out /tmp/aso-p3-transition-proposal.json
python3 agent-system/tools/aso/aso.py propose checkpoint --root agent-system/tests/fixtures/state/valid_workspace --dry-run --json-out /tmp/aso-p3-checkpoint-proposal.json
python3 agent-system/tools/aso/aso.py apply --root agent-system/tests/fixtures/state/valid_workspace --proposal /tmp/aso-p3-next-task-proposal.json --dry-run --json-out /tmp/aso-p3-apply-plan.json
python3 -m json.tool /tmp/aso-p3-apply-plan.json >/dev/null
```

Use `--confirm-write` only to persist proposal artifacts under
`project-runtime/proposals/`. Use `--confirm-apply` only after reviewing a
fresh proposal for the same workspace; it does not grant dispatch,
checkpoint, commit, push, or publication authority.

Stage 3 package-layout diagnostics are read-only and verify package metadata,
entrypoint, hygiene, and canonical package-source coherence:

```text
python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
```

The deprecated `package-sync verify` command is the same read-only package
layout verification path kept for compatibility. It is not a synchronization
command, performs no file copying, and must not recreate the former root-level
`agent_system_orchestrator_aso/` package tree.

Project Factory P1 creates local generated project workspaces, plans GitHub
publication, and can publish a clean generated project using the selected
engine mode only after explicit confirmation. Local modes do not require secrets, GitHub
credentials, remote repository access, commit authority, push authority, or
live automation authority:

```text
python3 agent-system/tools/aso/aso.py project create --help
python3 agent-system/tools/aso/aso.py project verify-clean --help
```

Create a local vendored generated project, preserving the P0 behavior of
copying safe `agent-system/` package content:

```text
python3 agent-system/tools/aso/aso.py project create --local --engine-mode vendored --target /tmp/demo-vendored --name "Demo Vendored" --slug demo-vendored --profile generic --repo-url none --branch main
python3 agent-system/tools/aso/aso.py project verify-clean --root /tmp/demo-vendored --strict
python3 /tmp/demo-vendored/agent-system/tools/aso/aso.py state render --root /tmp/demo-vendored --confirm-write
python3 /tmp/demo-vendored/agent-system/tools/aso/aso.py status --root /tmp/demo-vendored --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /tmp/demo-vendored --mode workspace --strict
python3 agent-system/tools/aso/aso.py doctor --root /tmp/demo-vendored --mode workspace --strict
```

Create a local reference-mode generated project without vendoring
`agent-system/`:

```text
python3 agent-system/tools/aso/aso.py project create --local --engine-mode reference --target /tmp/demo-reference --name "Demo Reference" --slug demo-reference --profile generic --repo-url https://github.com/OWNER/demo-reference.git --branch main
python3 agent-system/tools/aso/aso.py project verify-clean --root /tmp/demo-reference --strict
aso state render --root /tmp/demo-reference --confirm-write
aso status --root /tmp/demo-reference --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /tmp/demo-reference --mode workspace --strict
python3 agent-system/tools/aso/aso.py doctor --root /tmp/demo-reference --mode workspace --strict
```

GitHub dry-run and confirmed publish use the selected `vendored` or
`reference` engine mode. In reference mode, the generated repository must not
track `agent-system/`; in vendored mode, it may publish only safe
generated-project `agent-system/` content that passes the clean boundary.

Plan GitHub publication without generated-project target writes, Git commands,
GitHub CLI, network access, credentials, repository creation, commits, or
pushes:

```text
python3 agent-system/tools/aso/aso.py project create --github --dry-run --engine-mode reference --target /tmp/demo-github --name "Demo GitHub" --slug demo-github --profile generic --branch main --owner OWNER --repo demo-github --private --json-out /tmp/demo-github-plan.json
```

Confirmed GitHub publish is the only Project Factory path that requires Git,
GitHub CLI (`gh`), and authenticated GitHub access. It is limited to the
generated project target path and requires `--confirm-publish` plus an explicit
visibility flag:

```text
python3 agent-system/tools/aso/aso.py project create --github --confirm-publish --engine-mode reference --target /tmp/demo-github --name "Demo GitHub" --slug demo-github --profile generic --branch main --owner OWNER --repo demo-github --private
```

The guided wizard exposes the same bounded Project Factory flows:

```text
python3 agent-system/tools/aso/aso.py wizard
python3 agent-system/tools/aso/aso.py wizard --answers path/to/answers.json --dry-run --json-out /tmp/aso-wizard-plan.json
```

Generated projects contain `aso.lock`, `.gitignore`, a minimal README, and
local ignored ASO working roots when needed. Local Project Factory creation may
initialize Runtime Schema `3.1.1` sidecars under the generated project's
ignored `project-runtime/state/` root; those sidecars are local runtime state,
not package publication artifacts. Vendored mode may copy safe `agent-system/`
content. Reference mode records the external ASO engine in `aso.lock` and must
not track `agent-system/`. Generated projects must not publish
`project-input/`, `project-runtime/`, `project-archive/`, virtual
environments, caches, logs, secret-like files, local upgrade packages, or ASO
engine `.git` metadata.

Project Factory P1 does not implement a runtime daemon, dashboard control
plane, distributed workers, live agent dispatch, or checkpoint executor. It
does not replace designer-led intake. Generated workspaces provide the bounded
filesystem shell for later profile-agent work; the project designer still
interprets the owner source brief, chooses the documentation template family,
records gaps, and authors functional owner question cards subject to audit.

For DAG readiness, `audit_passed` is not a completed dependency. Downstream
work that depends on accepted task output requires `checkpoint_done` with
checkpoint evidence, or another explicitly completed terminal state allowed by
the governance rules.

Repeatable root targets:

```text
make install
make install-user
make verify-install
make test
make smoke
make doctor
make lint
make install-smoke
make install-test-smoke
make e2e-real-tz-smoke
make source-contamination-guard
make ci
```

The smoke target includes CLI help, package status, strict package lint,
strict package doctor, read-only package-layout verification, valid
design/context-pack fixtures, rule validation, state sidecar verification,
dry-run next-action planning, static dashboard rendering to `/tmp`,
and checkpoint preflight. The CI target runs local test, smoke, doctor, lint,
clean install smoke, clean `[test]` install smoke, real-TZ E2E smoke, source
contamination guard, and whitespace diff checks. CI should use the same local
`make ci` command and must not require secrets, network credentials, real
remotes, publishing permissions, or live automation authority.

Final local and CI validation commands for this package are:

```text
PYTHONDONTWRITEBYTECODE=1 make install-smoke
PYTHONDONTWRITEBYTECODE=1 make install-test-smoke
PYTHONDONTWRITEBYTECODE=1 make e2e-real-tz-smoke
PYTHONDONTWRITEBYTECODE=1 make ci
```

`make install-user` runs `install.sh` against `.venv`. `make verify-install`
uses the installed `.venv/bin/aso` command for package status, strict lint,
strict doctor, and strict package-layout verification. Package validation does
not require `.venv`; direct script checks remain the compatibility baseline.

Stage 2 state-contract examples use the corrected valid workspace fixture at
`agent-system/tests/fixtures/state/valid_workspace`. The dry-run plan example
may report the canonical next action value `CREATE_AGENT` only for a
dispatchable route; it is evidence only and does not dispatch an agent.

The helper supports status, lint, doctor, package-layout verification, design
validation, context pack validation, rule validation, Runtime Schema `3.1.1`
state init/migrate/render/verify, dry-run next-action planning, static
dashboard rendering, checkpoint eligibility preflight, archive verify
inspection, P4 design governance, and Project Factory scoped generated-project
helpers. Diagnostic, validator, design-governance, planning, dashboard,
archive, and checkpoint-preflight surfaces
remain read-only, dry-run, or proposal-only. State writes are limited to
explicit `state init --confirm-write`, `state migrate --confirm-write`, and
generated-project local initialization under ignored workspace roots. Design
decision recording is limited to explicit `design decision record
--confirm-write` under ignored local owner-decision runtime roots. Project
Factory commands may create generated projects and, when a later publish flow
is explicitly confirmed, publish only clean generated-project files from
explicit target paths. Outside the P3 local runtime-state proposal/apply
boundary and the P4 owner-decision recording boundary, ASO does not provide a
runtime daemon, live agent dispatch, checkpoint execution, general
package/runtime mutation, commit, or push authority. For package lint
compatibility, this scoped boundary is also stated as: ASO diagnostic surfaces
do not provide general mutation, dispatch, or checkpoint authority.

## Publication boundary

`project-input/`, `project-runtime/`, and `project-archive/` are local
generated or owner-input roots. Working upgrade packages, runtime results,
audit files, scratch notes, command logs, and local Codex artifacts from those
roots must not be published as package documentation. After an accepted upgrade
flow completes and the orchestrator-owned checkpoint is complete, remove local
upgrade packages and verify:

```text
git status --short project-input project-runtime project-archive .venv
git ls-files project-input project-runtime project-archive .venv
```

The expected tracked-file result is empty. Stable release or validation
summaries belong under accepted package paths such as `agent-system/11_release/`.
Local `.venv` directories are generated user install state and must not be
staged or published.
Current P4.1 release evidence is recorded in
`agent-system/11_release/ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_RELEASE_NOTES.md`
and
`agent-system/11_release/ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_VALIDATION_REPORT.md`.
Current P5 release evidence is recorded in
`agent-system/11_release/ASO_ARTIFACT_PACKAGE_MODEL_P5_V3_7_0_RELEASE_NOTES.md`
and
`agent-system/11_release/ASO_ARTIFACT_PACKAGE_MODEL_P5_V3_7_0_VALIDATION_REPORT.md`.
Incident replay notes are recorded in
`agent-system/11_release/ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_INCIDENT_REPLAY_NOTES.md`.
The historical Stage 2 validation report is
`agent-system/11_release/STAGE2_UPGRADE_VALIDATION_REPORT.md`; it is superseded
for current acceptance by the Stage 2 state-contract correction. The final
correction validation report is
`agent-system/11_release/STAGE2_STATE_CONTRACT_CORRECTION_VALIDATION_REPORT.md`.
That report records Task 006 command evidence and the current validation
blocker status. Stage 3 v3.1.0 release cleanup notes are recorded in
`agent-system/11_release/STAGE3_SAFE_AUTOMATION_DIAGNOSTICS_RELEASE_NOTES.md`;
that file is historical Task 007 documentation evidence only. Current pre-main
package layout cleanup evidence belongs in
`agent-system/11_release/STAGE3_PRE_MAIN_PACKAGE_LAYOUT_CLEANUP_VALIDATION_REPORT.md`.
That report must separate `VALIDATION_COMMAND_HEAD` from post-push remote HEAD
verification and must not claim a merge to `main`.

Merge readiness is governed by
`09_MAIN_MERGE_READINESS_PROCEDURE.md` or the accepted package merge-readiness
docs after audit, orchestrator-owned checkpoint, push, and remote CI evidence.

Current P5.2 release prep evidence is recorded in
`agent-system/11_release/ASO_BOOTSTRAP_STATE_RECONCILIATION_P5_2_V3_7_2_RELEASE_NOTES.md`
and
`agent-system/11_release/ASO_BOOTSTRAP_STATE_RECONCILIATION_P5_2_V3_7_2_VALIDATION_REPORT.md`.
