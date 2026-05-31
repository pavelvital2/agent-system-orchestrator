# ASO local user install

## Clean source install

For source-hygiene validation, use the clean installer from the repository
root:

```text
bash agent-system/scripts/install_aso_clean.sh --source . --venv /tmp/aso_clean_install_venv --fresh --with-test
source /tmp/aso_clean_install_venv/bin/activate
aso --help
aso status --root . --mode package
```

The clean installer archives the tracked ASO source into an isolated temporary
directory, installs from that copy, and compares the original repository git
status before and after installation. The virtual environment and optional
`--source-copy` path must be outside the source repository. Use `--with-test`
to install the supported `test` extra.

Direct local path installs such as `python3 -m pip install .` or
`python3 -m pip install -e .` are development shortcuts only. They are not the
official clean-source validation path for this package because the current
setuptools backend may write build metadata into the live checkout. Route clean
install checks through `agent-system/scripts/install_aso_clean.sh`.

To verify the source status externally around the clean install:

```text
ASO_ROOT=$(pwd)
git status --short --branch > /tmp/aso_before_install_status.txt
rm -rf /tmp/aso_clean_install_venv /tmp/aso_clean_install_src
bash agent-system/scripts/install_aso_clean.sh --source "$ASO_ROOT" --venv /tmp/aso_clean_install_venv --fresh --source-copy /tmp/aso_clean_install_src --with-test
. /tmp/aso_clean_install_venv/bin/activate
aso --help
aso status --root "$ASO_ROOT" --mode package
cd "$ASO_ROOT"
git status --short --branch > /tmp/aso_after_install_status.txt
diff -u /tmp/aso_before_install_status.txt /tmp/aso_after_install_status.txt
```

## Editable user install

Run from the repository root:

```text
bash install.sh
```

On Windows PowerShell, run from the repository root:

```text
powershell -ExecutionPolicy Bypass -File install.ps1
```

The editable installer creates `.venv`, installs this checkout as an editable
package, and verifies the installed `aso` command. It uses local Python
packaging only; it does not require secrets, GitHub credentials, remote
repository access, dispatch authority, checkpoint execution, commit, push, or
publication rights.
On POSIX systems, `install.sh` creates an isolated virtual environment,
upgrades `pip`, `setuptools`, and `wheel` inside that environment, and installs
ASO with normal dependency and build isolation behavior. The installer must
still verify the canonical package from this checkout, not a root-level
duplicate Python tree.

This install document covers the S1.140 enum/schema/version coherence context:
package version `3.8.0` with runtime schema `3.2.0` and artifact package schema
`1.1.0`. P57 documents ASO workflow readiness through installed real-TZ
intake/bootstrap and read-only plan-next dispatchability while preserving the
Runtime State sidecar schema, the artifact package schema, and the Project
Factory P1 command boundary. Current real-TZ and real-E2E wording refers to
filesystem/governance lifecycle E2E smoke coverage for package install,
state lifecycle, governance routing, and read-only planning. It is not full automatic
product generation, does not claim full real-product Telegram bot
generation, and does not add semantic TZ reading, product-intake automation,
daemon mode, live dispatch, live runner behavior, product generation, secret
collection, or checkpoint execution.
The installed ASO helper supports read-only diagnostics plus explicit confirmed
writes; mutating surfaces document their guarding mode or confirmation flag and
bounded write roots.
P57 release validation is recorded in
`agent-system/11_release/ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_VALIDATION_REPORT.md`;
the in-repository remote CI evidence selector/procedure for P57 is recorded in
`agent-system/11_release/ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_REMOTE_CI_EVIDENCE.md`.
It does not record an immutable final run id or final post-push HEAD evidence.
Final real-TZ readiness criteria are documented, but final real-TZ acceptance
requires explicit owner instruction after P57 merge readiness and external
remote CI evidence.
In-repository remote CI evidence files define the selector/procedure only.
Immutable final run id, final HEAD, status, and URL evidence belongs in the
external release/audit RESULT after the final push, avoiding an infinite commit/CI
loop.

