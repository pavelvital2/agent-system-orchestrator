# ASO Project Factory P0 v3.2.0 Release Notes

## Package Tuple

```text
package version: 3.2.0
runtime schema: 3.0.0
```

Project Factory P0 changes the package capability surface. It does not change
the accepted meaning of runtime state files, so the runtime schema remains
`3.0.0`.

## Added

- Project Factory command group:

```text
aso project
```

- Local generated-project creation:

```text
aso project create --local --target /tmp/demo-project --name "Demo Project" --slug demo-project --profile generic --repo-url none --branch main
```

- Generated-project clean repository verification:

```text
aso project verify-clean --root /tmp/demo-project --strict
```

- Generated project clean-repo contract covering `aso.lock`, `.gitignore`,
  minimal generated README content, ignored local ASO working roots, optional
  safe vendored `agent-system/` content, and publication-boundary checks.

## Clean Repository Guarantees

A Project Factory P0 generated project is intended to be clean for independent
local repository use when `aso project verify-clean --strict` passes. The clean
contract excludes tracked local owner input, runtime state, archives, local
upgrade packages, virtual environments, caches, logs, secret-like files, and ASO
engine repository metadata.

Generated projects may keep these local working roots on disk, but they must be
ignored and must not be published as tracked project content:

```text
project-input/
project-runtime/
project-archive/
```

The detailed contract is documented in:

```text
agent-system/12_project_factory/GENERATED_PROJECT_CLEAN_REPO_CONTRACT.md
```

## Boundaries

Project Factory P0 local mode does not require secrets, GitHub credentials,
remote repository access, commit authority, push authority, publication rights,
or live automation authority.

Project Factory P0 does not implement:

- runtime daemon;
- dashboard control plane;
- distributed workers;
- live GitHub repository creation;
- agent dispatch;
- checkpoint execution.

## Documentation

Updated package and install documentation record the v3.2.0 package version,
the unchanged v3.0.0 runtime schema, Project Factory P0 command examples, and
generated-project clean repository limitations.
