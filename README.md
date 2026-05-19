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

This Stage 2 state-contract correction branch updates the active package
metadata to the governed `3.0.2` package/governance tuple with runtime schema
`3.0.0`. The correction resolves drift among state sidecars, templates,
schemas, fixtures, validator expectations, command examples, and release
evidence.

## Local install and command surface

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

Repeatable root targets:

```text
make install
make test
make smoke
make doctor
make lint
make ci
```

The smoke target includes CLI help, package status, strict package lint,
strict package doctor, valid design/context-pack fixtures, rule validation,
state sidecar verification, dry-run next-action planning, static dashboard
rendering to `/tmp`, checkpoint preflight, and the local governance smoke
runner. The CI target runs the local test, smoke, doctor, lint, and whitespace
diff checks. CI should use the same local commands and must not require
secrets, network credentials, real remotes, or publishing permissions.

Stage 2 state-contract examples use the corrected valid workspace fixture at
`agent-system/tests/fixtures/state/valid_workspace`. The dry-run plan example
reports the canonical next action value `CREATE_AGENT`; it is evidence only and
does not dispatch an agent.

The helper supports read-only status, lint, doctor, design validation, context
pack validation, rule validation, state verification, dry-run next-action
planning, static dashboard rendering, checkpoint eligibility preflight, and
archive verify inspection. Its read-only behavior is part of the ASO boundary.
It does not dispatch agents, mutate package or workspace state, perform
checkpoints, commit, or push. For package lint compatibility, this boundary is
also stated as: ASO does not provide mutation, dispatch, or checkpoint
commands.

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
The historical Stage 2 validation report is
`agent-system/11_release/STAGE2_UPGRADE_VALIDATION_REPORT.md`; it is superseded
for current acceptance by the Stage 2 state-contract correction. The draft
correction report is
`agent-system/11_release/STAGE2_STATE_CONTRACT_CORRECTION_VALIDATION_REPORT.md`.
Task 006 owns final correction validation evidence and must not be pre-claimed
here.
