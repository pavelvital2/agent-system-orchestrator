# PROJECT_FACTORY_P0_SPEC

## Purpose

Project Factory P0 defines the first bounded ASO product layer for creating
clean local project workspaces from the ASO package.

The target package tuple is:

```text
package version: 3.2.0
runtime schema: 3.0.0
```

The runtime schema remains `3.0.0`. Project Factory P0 adds package CLI and
workspace creation capability; it does not change the accepted meaning of
current runtime state files.

## Scope

Project Factory P0 is limited to:

- creating a local generated project workspace;
- writing `aso.lock`;
- writing a generated-project `.gitignore`;
- writing a minimal generated-project `README.md`;
- creating local ignored ASO working roots when needed;
- optionally vendoring safe `agent-system/` package content;
- verifying that a generated project is clean for publication.

Project Factory P0 must not implement:

- runtime daemon;
- distributed workers;
- Redis, NATS, Kafka, Postgres, or queue-backed orchestration;
- multi-user RBAC;
- SaaS dashboard;
- VSCode extension;
- live GitHub repository creation;
- agent dispatch;
- checkpoint execution.

## Command Surface

Project Factory P0 adds a new CLI command group:

```text
aso project
```

Required canonical subcommands:

```text
aso project create --local
aso project verify-clean
```

Existing ASO commands must not be removed, renamed, or given incompatible
semantics. Optional aliases are allowed only when the canonical command surface
remains visible and documented.

## `aso project create --local`

### Required Inputs

Recommended canonical flags:

```text
--target PATH
--name TEXT
--slug TEXT
--profile TEXT
--repo-url URL_OR_NONE
--branch TEXT
--engine-mode vendored
```

Allowed defaults:

```text
--profile generic
--branch main
--engine-mode vendored
```

`--target`, `--name`, and `--slug` should be explicit unless the implementation
defines a deterministic derivation rule.

### Required Behavior

`aso project create --local` must:

1. Validate the target path.
2. Create the target directory if it does not exist.
3. Refuse to overwrite a non-empty target unless a separately documented safe
   force flag exists.
4. Generate `aso.lock` using the Project Factory lock contract.
5. Generate `.gitignore` using the generated-project clean repo contract.
6. Generate a minimal `README.md` with local next steps.
7. Create `project-input/`, `project-runtime/`, and `project-archive/` only as
   local ignored working roots when needed.
8. In `vendored` mode, copy only safe package content into `agent-system/`.
9. Exclude repository metadata, local owner input, runtime state, archives,
   caches, logs, virtual environments, upgrade packages, and secret-like paths.
10. Never copy the ASO engine repository `.git` history.
11. Never require secrets, GitHub credentials, remote repository access, commit
    authority, push authority, or live automation authority in local mode.
12. Print a deterministic summary of created files, engine mode, package
    version, runtime schema, and next verification command.

## `aso project verify-clean`

### Required Inputs

Recommended canonical flags:

```text
--root PATH
--strict
--json-out PATH
```

### Required Behavior

`aso project verify-clean` must:

1. Verify that `aso.lock` exists.
2. Verify that `aso.lock` is valid JSON and conforms to the lock contract.
3. Verify that `.gitignore` protects local ASO working roots.
4. Verify that `project-input/`, `project-runtime/`, `project-archive/`, and
   `.venv/` are not tracked when the target is a Git repository.
5. Verify that there is no nested `.git` directory under vendored
   `agent-system/` content.
6. Verify that local upgrade packages, known cache directories, old runtime
   results, archives, logs, and secret-like paths are not tracked.
7. Verify expected repository URL and default branch when they are provided by
   `aso.lock` or command flags and the target is a Git repository.
8. Return non-zero in strict mode on any violation.
9. Produce deterministic human-readable output and, when `--json-out` is used,
   deterministic machine-readable output.

## Engine Modes

Project Factory P0 must implement at least:

```text
vendored
```

`vendored` mode copies the package content needed by a generated project into
`agent-system/` while applying the publication boundary and exclusion rules.

Future engine modes may be added only by a bounded design and audit path. A
possible future mode is:

```text
linked
```

`linked` mode is out of scope for P0 unless a later task explicitly defines and
accepts its safety contract.

## Generated Workspace Outputs

A clean generated project may include:

```text
aso.lock
README.md
.gitignore
project-input/
project-runtime/
project-archive/
agent-system/
.github/workflows/
.devcontainer/
```

`project-input/`, `project-runtime/`, and `project-archive/` may exist locally
in the generated project, but they must be ignored and must not be published as
tracked project content.

## Version And Schema Policy

Project Factory P0 uses:

```text
package version: 3.2.0
runtime schema: 3.0.0
```

Implementation tasks must stop and request a governance decision if they
discover that runtime-state semantics need to change. Such a change is outside
this P0 contract and must not be handled by silently bumping runtime schema.

## Publication Boundary

Generated projects must be capable of living in their own clean repositories.
They must not publish ASO local working data, local owner input, runtime
execution state, archival material, local upgrade packages, virtual
environments, caches, logs, secrets, credentials, cookies, or engine repository
metadata.

The detailed generated-project boundary is defined in:

```text
agent-system/12_project_factory/GENERATED_PROJECT_CLEAN_REPO_CONTRACT.md
```

The lock metadata contract is defined in:

```text
agent-system/12_project_factory/ASO_LOCK_CONTRACT.md
```
