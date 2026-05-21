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

The package is a filesystem-governed instruction, template, lifecycle, and validation system for Codex CLI orchestration. It includes an experimental read-only ASO helper CLI at `agent-system/tools/aso/aso.py`.

This Project Factory P0 package records the active package metadata as the
governed `3.2.0` package/governance tuple with runtime schema `3.0.0`.
The runtime schema remains unchanged because this package adds local project
workspace creation and clean-repository verification without changing accepted
runtime state meaning.

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

Stage 2 command surfaces are also read-only or dry-run only:

```text
python3 agent-system/tools/aso/aso.py validate-rules --root . --strict
python3 agent-system/tools/aso/aso.py state verify --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-state.json
python3 agent-system/tools/aso/aso.py plan-next --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-plan.json
python3 agent-system/tools/aso/aso.py dashboard --root agent-system/tests/fixtures/state/valid_workspace --out /tmp/aso-stage2-dashboard.html
python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict --json-out /tmp/aso-stage2-checkpoint-preflight.json
```

Stage 3 package-layout diagnostics are read-only and verify package metadata,
entrypoint, hygiene, and canonical package-source coherence:

```text
python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
```

Project Factory P0 creates local generated project workspaces and verifies that
they are clean for publication. Local mode does not require secrets, GitHub
credentials, remote repository access, commit authority, push authority, or live
automation authority:

```text
python3 agent-system/tools/aso/aso.py project create --help
python3 agent-system/tools/aso/aso.py project verify-clean --help
python3 agent-system/tools/aso/aso.py project create --local --target /tmp/demo-project --name "Demo Project" --slug demo-project --profile generic --repo-url none --branch main
python3 agent-system/tools/aso/aso.py project verify-clean --root /tmp/demo-project --strict
```

Generated projects contain `aso.lock`, `.gitignore`, a minimal README, local
ignored ASO working roots when needed, and optional vendored safe
`agent-system/` content. They must not publish `project-input/`,
`project-runtime/`, `project-archive/`, virtual environments, caches, logs,
secret-like files, local upgrade packages, or ASO engine `.git` metadata.
Project Factory P0 does not create GitHub repositories and does not implement a
runtime daemon, dashboard control plane, distributed workers, agent dispatch, or
checkpoint execution.

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

The helper supports read-only status, lint, doctor, package-layout verification,
design validation, context pack validation, rule validation, state
verification, dry-run next-action planning, static dashboard rendering,
checkpoint eligibility preflight, and archive verify inspection. Its read-only
behavior is part of the ASO boundary. It does not dispatch agents, mutate
package or workspace state, perform checkpoints, commit, or push. For package
lint compatibility, this boundary is also stated as: ASO does not provide
mutation, dispatch, or checkpoint commands.

## Publication boundary

`project-input/`, `project-runtime/`, and `project-archive/` are local
generated or owner-input roots. Working upgrade packages, runtime results,
audit files, scratch notes, command logs, and local Codex artifacts from those
roots must not be published as package documentation. After an accepted upgrade
flow completes and the orchestrator-owned checkpoint is complete, remove local
upgrade packages and verify:

```text
git status --short project-input project-runtime project-archive
git ls-files project-input project-runtime project-archive
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