Both installers accept a Python executable and virtual environment path:

```text
bash install.sh --python python3 --venv .venv
powershell -ExecutionPolicy Bypass -File install.ps1 -Python python -Venv .venv
```

For development and schema contract test runs, install the supported test extra
inside the active environment:

```text
python3 -m pip install -e ".[test]"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s agent-system/tools/aso/tests
```

The runtime dependencies include `tomli>=2` only on Python versions older than
3.11 so installed Python 3.10 commands can parse TOML through the same
`tomllib` interface used on newer Python versions. The `test` extra includes
`jsonschema>=4.22`, which is required by the schema and dispatchability
contract tests.

Installed `aso` commands resolve required governance resources from packaged
package data, not from the virtualenv root or the current working directory.
Packaged ASO governance/runtime resources include the vendored Project Factory
source tree required for installed `aso project create --engine-mode vendored`
as well as installed package commands such as `plan-next`, without requiring an
adjacent source checkout. `aso package-layout verify` checks the packaged
resource manifest and hashes.

`aso package-sync verify` is a deprecated compatibility alias for
`aso package-layout verify`. It performs no copy synchronization and must not
be used to reintroduce duplicate package trees.

## Activate

```text
source .venv/bin/activate
aso --help
```

On Windows PowerShell:

```text
.\.venv\Scripts\Activate.ps1
aso --help
```

Direct script execution remains supported without activating the environment:

```text
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py --help
```

## Verify

```text
make verify-install
```

The verification target runs the installed `aso` command for package status,
Project Factory command help, strict package lint, strict package doctor, and
strict package-layout verification. Package validation still works without
`.venv` through direct script execution:

```text
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
```

Package checks should continue to pass `--mode package` explicitly. When
`--mode` is omitted, the CLI guards inference by detecting package roots from
`pyproject.toml` plus `agent-system/`, initialized workspace roots from
`project-runtime/state/`, and failing with `ASO_MODE_AMBIGUOUS` if both are
present.

CI uses the same reproducible clean install smoke path locally available as:

```text
make install-smoke
```

The target creates a temporary virtual environment, runs
`agent-system/scripts/install_aso_clean.sh`, verifies `aso --help`,
`aso status --root . --mode package`, strict package-layout verification, and
confirms the installed package resolves from the virtual environment
`site-packages` rather than the live source checkout.

To repeat only the test dependency install in an existing environment, run:

```text
make install-test
```

Initialized project workspaces use explicit workspace mode, materialized
runtime views, and bootstrap reconciliation checks:

```text
aso state render --root /path/to/project --confirm-write
aso state verify --root /path/to/project --strict
aso status --root /path/to/project --mode workspace
aso lint --root /path/to/project --mode workspace --strict
aso doctor --root /path/to/project --mode workspace --strict
aso lifecycle receive-result --root /path/to/project --from-result project-runtime/results/worker/RESULT_TASK_ID_ATTEMPT_001.md --confirm-write
aso artifact accept --root /path/to/project --package project-runtime/artifacts/candidates/TASK_ID/manifest.json --confirm-write
aso lifecycle terminate-agent --root /path/to/project --from-result project-runtime/results/worker/RESULT_TASK_ID_ATTEMPT_001.md --confirm-write
```

For a fresh real-TZ workspace, the official installed-orchestrator bootstrap
sequence is:

```text
ASO_ROOT=$(pwd)
WORK=/tmp/aso-real-tz-workspace
rm -rf "$WORK" /tmp/aso_clean_install_venv /tmp/aso_clean_install_src
mkdir -p "$WORK/project-input"
cp /path/to/TZ_REAL_E2E_TELEGRAM_BOT.md "$WORK/project-input/TZ_REAL_E2E_TELEGRAM_BOT.md"
bash agent-system/scripts/install_aso_clean.sh --source "$ASO_ROOT" --venv /tmp/aso_clean_install_venv --fresh --source-copy /tmp/aso_clean_install_src --with-test
. /tmp/aso_clean_install_venv/bin/activate
aso state init --root "$WORK" --tz project-input/TZ_REAL_E2E_TELEGRAM_BOT.md --confirm-write --json-out /tmp/aso-state-init.json
aso intake bootstrap --root "$WORK" --tz project-input/TZ_REAL_E2E_TELEGRAM_BOT.md --target-role requirements_analyst --confirm-write --json-out /tmp/aso-intake-bootstrap.json
aso state verify --root "$WORK" --strict --json-out /tmp/aso-state-verify.json
aso plan-next --root "$WORK" --strict --json-out /tmp/aso-plan-next.json
```

