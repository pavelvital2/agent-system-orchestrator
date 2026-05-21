# ASO Runtime State P2 v3.4.0 Release Notes

## Package Tuple

```text
package version: 3.4.0
governance ruleset version: 3.4.0
runtime schema: 3.1.0
```

Runtime State P2 changes the ASO package capability surface by adding a
governed JSON-first runtime state foundation. Filesystem governance remains
canonical for package publication and owner boundaries, while P2 runtime state
uses JSON sidecars under `project-runtime/state/` as the canonical machine
contract for initialized workspaces.

## Added

- Runtime Schema `3.1.0` sidecar contract for:

```text
PROJECT_STATE.json
TASK_REGISTRY.json
NEXT_ACTION.json
CURRENT_GATE.json
WORKSPACE_IDENTITY.json
REPOSITORY_LOCK.json
ACCEPTED_ARTIFACTS.json
CHECKPOINT_STATE.json
SCHEMA_MANIFEST.json
```

- Guarded state initialization:

```text
aso state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --dry-run --json-out /tmp/aso-state-init-plan.json
aso state init --root /tmp/aso-state-demo --project-name "State Demo" --project-slug state-demo --profile generic --repo-url none --branch main --confirm-write --json-out /tmp/aso-state-init-receipt.json
```

`--dry-run` writes no files. Confirmed initialization requires
`--confirm-write` and writes only local ignored workspace state under
`project-runtime/state/` for the selected root.

- Deterministic migration planning for compatible legacy state:

```text
aso state migrate --root agent-system/tests/fixtures/state/valid_workspace --to 3.1.0 --dry-run --json-out /tmp/aso-state-migrate-plan.json
```

Confirmed migration requires `--confirm-write`, fails closed on malformed or
ambiguous sidecars, converts compatible legacy `2.0.0`/`3.0.0` sidecars to the
`3.1.0` envelope, and records migration receipts under allowed runtime report
paths.

- Read-only compatibility rendering from JSON state:

```text
aso state render --root /tmp/aso-state-demo --format markdown --out /tmp/aso-state-render.md
aso state render --root /tmp/aso-state-demo --format json --out /tmp/aso-state-render.json
```

Render output is allowed under `/tmp`, `project-runtime/reports`, or
`project-runtime/rendered`. Rendering does not mutate canonical JSON sidecars.

- Runtime Schema `3.1.0` verification:

```text
aso state verify --root /tmp/aso-state-demo --strict --json-out /tmp/aso-state-verify.json
```

Verification checks envelope fields, sidecar types, schema alignment, malformed
JSON, task references, next action and gate references, workspace identity,
repository lock signals, and compatibility diagnostics.

## Preserved

Project Factory P1 remains available in package version `3.4.0`:

```text
aso project create --local --engine-mode vendored --target /tmp/demo-vendored --name "Demo Vendored" --slug demo-vendored --profile generic --repo-url none --branch main
aso project create --local --engine-mode reference --target /tmp/demo-reference --name "Demo Reference" --slug demo-reference --profile generic --repo-url https://github.com/OWNER/demo-reference.git --branch main
aso project create --github --dry-run --engine-mode reference --target /tmp/demo-github --name "Demo GitHub" --slug demo-github --profile generic --branch main --owner OWNER --repo demo-github --private --json-out /tmp/demo-github-plan.json
aso wizard --answers path/to/answers.json --dry-run --json-out /tmp/aso-wizard-plan.json
```

Existing P0/P1 generated-project lockfiles remain compatible when they satisfy
accepted package-version, runtime-schema, engine-mode, and publication-boundary
rules. Local generated projects may initialize Runtime Schema `3.1.0` JSON
sidecars under their ignored `project-runtime/state/` root. Reference-mode
generated repositories must not track `agent-system/`; vendored-mode
generated repositories may publish only safe generated-project `agent-system/`
content that passes the clean boundary.

## Publication Boundary

Runtime State P2 does not change the owner-root publication boundary.
Generated projects and ASO package commits must not track or publish:

```text
project-input/
project-runtime/
project-archive/
.venv/
caches
logs
secret-like files
local upgrade packages
ASO engine .git metadata
```

Confirmed GitHub publish remains target-scoped to the generated project. It is
not authority to stage, commit, push, tag, merge, or publish the ASO package
repository or local owner roots.

## Limitations

Runtime State P2 does not implement:

- proposal/apply mutation layer;
- runtime daemon;
- live agent dispatch;
- checkpoint executor;
- distributed workers or external queue infrastructure.

Diagnostic, validator, planning, dashboard, archive, and checkpoint-preflight
surfaces remain read-only, dry-run, or proposal-only. The only P2 runtime state
writes are explicit `state init --confirm-write`, explicit `state migrate
--confirm-write`, and generated-project local initialization under ignored
workspace roots.

## Documentation

Updated package and install documentation record package version `3.4.0`,
governance ruleset version `3.4.0`, runtime schema `3.1.0`, state
init/migrate/render/verify examples, migration behavior, generated-project
runtime-state initialization, publication boundaries, and deferred automation
items.
