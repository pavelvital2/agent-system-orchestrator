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

This P4.1 hotfix package records the active
package metadata as the governed `3.6.1` package/governance tuple with runtime
schema `3.1.0`. P4.1 fixes workspace/package mode guard handling, derived
runtime Markdown materialization from JSON sidecars, and the missing
lifecycle termination event after RESULT before audit routing while preserving
the P2/P3 Runtime Schema `3.1.0` sidecar envelope. ASO remains a governance
and control conveyor: it does not interpret raw TZ content, replace project
designer reasoning, generate product questions from TZ, install product-intake
code or a product-intake engine, run a daemon, dispatch live agents, execute
checkpoints, generate products, collect secrets, or run external workers.

The Runtime Schema `3.1.0` sidecar contract is documented in
`agent-system/02_runtime/RUNTIME_STATE_P2_CONTRACT.md` and packaged as
`agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json`.
It defines required and optional sidecars, the P2 envelope, allowed
lifecycle/checkpoint/action/compatibility statuses, legacy `2.0.0` and
`3.0.0` migration compatibility behavior, and fixture expectations. The
validator contract checks use Python stdlib JSON/data validation only.

The corrected P4 governance boundary is documented in
`agent-system/02_runtime/PROJECT_DESIGN_GAP_GOVERNANCE_P4_CONTRACT.md`.
The P4.1 hotfix boundary is documented in
`agent-system/02_runtime/WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_HOTFIX_CONTRACT.md`.
It supersedes the non-authoritative
`upgrade/product-intake-capability-p4-v3.6.0` branch without deleting it.

The canonical ASO Python package is:

```text
agent-system/tools/aso/agent_system_orchestrator_aso/
```

The former root-level duplicate package path
`agent_system_orchestrator_aso/` is not a package source and must remain absent
from tracked files before merge. Package-layout verification replaces duplicate
copy synchronization checks for this cleanup.

## Local install and command surface

For a repeatable user install from the repository root:

```text
bash install.sh
source .venv/bin/activate
make verify-install
```

The installer creates `.venv`, installs this checkout in editable mode, and
verifies the installed `aso` command. It does not require secrets, GitHub
credentials, remote repository access, dispatch authority, checkpoint
execution, commit, push, or publication rights. See
`README_INSTALL.md` for activation, verification, update, and cleanup
commands.

For local console-script use from this repository:

```text
python3 -m pip install -e .
aso --help
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

Initialized project workspaces use explicit workspace mode:

```text
python3 agent-system/tools/aso/aso.py status --root /path/to/project --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /path/to/project --mode workspace --strict
python3 agent-system/tools/aso/aso.py doctor --root /path/to/project --mode workspace --strict
```

Design and context-pack validators are read-only:

```text
python3 agent-system/tools/aso/aso.py validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict
python3 agent-system/tools/aso/aso.py validate-context-pack agent-system/tests/fixtures/context_pack/valid_context_pack.json --root . --strict
```

Runtime State P2 command surfaces formalize JSON sidecars under
`project-runtime/state/`. JSON sidecars are canonical for P2+ runtime state;
Markdown or report outputs are compatibility views generated from JSON. The
active package version is `3.6.1` and the active runtime schema version is
`3.1.0`.

```text
python3 agent-system/tools/aso/aso.py validate-rules --root . --strict
python3 agent-system/tools/aso/aso.py state --help
python3 agent-system/tools/aso/aso.py state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --dry-run --json-out /tmp/aso-state-init-plan.json
python3 agent-system/tools/aso/aso.py state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --confirm-write --json-out /tmp/aso-state-init-receipt.json
python3 agent-system/tools/aso/aso.py state verify --root /tmp/aso-state-demo --strict --json-out /tmp/aso-state-verify.json
python3 agent-system/tools/aso/aso.py state render --root /tmp/aso-state-demo --format markdown --out /tmp/aso-state-render.md
python3 agent-system/tools/aso/aso.py state migrate --root agent-system/tests/fixtures/state/valid_workspace --to 3.1.0 --dry-run --json-out /tmp/aso-state-migrate-plan.json
python3 agent-system/tools/aso/aso.py plan-next --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-plan.json
python3 agent-system/tools/aso/aso.py dashboard --root agent-system/tests/fixtures/state/valid_workspace --out /tmp/aso-stage2-dashboard.html
python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict --json-out /tmp/aso-stage2-checkpoint-preflight.json
```

`aso state init --dry-run` writes no files. Confirmed initialization requires
`--confirm-write` and writes only local ignored workspace state under the
selected root. `aso state migrate --dry-run` emits a deterministic migration
plan for compatible legacy sidecars; confirmed migration requires
`--confirm-write`, fails closed on malformed or ambiguous input, and writes
migration receipts under allowed `project-runtime/` report paths. `aso state
render` is read-only except for explicit output to `/tmp` or workspace
`project-runtime/reports` or `project-runtime/rendered` paths.

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
Runtime Schema `3.1.0` state. Proposal commands do not dispatch agents, do not
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
```

Create a local reference-mode generated project without vendoring
`agent-system/`:

```text
python3 agent-system/tools/aso/aso.py project create --local --engine-mode reference --target /tmp/demo-reference --name "Demo Reference" --slug demo-reference --profile generic --repo-url https://github.com/OWNER/demo-reference.git --branch main
python3 agent-system/tools/aso/aso.py project verify-clean --root /tmp/demo-reference --strict
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
initialize Runtime Schema `3.1.0` sidecars under the generated project's
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
make ci
```

The smoke target includes CLI help, package status, strict package lint,
strict package doctor, read-only package-layout verification, valid
design/context-pack fixtures, rule validation, state sidecar verification,
dry-run next-action planning, static dashboard rendering to `/tmp`,
and checkpoint preflight. The CI target runs the local test, smoke, doctor,
lint, and whitespace diff checks. CI should use the same local commands and
must not require secrets, network credentials, real remotes, publishing
permissions, or live automation authority.

`make install-user` runs `install.sh` against `.venv`. `make verify-install`
uses the installed `.venv/bin/aso` command for package status, strict lint,
strict doctor, and strict package-layout verification. Package validation does
not require `.venv`; direct script checks remain the compatibility baseline.

Stage 2 state-contract examples use the corrected valid workspace fixture at
`agent-system/tests/fixtures/state/valid_workspace`. The dry-run plan example
reports the canonical next action value `CREATE_AGENT`; it is evidence only and
does not dispatch an agent.

The helper supports status, lint, doctor, package-layout verification, design
validation, context pack validation, rule validation, Runtime Schema `3.1.0`
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