By default, confirmed runtime bootstrap writes record current UTC timestamps in
RFC 3339 `Z` form. Add `--deterministic-timestamps` to `state init` or
`intake bootstrap` only for regression tests, fixture generation, or
documentation captures that require the fixed test timestamp.

Unsupported install and bootstrap patterns:

- running clean install checks with `--venv` or `--source-copy` inside the live
  source checkout;
- using direct `pip install .` or `pip install -e .` as clean-source
  validation evidence;
- giving `state init` an IANA timezone string when a project TZ document is
  required;
- running `intake bootstrap` without `--confirm-write` and expecting state
  mutation;
- treating `plan-next` output as live dispatch, audit, checkpoint, commit, or
  push authority.

After a profile-agent RESULT is recorded, completion must follow the P5
artifact package sequence:

```text
RESULT_RECEIVED -> ARTIFACT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY
```

The profile-agent RESULT is treated as candidate artifact package output until
the orchestrator accepts it into `project-runtime/artifacts/accepted/` and
records the artifact acceptance receipt. Later context packs and task packets
must cite accepted artifact packages or rendered views under
`project-runtime/rendered/`; raw agent context is not accepted project truth.
`AUDIT_ROUTE_READY` does not dispatch live agents or execute checkpoints.

Project Factory help and a local create/verify-clean smoke should also be
available after install:

```text
aso project create --help
aso project verify-clean --help
aso wizard --help
aso project create --local --target /tmp/aso-install-project-smoke --name "ASO Install Smoke" --slug aso-install-smoke
aso project verify-clean --root /tmp/aso-install-project-smoke --strict
```

Runtime State P2 state commands should be available after install:

```text
aso state --help
mkdir -p /tmp/aso-state-demo/project-input
cp /path/to/TZ_REAL.md /tmp/aso-state-demo/project-input/TZ_REAL.md
aso state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --tz project-input/TZ_REAL.md --dry-run --json-out /tmp/aso-state-init-plan.json
aso state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --tz project-input/TZ_REAL.md --confirm-write --json-out /tmp/aso-state-init-receipt.json
aso state verify --root /tmp/aso-state-demo --strict --json-out /tmp/aso-state-verify.json
aso state render --root /tmp/aso-state-demo --format markdown --out /tmp/aso-state-render.md
aso state migrate --root agent-system/tests/fixtures/state/valid_workspace --to 3.2.0 --dry-run --json-out /tmp/aso-state-migrate-plan.json
```

`aso state init --dry-run` writes no files. Confirmed initialization requires a
real workspace-local TZ document passed with `--tz` and `--confirm-write`, and
writes only local ignored workspace files under `project-runtime/state/`,
derived `project-runtime/*.md` compatibility views, and the canonical
`project-input` TZ path. Confirmed `state init`, `intake bootstrap`, and
`state render` materialize canonical sidecar views plus legacy operator views
such as `GAP_REGISTER.md`, `AGENT_RESULTS_LOG.md`,
`ORCHESTRATOR_EVENTS_LOG.md`, and `STATUS_SUMMARY.md`; those legacy views are
not canonical state sidecars. Confirmed runtime writes use current UTC
timestamps by default;
`--deterministic-timestamps` is reserved for tests and fixtures.
`aso state migrate --dry-run` emits a deterministic plan for compatible legacy
sidecars; confirmed migration requires
`--confirm-write`, fails closed on malformed or ambiguous input, and records
receipts under allowed `project-runtime/` report paths. Without
`--confirm-write`, `aso state render` is read-only except for explicit report
output to `/tmp`, `project-runtime/reports`, or `project-runtime/rendered`.
With `--confirm-write`, it writes Markdown compatibility views from canonical
`project-runtime/state/*.json` sidecars plus legacy operator compatibility
views. In strict workspace mode, an active/open bootstrap
state with mandatory inputs must not be treated as terminal STOP-ready; an
IANA timezone string such as `Europe/Moscow` is not a valid `TZ_PATH` value
when `project-input/TZ.md` or another project TZ file should be referenced.

