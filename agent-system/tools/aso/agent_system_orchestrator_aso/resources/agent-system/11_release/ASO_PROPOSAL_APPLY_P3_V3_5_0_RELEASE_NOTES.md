# ASO Proposal / Apply P3 v3.5.0 Release Notes

## Version Boundary

Package version: `3.5.0`
Governance ruleset version: `3.5.0`
Runtime schema version: `3.1.0`

Safe Proposal / Apply P3 preserves the Runtime State P2 sidecar schema and
adds a guarded local proposal/apply layer for runtime-state changes.

## Added

- `aso propose` command group for local proposal artifacts.
- `aso propose next-task` for deterministic next-task proposals from current
  Runtime Schema `3.1.0` sidecars.
- `aso propose transition --to STAGE` for guarded lifecycle transition
  proposals.
- `aso propose checkpoint` for checkpoint eligibility proposals only.
- `aso apply` for dry-run proposal validation and confirmed supported
  runtime-state apply.
- Proposal and receipt artifact contracts, templates, validators, tests, and
  docs.

Runnable dry-run examples:

```text
python3 agent-system/tools/aso/aso.py propose --help
python3 agent-system/tools/aso/aso.py propose next-task --root agent-system/tests/fixtures/state/valid_workspace --dry-run --json-out /tmp/aso-p3-next-task-proposal.json
python3 agent-system/tools/aso/aso.py propose transition --root agent-system/tests/fixtures/state/valid_workspace --to TESTING --dry-run --json-out /tmp/aso-p3-transition-proposal.json
python3 agent-system/tools/aso/aso.py propose checkpoint --root agent-system/tests/fixtures/state/valid_workspace --dry-run --json-out /tmp/aso-p3-checkpoint-proposal.json
python3 agent-system/tools/aso/aso.py apply --root agent-system/tests/fixtures/state/valid_workspace --proposal /tmp/aso-p3-next-task-proposal.json --dry-run --json-out /tmp/aso-p3-apply-plan.json
python3 -m json.tool /tmp/aso-p3-apply-plan.json >/dev/null
```

## Preserved

- Runtime Schema `3.1.0` remains the canonical runtime sidecar schema.
- P0 verify-clean behavior remains governed.
- P1 Project Factory local, reference, vendored, GitHub dry-run, confirmed
  publish, and wizard boundaries remain governed.
- P2 state init, migrate, render, verify, dashboard, plan-next, and
  checkpoint-preflight behavior remains compatible.
- Proposal dry-run writes no workspace state unless an explicit allowed
  `--json-out` is supplied.
- Apply dry-run validates proposals and writes no state.

## Guardrails

- Proposal/apply commands are local and guarded.
- `--confirm-write` is required to persist proposal artifacts under
  `project-runtime/proposals/`.
- `--confirm-apply` is required before supported runtime-state writes.
- Apply verifies proposal shape, workspace identity, base state hashes,
  staleness, path allowlists, and runtime state before/after apply.
- Checkpoint proposal is not checkpoint execution.
- Proposal/apply does not dispatch agents.
- Proposal/apply does not commit, push, tag, merge, invoke `gh`, or publish.

## Limitations

P3 does not implement a runtime daemon, live agent dispatch, checkpoint
executor, commit/push automation, distributed workers, web control panel,
multi-project registry, or live automation loop. P4 dashboard/control-plane
work, P5 queue/dispatcher work, P6 checkpoint executor work, daemon mode, and
distributed workers are deferred to later bounded package upgrades.

Confirmed apply is intentionally limited to supported safe runtime-state
operations represented in a fresh proposal for the same workspace. It is not a
general package mutation, owner-root mutation, checkpoint, or publication
mechanism.

## Publication Boundary

Proposal and receipt artifacts are runtime artifacts. In a user workspace they
belong under local ignored roots:

```text
project-runtime/proposals/
project-runtime/receipts/
project-runtime/reports/
```

The package repository may include schemas, templates, fixtures, tests, and
documentation for proposal/apply. It must not publish active runtime
proposal/receipt/report artifacts from `project-runtime/`, owner input from
`project-input/`, archive material from `project-archive/`, or virtual
environment state from `.venv/`.

Publication boundary check:

```text
git ls-files project-input project-runtime project-archive .venv
```

Expected tracked-file result: empty.
