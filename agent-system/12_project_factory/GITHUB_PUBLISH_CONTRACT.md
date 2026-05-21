# GITHUB_PUBLISH_CONTRACT

## Purpose

This contract defines the Project Factory P1 boundary for publishing a
generated project to GitHub.

GitHub publish mode is for generated-project repositories. It is not authority
to publish the ASO package repository, working upgrade packages, runtime
artifacts, owner-input files, local archives, or secrets.

## Supported Mode

Project Factory P1 GitHub publish uses:

```text
engine mode: selected vendored or reference mode
runtime schema: 3.0.0
```

GitHub publish mode creates or uses a clean generated-project target, records
the selected ASO engine mode in `aso.lock`, initializes a separate Git
repository inside the generated project, creates a GitHub repository through
the GitHub CLI, and pushes only generated-project files that satisfy this
contract.

## Dry-Run Boundary

GitHub dry-run planning must not perform network actions and must not require
GitHub CLI availability or authentication.

Dry-run may validate deterministic inputs and write a plan to stdout,
`--json-out`, `/tmp`, or an ignored generated-project output path. It must not
create a GitHub repository, push to a remote, or require real credentials.

## Real Publish Preconditions

No real GitHub action may occur unless all of these conditions are true:

```text
--github is present
--confirm-publish is present
--dry-run is absent
target path is valid
repo owner/name is valid
one visibility is selected
git executable is available
gh executable is available
gh auth status passes
generated project verify-clean passes
generated project Git scope is separate from the ASO engine repository
generated tracked files contain no secrets
```

If any preflight check fails, the command must stop before creating a GitHub
repository or pushing to a remote.

## Visibility Contract

Exactly one visibility must be selected for a confirmed publish:

```text
private
public
internal
```

The selected visibility determines the GitHub CLI repository creation flag:

```text
--private
--public
--internal
```

## Publication Boundary

Generated-project GitHub publication must not track or push:

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
credential files
secret-like files
tokens
cookies
caches
logs
```

Reference-mode GitHub repositories must not track vendored `agent-system/`
content. Vendored-mode GitHub repositories may track only safe generated-project
`agent-system/` content that passes the generated-project clean boundary. The
generated project records the selected ASO engine mode through `aso.lock` and
user documentation, while the publishable repository remains bounded to clean
generated-project files.

The root `.git/` directory of the generated project is allowed only as the
generated project's own repository metadata. It must not be copied from the ASO
engine checkout.

## Allowed Published Files

A generated project may track:

```text
.gitignore
README.md
aso.lock
agent-system/** only for vendored mode after clean-boundary verification
.github/workflows/**
.devcontainer/**
```

Optional workflow and devcontainer files are allowed only when they do not
require secrets, live service credentials, dispatch authority, checkpoint
execution, commit authority outside the generated project, or push authority
outside the generated project.

## GitHub CLI Contract

Project Factory P1 may depend on GitHub CLI for confirmed publish mode.
Dry-run mode must not require `gh`.

After the generated project has a local Git commit and all preflights pass,
the recommended command shape is:

```bash
gh repo create OWNER/REPO --private --source TARGET --remote origin --push
```

Use `--public` or `--internal` instead of `--private` according to the selected
visibility.

The implementation must construct subprocess calls without shell interpolation
of untrusted owner, repo, target, branch, or visibility values.

## Redaction

Project Factory P1 must not print:

```text
tokens
credential helper output
full environment
secret-like file contents
authorization headers
cookie values
```

Human-readable output and JSON output may include deterministic status,
selected visibility, owner/repo, target path, branch, command phase, and
non-secret failure summaries.

## Verification Evidence

Confirmed publish preflight evidence should include:

```text
target path status
engine mode
runtime schema
visibility
git availability
gh availability
gh auth status result
verify-clean result
forbidden tracked path count
secret scan status
publish action status
```

Evidence must not include secret values or full credential output.

## No Runtime Schema Change

This contract does not change runtime-state semantics. Project Factory P1
GitHub publish uses runtime schema `3.0.0`.
