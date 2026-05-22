# ASO local user install

Run from the repository root:

```text
bash install.sh
```

On Windows PowerShell, run from the repository root:

```text
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer creates `.venv`, installs this checkout as an editable package,
and verifies the installed `aso` command. It uses local Python packaging only;
it does not require secrets, GitHub credentials, remote repository access,
dispatch authority, checkpoint execution, commit, push, or publication rights.

This install document covers package version `3.6.0` with runtime schema
`3.1.0`. Corrected P4 adds designer-led project design, gap governance,
audited owner question routing, and owner decision recording while preserving
the Runtime State P2/P3 sidecar schema and the Project Factory P1 command
boundary.

Both installers accept a Python executable and virtual environment path:

```text
bash install.sh --python python3 --venv .venv
powershell -ExecutionPolicy Bypass -File install.ps1 -Python python -Venv .venv
```

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

Project Factory help should also be available after install:

```text
aso project create --help
aso project verify-clean --help
aso wizard --help
```

Runtime State P2 state commands should be available after install:

```text
aso state --help
aso state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --dry-run --json-out /tmp/aso-state-init-plan.json
aso state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --confirm-write --json-out /tmp/aso-state-init-receipt.json
aso state verify --root /tmp/aso-state-demo --strict --json-out /tmp/aso-state-verify.json
aso state render --root /tmp/aso-state-demo --format markdown --out /tmp/aso-state-render.md
aso state migrate --root agent-system/tests/fixtures/state/valid_workspace --to 3.1.0 --dry-run --json-out /tmp/aso-state-migrate-plan.json
```

`aso state init --dry-run` writes no files. Confirmed initialization requires
`--confirm-write` and writes only local ignored workspace sidecars under
`project-runtime/state/`. `aso state migrate --dry-run` emits a deterministic
plan for compatible legacy sidecars; confirmed migration requires
`--confirm-write`, fails closed on malformed or ambiguous input, and records
receipts under allowed `project-runtime/` report paths. `aso state render` is
read-only except for explicit output to `/tmp`, `project-runtime/reports`, or
`project-runtime/rendered`.

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
and every guard passes. Checkpoint proposal records eligibility evidence only;
it does not stage, commit, push, tag, or execute a checkpoint.

Create and verify a local vendored generated project without secrets or remote
access:

```text
aso project create --local --engine-mode vendored --target /tmp/demo-vendored --name "Demo Vendored" --slug demo-vendored --profile generic --repo-url none --branch main
aso project verify-clean --root /tmp/demo-vendored --strict
```

Create and verify a local reference generated project without vendoring
`agent-system/`:

```text
aso project create --local --engine-mode reference --target /tmp/demo-reference --name "Demo Reference" --slug demo-reference --profile generic --repo-url https://github.com/OWNER/demo-reference.git --branch main
aso project verify-clean --root /tmp/demo-reference --strict
```

Local generated projects may initialize Runtime Schema `3.1.0` JSON sidecars
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
