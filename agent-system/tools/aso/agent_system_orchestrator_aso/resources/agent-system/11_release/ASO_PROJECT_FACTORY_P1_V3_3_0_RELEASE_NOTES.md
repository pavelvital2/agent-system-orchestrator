# ASO Project Factory P1 v3.3.0 Release Notes

## Package Tuple

```text
package version: 3.3.0
runtime schema: 3.0.0
```

Project Factory P1 changes the package capability surface. It does not change
the accepted meaning of runtime state files, so the runtime schema remains
`3.0.0`.

## Added

- Local reference-mode generated projects:

```text
aso project create --local --engine-mode reference --target /tmp/demo-reference --name "Demo Reference" --slug demo-reference --profile generic --repo-url https://github.com/OWNER/demo-reference.git --branch main
```

- GitHub publication dry-run planning:

```text
aso project create --github --dry-run --engine-mode reference --target /tmp/demo-github --name "Demo GitHub" --slug demo-github --profile generic --branch main --owner OWNER --repo demo-github --private --json-out /tmp/demo-github-plan.json
```

- Confirmed GitHub publish:

```text
aso project create --github --confirm-publish --engine-mode reference --target /tmp/demo-github --name "Demo GitHub" --slug demo-github --profile generic --branch main --owner OWNER --repo demo-github --private
```

GitHub dry-run and confirmed publish use the selected `vendored` or
`reference` engine mode. Reference-mode GitHub repositories must not track
`agent-system/`; vendored-mode GitHub repositories may publish only safe
generated-project `agent-system/` content that passes the clean boundary.

- Guided Project Factory wizard:

```text
aso wizard
aso wizard --answers path/to/answers.json --dry-run --json-out /tmp/aso-wizard-plan.json
```

## Preserved

Local vendored mode remains available and preserves the P0 generated-project
behavior:

```text
aso project create --local --engine-mode vendored --target /tmp/demo-vendored --name "Demo Vendored" --slug demo-vendored --profile generic --repo-url none --branch main
aso project verify-clean --root /tmp/demo-vendored --strict
```

## GitHub CLI Boundary

GitHub CLI (`gh`) is optional for installation, local generated-project
creation, local verification, wizard dry-run, and GitHub dry-run planning.

`gh` is required only for confirmed GitHub publish mode. Confirmed publish also
requires authenticated GitHub access, Git availability, explicit
`--confirm-publish`, exactly one visibility flag, a clean generated project, and generated-project publication-boundary checks.

Dry-run mode must not create a repository, push to a remote, require
credentials, or contact GitHub.

## Clean Repository Guarantees

Generated projects contain `aso.lock`, `.gitignore`, a minimal generated
README, and ignored local working roots when needed. Vendored mode may include
safe `agent-system/` content. Reference mode records the external ASO engine in
`aso.lock` and must not track `agent-system/`.

Generated projects must not publish:

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

Confirmed GitHub publish is target-scoped to the generated project repository.
It is not authority to stage, commit, push, tag, merge, or publish the ASO
package repository or local `project-input`, `project-runtime`, or
`project-archive` state.

## Boundaries

Project Factory P1 does not implement:

- runtime daemon;
- dashboard control plane;
- distributed workers;
- live agent dispatch;
- checkpoint executor.

## Documentation

Updated package and install documentation record local vendored creation, local
reference creation, GitHub dry-run planning, GitHub confirmed publish, wizard
usage, safety boundaries, package version `3.3.0`, and unchanged runtime schema
`3.0.0`.