Corrected P4 design governance commands should also be available after
install:

```text
aso design --help
aso design verify --root agent-system/tests/fixtures/design_gap/valid_workspace --strict
aso design questions next --root agent-system/tests/fixtures/design_gap/valid_workspace --json-out /tmp/aso-dg4-next-question.json
aso design gate verify --root agent-system/tests/fixtures/design_gap/valid_workspace --stage DESIGN --strict
```

These commands validate and route existing project-designer-authored artifacts.
They do not interpret raw TZ content, choose product capabilities, or generate
owner questions. Owner-facing questions must be functional, workflow, UX,
interface, visualization, business-rule, reporting, priority, acceptance, or
operational-behavior questions; they must not ask the owner to choose
frameworks, databases, queues, schedulers, transports, hosting mechanisms,
ORMs, or API styles.

Owner-answer validation is used after an audited question has been presented:

```text
aso design decision record --root /path/to/project --question-id Q-001 --answer A --dry-run
```

Safe Proposal / Apply P3 command help should also be available after install:

```text
aso propose --help
aso propose next-task --help
aso propose transition --help
aso propose checkpoint --help
aso apply --help
```

Runnable dry-run examples:

```text
aso propose next-task --root agent-system/tests/fixtures/state/valid_workspace --dry-run --json-out /tmp/aso-p3-next-task-proposal.json
aso propose transition --root agent-system/tests/fixtures/state/valid_workspace --to TESTING --dry-run --json-out /tmp/aso-p3-transition-proposal.json
aso propose checkpoint --root agent-system/tests/fixtures/state/valid_workspace --dry-run --json-out /tmp/aso-p3-checkpoint-proposal.json
aso apply --root agent-system/tests/fixtures/state/valid_workspace --proposal /tmp/aso-p3-next-task-proposal.json --dry-run --json-out /tmp/aso-p3-apply-plan.json
python3 -m json.tool /tmp/aso-p3-apply-plan.json >/dev/null
```

These commands are local and guarded. Proposal dry-runs write no workspace
state except an explicit allowed `--json-out`; `--confirm-write` may persist a
proposal only under `project-runtime/proposals/`. Apply writes nothing unless
`--confirm-apply` is supplied, the proposal is fresh for the same workspace,
and every guard passes; confirmed apply writes only supported state sidecars,
receipts, and reports under `project-runtime/state`, `project-runtime/receipts`,
and `project-runtime/reports`. Checkpoint proposal records eligibility evidence
only; it does not stage, commit, push, tag, or execute a checkpoint.

Create and verify a local vendored generated project without secrets or remote
access:

```text
aso project create --local --engine-mode vendored --target /tmp/demo-vendored --name "Demo Vendored" --slug demo-vendored --profile generic --repo-url none --branch main
aso project verify-clean --root /tmp/demo-vendored --strict
cp /path/to/TZ_REAL.md /tmp/demo-vendored/project-input/TZ_REAL.md
python3 /tmp/demo-vendored/agent-system/tools/aso/aso.py state init --root /tmp/demo-vendored --tz project-input/TZ_REAL.md --confirm-write
python3 /tmp/demo-vendored/agent-system/tools/aso/aso.py intake bootstrap --root /tmp/demo-vendored --tz project-input/TZ_REAL.md --target-role requirements_analyst --confirm-write
python3 /tmp/demo-vendored/agent-system/tools/aso/aso.py plan-next --root /tmp/demo-vendored --strict
python3 /tmp/demo-vendored/agent-system/tools/aso/aso.py status --root /tmp/demo-vendored --mode workspace
python3 /tmp/demo-vendored/agent-system/tools/aso/aso.py lint --root /tmp/demo-vendored --mode workspace --strict
python3 /tmp/demo-vendored/agent-system/tools/aso/aso.py doctor --root /tmp/demo-vendored --mode workspace --strict
```

