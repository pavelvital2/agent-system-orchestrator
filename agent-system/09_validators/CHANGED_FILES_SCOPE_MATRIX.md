# CHANGED_FILES_SCOPE_MATRIX

## Purpose

This document defines checkpoint-time file scope validation by role and
workspace type.

It is used by `GIT_CHECKPOINT_VALIDATION_RULES.md` before staging any changed
file. Task packet `ALLOWED_FILE_CHANGES` and `FORBIDDEN_FILE_CHANGES` remain
the narrowest authority; this matrix cannot expand a task packet.

## Required inputs

```text
TASK_ID
TARGET_ROLE
TASK_KIND
WORKSPACE_TYPE
ACTIVE_DOC_ROOT
ALLOWED_FILE_CHANGES
FORBIDDEN_FILE_CHANGES
CHANGED_FILES
AUDIT_STATUS
CHECKPOINT_ELIGIBILITY_STATUS
```

## Required status values

Changed-file scope evidence must use:

```text
CHANGED_FILES_SCOPE_STATUS: not_checked | passed | failed | blocked
```

`not_checked` is valid only before scope validation is required. Once audit or
checkpoint validation is required, `not_checked`, `failed`, or `blocked`
forbids auditor pass, staging, commit, and push.

## Global rules

- Every changed file must be allowed by the active task packet.
- New files intended for checkpoint count as changed files even before they are
  staged.
- No changed file may match task packet `FORBIDDEN_FILE_CHANGES`.
- `project-runtime/` may be changed only by orchestrator-owned runtime updates.
- `project-input/` may not be changed by ordinary profile-agent work.
- `project-archive/` may not be used as active source-of-truth.
- `agent-system/` may be changed only by owner-authorized package governance
  tasks whose task packet explicitly lists each changed path.
- Secret or sensitive artifacts are always forbidden unless the task is a
  bounded secret-handling correction that records placeholders only.

## Workspace type matrix

| WORKSPACE_TYPE | Allowed checkpoint surface | Push policy |
|---|---|---|
| `package_repo` | Owner-authorized package governance changes under `agent-system/` and package metadata explicitly listed in the task packet. Project-specific `project-docs/`, `project-runtime/`, and `project-input/` changes are forbidden unless they are orchestrator-owned runtime evidence and not staged by a profile agent. | Requires accepted repository lock and `PUSH_ALLOWED: true`. |
| `project_workspace` | Active project docs under `ACTIVE_DOC_ROOT`, governed task packets, and orchestrator-owned runtime records. `agent-system/` changes require a separate package governance task. | Requires accepted repository lock and `PUSH_ALLOWED: true`. |
| `implementation_repo` | Product/source files, tests, configuration, and docs explicitly listed by the implementation task packet. Runtime and package instruction paths are forbidden unless the repository is intentionally structured to contain them and the task packet names them. | Requires accepted repository lock and `PUSH_ALLOWED: true`. |
| `test_fixture` | Disposable fixture files explicitly listed by a testing or smoke task. Package, project, and implementation checkpoint authority cannot be inferred from a fixture. | Push is forbidden; `PUSH_ALLOWED` must remain false. |

## Role matrix

| TARGET_ROLE | Normally allowed changed files | Normally forbidden changed files |
|---|---|---|
| `requirements_analyst` | Bounded requirements artifacts under `ACTIVE_DOC_ROOT` listed by task packet. | `agent-system/`, `project-runtime/`, `project-input/`, implementation code, archive docs. |
| `solution_architect` | Architecture, stage, task packet, and project design docs under `ACTIVE_DOC_ROOT` listed by task packet. | `agent-system/`, `project-runtime/`, implementation code, source input rewrites. |
| `designer` | Deprecated alias for `solution_architect`; accepted for legacy packets with a warning. | Same as `solution_architect`. |
| `developer` | Implementation files explicitly listed by task packet. For owner-authorized package governance correction/update tasks, explicitly listed `agent-system/` files may be changed. | `project-runtime/`, `project-input/`, `project-archive/`, unrelated project docs, unlisted package files. |
| `auditor` | No file changes by default. | All changes unless a separate correction task explicitly grants bounded write authority. |
| `tester` | Temporary test artifacts only when the task packet explicitly allows them. | Source code, project docs, task packets, runtime state, package instructions. |
| `technical_writer` | User-facing docs and run/usage docs under `ACTIVE_DOC_ROOT` listed by task packet. | Code, runtime state, task packets, source architecture docs outside task scope. |
| `devops_setup_engineer` | Setup, configuration templates, run-readiness, and operational handoff artifacts explicitly listed by task packet. | Secrets, credentials, runtime state, project input, package instructions, production deployment artifacts outside task scope. |
| `release_manager` | Launch/readiness/handover/final acceptance artifacts explicitly listed by task packet. | Code, runtime state, package instructions, requirements/design/testing evidence outside task scope. |

## Invalid scope conditions

Any of the following must set `CHANGED_FILES_SCOPE_STATUS: failed` and block
checkpoint:

- changed file absent from `ALLOWED_FILE_CHANGES`;
- changed file matches `FORBIDDEN_FILE_CHANGES`;
- changed file conflicts with the role matrix;
- changed file conflicts with `WORKSPACE_TYPE`;
- ordinary profile-agent work changed `project-runtime/`;
- ordinary project work changed `agent-system/`;
- changed file is a secret or sensitive artifact under `SECRET_SCAN_RULES.md`;
- changed task packet is dispatchable but schema-invalid.

Legacy receipts may still display `FILE_SCOPE_CHECK_STATUS`, but current audit
and checkpoint evidence must use `CHANGED_FILES_SCOPE_STATUS`.

## Evidence rules

File scope evidence may list paths and rule identifiers. It must not include
secret values or file contents from sensitive artifacts.

If checkpoint preflight finds a changed-file scope blocker after auditor
`STATUS: pass`, and the auditor was required to validate changed-file scope,
the orchestrator must record `AUDIT_FALSE_PASS_DETECTED` with
`FAILURE_TYPE: audit_miss` and route correction without staging, commit, or
push.
