# REFERENCE_ENGINE_MODE_CONTRACT

## Purpose

Reference engine mode lets generated user repositories stay clean and small
without vendored ASO engine files.

The generated project records the ASO engine source and package tuple in
`aso.lock`, while ASO command execution comes from an installed ASO CLI or
another external ASO engine source.

## Mode Name

The engine mode name is:

```text
reference
```

## Version And Schema

Project Factory P1 reference mode uses:

```text
package version: 3.3.0
runtime schema: 3.0.0
```

The runtime schema remains `3.0.0`. Reference mode changes generated-project
packaging, not runtime-state semantics.

## Required Lockfile Fields

`aso.lock` must record the ASO engine reference:

```json
{
  "aso_engine": {
    "package_name": "agent-system-orchestrator",
    "version": "3.3.0",
    "runtime_schema": "3.0.0",
    "source": "https://github.com/pavelvital2/agent-system-orchestrator",
    "engine_mode": "reference"
  }
}
```

The lock file must also preserve the required generated-project metadata and
publication boundary fields defined by the Project Factory lock contract.

## Generated Project Contents

Reference mode should include:

```text
.gitignore
README.md
aso.lock
```

Reference mode should not include:

```text
agent-system/
project-input tracked files
project-runtime tracked files
project-archive tracked files
local upgrade packages
ASO engine .git metadata
secret-like files
```

Local ignored roots may exist on disk for owner input and runtime use:

```text
project-input/
project-runtime/
project-archive/
```

They are local workspace roots and must not be tracked or published.

## Engine Resolution Boundary

Reference mode does not vendor executable ASO engine code into the generated
project. Users run ASO commands through an installed CLI or another external
engine source identified by the lock metadata.

Generated-project documentation may provide local install or verification
instructions, but it must not embed secrets, credentials, local ASO checkout
paths, or machine-specific runtime state as publishable content.

## GitHub Publication Boundary

Reference mode is the required Project Factory P1 engine mode for GitHub
publish.

Reference-mode GitHub repositories may track only clean generated-project
files, such as:

```text
.gitignore
README.md
aso.lock
.github/workflows/**
.devcontainer/**
```

They must not track vendored `agent-system/` content unless a later bounded
contract explicitly changes the GitHub publication model.

## Verification Rules

`aso project verify-clean --root PATH --strict` must treat a reference-mode
generated project as invalid when:

- `aso.lock` is missing or invalid JSON;
- `aso_engine.engine_mode` is not `reference`;
- `aso_engine.runtime_schema` is not `3.0.0`;
- required generated-project metadata is missing;
- `.gitignore` does not protect local working roots;
- `agent-system/` is tracked in a reference-mode generated project;
- `project-input/`, `project-runtime/`, or `project-archive/` is tracked;
- local upgrade packages, caches, logs, virtual environments, or secret-like
  files are tracked;
- ASO engine `.git` metadata is present in generated-project tracked files.

Strict verification must return non-zero for reference-mode publication
boundary violations.

## No Runtime Schema Change

Reference mode is a Project Factory packaging mode. It is not a runtime-state
schema migration and must not change the runtime schema from `3.0.0`.