Create and verify a local reference generated project without vendoring
`agent-system/`:

```text
aso project create --local --engine-mode reference --target /tmp/demo-reference --name "Demo Reference" --slug demo-reference --profile generic --repo-url https://github.com/OWNER/demo-reference.git --branch main
aso project verify-clean --root /tmp/demo-reference --strict
cp /path/to/TZ_REAL.md /tmp/demo-reference/project-input/TZ_REAL.md
aso state init --root /tmp/demo-reference --tz project-input/TZ_REAL.md --confirm-write
aso intake bootstrap --root /tmp/demo-reference --tz project-input/TZ_REAL.md --target-role requirements_analyst --confirm-write
aso plan-next --root /tmp/demo-reference --strict
aso status --root /tmp/demo-reference --mode workspace
aso lint --root /tmp/demo-reference --mode workspace --strict
aso doctor --root /tmp/demo-reference --mode workspace --strict
```

Local generated projects may initialize Runtime Schema `3.2.0` JSON sidecars
under their ignored `project-runtime/state/` root. Those files are local
runtime state and must not be tracked or published by generated-project
publication flows.

After install, the guided wizard is available through the console command:

```text
aso wizard
aso wizard --answers path/to/answers.json --dry-run --json-out /tmp/aso-wizard-plan.json
```

GitHub dry-run planning and confirmed publish use the selected `vendored` or
`reference` engine mode. Reference-mode GitHub repositories must not track
`agent-system/`; vendored-mode GitHub repositories may publish only safe
generated-project `agent-system/` content that passes the clean boundary.

GitHub dry-run planning remains offline and does not require `gh`, GitHub
authentication, network access, repository creation, commits, or pushes:

```text
aso project create --github --dry-run --engine-mode reference --target /tmp/demo-github --name "Demo GitHub" --slug demo-github --profile generic --branch main --owner OWNER --repo demo-github --private --json-out /tmp/demo-github-plan.json
```

GitHub CLI is optional for installation and for all local or dry-run flows. It
is required only for confirmed GitHub publish mode, together with GitHub
authentication and explicit confirmation:

```text
gh auth status
aso project create --github --confirm-publish --engine-mode reference --target /tmp/demo-github --name "Demo GitHub" --slug demo-github --profile generic --branch main --owner OWNER --repo demo-github --private
```

Safe Proposal / Apply P3, corrected P4 design governance, and Project Factory
P1 do not add a runtime daemon, live dispatch, checkpoint executor, commit/push
automation, distributed workers, web control panel, ASO Studio, product
generation, or multi-project registry. The install and verification commands
do not grant commit, push, tag, merge, checkpoint, or publication authority for
the package repository or owner roots. Later control-plane, queue/dispatcher,
checkpoint executor, daemon, Studio, and distributed-worker work requires a
separate bounded package upgrade.

## Dev Container

When using VS Code Dev Containers, reopen this repository in the container.
The included `.devcontainer/devcontainer.json` uses the Python devcontainer
image and runs `bash install.sh` after creation. It creates only local
workspace state and does not require GitHub credentials, secrets, admin
privileges, commit rights, or publish rights.

## Update

After pulling or receiving new package changes, refresh the editable install:

```text
bash install.sh
make verify-install
```

## Cleanup

Remove the local virtual environment at any time:

```text
rm -rf .venv
```

On Windows PowerShell:

```text
Remove-Item -Recurse -Force .venv
```

Then use direct script checks, or recreate the environment with `bash
install.sh`. The local `.venv` directory is generated workspace state and must
not be staged, committed, or published.
