# GENERATED_PROJECT_CLEAN_REPO_CONTRACT

## Purpose

This contract defines when a Project Factory generated project is clean enough
to be used as an independent repository.

The contract protects the ASO publication boundary: generated projects may keep
local ASO working roots on disk, but they must not publish local owner input,
runtime state, archive data, local upgrade packages, credentials, caches, or
engine repository metadata.

## Clean Repository Rule

A generated project is clean when:

- it has a valid `aso.lock`;
- it has a `.gitignore` that protects ASO local working roots and common local
  machine artifacts;
- no forbidden local root or artifact is tracked by Git;
- no vendored package content contains nested Git repository metadata;
- the lock package tuple is compatible with the active Project Factory
  boundary:

```text
active package version: 3.7.0
active runtime schema: 3.1.0
compatible historical tuples:
3.6.1/3.1.0, 3.6.0/3.1.0, 3.5.0/3.1.0, 3.4.0/3.1.0,
3.3.0/3.0.0, 3.2.0/3.0.0
```

## Required Local Ignore Entries

The generated project `.gitignore` must include at least:

```gitignore
/project-input/
/project-runtime/
/project-archive/
/.tmp/
/tmp/
/.venv/
.env
.env.*
*.pem
*.key
*.crt
*.p12
*.pfx
*.cookie
cookies.json
secrets/
private/
**/__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.DS_Store
```

Implementations may add stricter ignore entries, but they must not weaken the
minimum publication boundary above.

## Forbidden Published Paths

Generated projects must not track:

```text
project-input/**
project-runtime/**
project-archive/**
.venv/**
.tmp/**
tmp/**
secrets/**
private/**
```

Generated projects must not track local upgrade package paths, including:

```text
project-input/aso_upgrade_project_factory_p0/**
```

Generated projects must not include nested repository metadata copied from the
engine checkout:

```text
agent-system/**/.git/**
.git/**
```

The root `.git/` directory of the generated project itself is allowed when the
user initializes the generated project as a Git repository. It must be created
by the generated project owner or their Git tooling, not copied from the ASO
engine repository.

## Forbidden Published Artifact Classes

Generated projects must not track:

- local owner-input packages;
- runtime state, worker results, audit results, checkpoint receipts, old run
  logs, generated dashboards, or runtime reports;
- project archives and superseded local materials;
- virtual environments;
- Python caches and test caches;
- local temporary directories;
- environment files;
- keys, certificates, cookies, tokens, or secret-like files;
- ASO engine repository history;
- local packaging or upgrade scratch artifacts.

## Allowed Generated Files

A Project Factory generated project may track:

```text
aso.lock
README.md
.gitignore
agent-system/**
.github/workflows/**
.devcontainer/**
```

`agent-system/**` is allowed only when `aso.lock` selects an engine mode that
requires vendoring and the copied content satisfies this clean repo contract.

Optional workflow and devcontainer files are allowed only when they do not
require secrets, credentials, live remote access, dispatch authority, checkpoint
execution, commit authority, or push authority for local verification.

## Local Working Roots

The following directories may exist in a generated project as local ignored
working roots:

```text
project-input/
project-runtime/
project-archive/
```

They are generated workspace state, not publishable package or project
documentation. Their contents must remain ignored unless a later bounded
project-specific governance decision explicitly changes the publication model.
P5 artifact package storage under `project-runtime/artifacts/raw/`,
`project-runtime/artifacts/candidates/`,
`project-runtime/artifacts/accepted/`, and
`project-runtime/artifacts/rejected/` is included in this local ignored
workspace boundary and must not be tracked or published by Project Factory
flows.

## Verification Contract

`aso project verify-clean --root PATH --strict` must fail when:

- `aso.lock` is missing;
- `aso.lock` is invalid JSON;
- required lock fields are missing or incompatible;
- `.gitignore` does not protect required local roots;
- a forbidden path is tracked by Git;
- a forbidden artifact class is tracked by Git;
- vendored `agent-system/` content contains nested `.git` metadata;
- repository URL or default branch conflicts with `aso.lock` when those values
  are available for verification;
- strict mode detects any publication-boundary violation.

When `--json-out PATH` is provided, the verification output should include:

```text
status
root
lockfile_status
gitignore_status
tracked_forbidden_paths
nested_git_paths
repo_metadata_status
package_version
runtime_schema
engine_mode
violations
```

The JSON output path is command output, not a generated project artifact. The
caller should write it outside the clean repository or to an ignored location.

## No Runtime Schema Change

This contract does not change runtime-state semantics. In the active P5
package it relies on package version `3.7.0`, runtime schema `3.1.0`, and
artifact package schema `1.0.0`, while preserving compatibility for accepted
historical generated-project lock tuples.
