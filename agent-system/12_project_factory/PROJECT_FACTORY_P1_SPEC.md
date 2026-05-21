# PROJECT_FACTORY_P1_SPEC

## Purpose

Project Factory P1 defines the bounded contract for creating clean generated
projects in local vendored mode, local reference mode, and GitHub publish mode
using the selected engine mode.

The target package tuple is:

```text
package version: 3.3.0
runtime schema: 3.0.0
```

The runtime schema remains `3.0.0`. Project Factory P1 adds project factory
capability and publication workflow contracts; it does not change the accepted
meaning of current runtime state files.

## Capability Model

Project Factory P1 supports three generated-project flows:

```text
local vendored mode
local reference mode
GitHub publish mode
```

`local vendored mode` preserves the Project Factory P0 behavior: it creates a
clean local generated project and may copy safe `agent-system/` package content
into the generated project.

`local reference mode` creates clean generated-project metadata without
vendoring `agent-system/`. The generated project records the external ASO
engine reference in `aso.lock` and relies on an installed ASO CLI or other
external ASO engine source.

`GitHub publish mode` creates a clean local generated project using the
selected `vendored` or `reference` engine mode, initializes a separate Git
repository for that generated project, creates a GitHub repository through the
GitHub CLI, and pushes only files that satisfy the generated-project
publication boundary.

## CLI Boundary

ASO CLI is a filesystem-governed helper CLI. Most command surfaces are
read-only diagnostics or dry-run proposals. Project Factory commands may create
or publish generated projects only within explicit target paths and only with
explicit confirmation for network or GitHub actions.

Diagnostics, validators, planning, dashboard rendering, archive inspection,
and checkpoint preflight remain read-only, dry-run, or proposal-only unless a
Project Factory command explicitly creates or publishes a generated project.

Existing ASO commands must not be removed, renamed, or given incompatible
semantics. P1 extends the Project Factory command surface; it does not grant
general mutation authority to status, lint, doctor, validators, planning,
dashboard, archive, package-layout, or checkpoint-preflight commands.

## Command Surface

Project Factory P1 uses:

```text
aso project
aso wizard
```

Required local generated-project commands:

```text
aso project create --local --engine-mode vendored
aso project create --local --engine-mode reference
aso project verify-clean
```

Required GitHub planning and publish commands:

```text
aso project create --github --dry-run --engine-mode vendored|reference
aso project create --github --confirm-publish --engine-mode vendored|reference
```

Required wizard commands:

```text
aso wizard
aso wizard --answers PATH --dry-run --json-out PATH
```

## Flag Semantics

`--local` and `--github` are mutually exclusive.

`--dry-run` and `--confirm-publish` are mutually exclusive for GitHub mode.
Non-dry-run GitHub mode requires `--confirm-publish`.

Visibility flags are mutually exclusive. GitHub mode must select exactly one
repository visibility when a real publish is requested:

```text
--private
--public
--internal
```

P1 engine mode choices are:

```text
vendored
reference
```

GitHub publish mode uses the selected engine mode. Reference mode records the
external ASO engine in `aso.lock` and must not publish vendored
`agent-system/` content. Vendored mode may publish only safe generated-project
`agent-system/` content that passes the generated-project clean boundary.

## Safe Mutation Boundary

Project Factory P1 may mutate only the explicit generated-project target path
and, for confirmed GitHub publish, the generated project's separate GitHub
repository.

Allowed local mutations are limited to:

- creating the explicit target directory;
- writing generated-project files such as `aso.lock`, `.gitignore`, and
  generated-project `README.md`;
- creating ignored local working roots when needed;
- copying safe vendored `agent-system/` content in `vendored` mode;
- initializing a Git repository inside the generated project only for an
  explicitly confirmed GitHub publish flow.

Project Factory P1 must not:

- mutate the ASO package repository as part of generated-project creation;
- copy or reuse ASO engine `.git` metadata;
- stage, commit, tag, push, or publish the ASO package repository;
- track owner-input, runtime, archive, local upgrade, cache, log, virtual
  environment, or secret-like files in a generated project;
- perform network or GitHub actions in dry-run mode;
- perform network or GitHub actions without `--confirm-publish`.

When a target already exists, P1 must refuse unsafe overwrite. Any force or
replace behavior requires a separately documented safety contract and must not
weaken the publication boundary.

## Local Vendored Mode

Local vendored mode uses the P0 generated-project behavior and publication
boundary. It may include safe `agent-system/` package content, but vendoring
must exclude repository metadata, local owner input, runtime state, archives,
caches, logs, virtual environments, local upgrade packages, and secret-like
paths.

## Local Reference Mode

Local reference mode writes clean generated-project metadata without vendored
`agent-system/` content.

Minimum generated files are:

```text
.gitignore
README.md
aso.lock
```

Local ignored roots may exist on disk for owner input and runtime use:

```text
project-input/
project-runtime/
project-archive/
```

They must be ignored and must not be tracked.

The detailed reference engine contract is defined in:

```text
agent-system/12_project_factory/REFERENCE_ENGINE_MODE_CONTRACT.md
```

## GitHub Publish Mode

GitHub publish mode is a publish workflow for clean generated projects using
the selected `vendored` or `reference` engine mode. A real publish requires
explicit confirmation and must pass the GitHub publish preflight before any
network action.

Reference mode must not track or publish `agent-system/`. Vendored mode may
publish only safe generated-project `agent-system/` content that passes the
generated-project clean boundary.

No real GitHub action may occur without:

```text
--github
--confirm-publish
valid target path
valid repo owner/name
visibility selection
GitHub CLI availability
gh auth status pass
git executable availability
verify-clean pass
safe generated-project Git scope
secret scan pass for generated tracked files
```

Dry-run is the default GitHub planning mode unless an explicit publish
confirmation flag is present. Dry-run must not require `gh`, GitHub
credentials, network access, or a real remote repository.

The detailed GitHub publish contract is defined in:

```text
agent-system/12_project_factory/GITHUB_PUBLISH_CONTRACT.md
```

## Generated Project Publication Boundary

Generated projects must not publish:

```text
project-input/**
project-runtime/**
project-archive/**
.venv/**
.tmp/**
tmp/**
secrets/**
private/**
local upgrade packages
ASO engine .git metadata
secret-like files
credential files
tokens
cookies
caches
logs
```

Reference-mode generated repositories must not track `agent-system/`.
Vendored-mode generated repositories may track only safe generated-project
`agent-system/` content that passes the publication boundary.

## Wizard Contract

`aso wizard` guides non-engineer users through Project Factory inputs:

```text
project name
project slug
profile
target folder
engine mode: reference or vendored
local-only or GitHub publish
GitHub owner/repo/visibility when selected
dry-run vs confirmed publish
```

The wizard must support deterministic non-interactive tests through an answers
file or equivalent flags. Wizard dry-run mode must produce a plan without
creating a GitHub repository or requiring GitHub credentials.

## Version And Schema Policy

Project Factory P1 uses:

```text
package version: 3.3.0
runtime schema: 3.0.0
```

Implementation tasks must stop and request a governance decision if they
discover that runtime-state semantics need to change. Such a change is outside
this P1 contract and must not be handled by silently bumping runtime schema.
