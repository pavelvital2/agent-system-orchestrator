# ASO_LOCK_CONTRACT

## Purpose

`aso.lock` records the ASO package tuple and generated-project metadata needed
to verify a Project Factory workspace.

The lock file is a generated project artifact. It is intended to be tracked by
the generated project repository.

## File Name And Format

The lock file name is:

```text
aso.lock
```

The file format is JSON.

Project Factory P0 uses:

```text
lockfile_version: 1.0
package version: 3.2.0
runtime schema: 3.0.0
```

The runtime schema remains `3.0.0`. `aso.lock` describes package/product
capability and generated-project metadata; it does not alter runtime-state
semantics.

## Required Shape

Project Factory P0 lock files must include:

```json
{
  "lockfile_version": "1.0",
  "aso_engine": {
    "package_name": "agent-system-orchestrator",
    "version": "3.2.0",
    "runtime_schema": "3.0.0",
    "source": "https://github.com/pavelvital2/agent-system-orchestrator",
    "engine_mode": "vendored"
  },
  "project": {
    "name": "Demo Project",
    "slug": "demo-project",
    "profile": "generic",
    "repo_url": "https://github.com/example/demo-project.git",
    "default_branch": "main"
  },
  "publication_boundary": {
    "ignored_roots": [
      "project-input/",
      "project-runtime/",
      "project-archive/",
      ".venv/"
    ],
    "forbidden_tracked_roots": [
      "project-input/",
      "project-runtime/",
      "project-archive/",
      ".venv/"
    ]
  }
}
```

Implementations may add fields when they are deterministic and documented, but
they must preserve the required fields and meanings above.

## Required Fields

### Root

`lockfile_version` must be the string:

```text
1.0
```

### `aso_engine`

Required fields:

```text
package_name
version
runtime_schema
source
engine_mode
```

Rules:

- `package_name` must identify the ASO package.
- `version` must be the package version used to create or verify the project.
- `runtime_schema` must be `3.0.0` for Project Factory P0.
- `source` should identify the package source used by the generated project.
- `engine_mode` must be `vendored` for the required P0 implementation.

### `project`

Required fields:

```text
name
slug
profile
repo_url
default_branch
```

Rules:

- `name` is the display name of the generated project.
- `slug` is the filesystem/repository-safe project identifier.
- `profile` is the selected project profile, defaulting to `generic` when not
  explicitly provided.
- `repo_url` is metadata only in P0 and must not trigger live GitHub or remote
  repository creation.
- `default_branch` records the expected branch name, defaulting to `main`.

When no repository URL is known, implementations may use `null` for `repo_url`
if the validator accepts it. If a stricter implementation does not accept
`null`, it must require an explicit metadata value or documented placeholder.

### `publication_boundary`

Required fields:

```text
ignored_roots
forbidden_tracked_roots
```

Minimum required roots:

```text
project-input/
project-runtime/
project-archive/
.venv/
```

Implementations may include additional ignored or forbidden roots when those
roots strengthen the clean generated-project boundary.

## Engine Mode Contract

Project Factory P0 requires support for:

```text
vendored
```

In `vendored` mode, the generated project may include `agent-system/` package
content. Vendoring must exclude:

```text
.git/**
project-input/**
project-runtime/**
project-archive/**
.venv/**
.tmp/**
tmp/**
secrets/**
private/**
```

Vendoring must also exclude caches, logs, local upgrade packages, and
secret-like files.

## Verification Rules

`aso project verify-clean` must treat the lock as invalid when:

- `aso.lock` is missing;
- JSON parsing fails;
- `lockfile_version` is missing or unsupported;
- required root objects are missing;
- required fields are missing;
- `aso_engine.version` is incompatible with the verifier's supported package
  contract;
- `aso_engine.runtime_schema` is not `3.0.0` for Project Factory P0;
- `aso_engine.engine_mode` is unsupported;
- publication boundary roots omit required local ASO working roots;
- repository URL or default branch metadata conflicts with the actual Git
  repository when such verification is requested or available.

Strict verification must return non-zero for lock validation failures.

## Compatibility

P0 implementations must not require third-party Python dependencies for lock
reading or validation unless a later bounded architecture decision explicitly
accepts the dependency.

The lock contract is a package/product contract. It is not a runtime-state
schema migration.
