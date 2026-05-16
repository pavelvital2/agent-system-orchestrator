# EXPECTED_FLOW_EXAMPLE

## Purpose

This example traces a generic project from TZ intake through requirements,
design, task execution, audit, post-audit checkpoint, setup, run, launch, and
handover. It demonstrates orchestration order only; it does not deploy or
require credentials.

## Flow summary

```text
TZ
-> bootstrap routing
-> if input is incomplete or ambiguous:
   requirements task
   requirements audit
   post-audit Git checkpoint
   design task
-> if input is sufficiently structured:
   design task
-> design audit
-> post-audit Git checkpoint
-> implementation task packet
-> profile agent RESULT
-> auditor RESULT
-> post-audit Git checkpoint
-> testing task, if required
-> setup gate
-> run/smoke gate
-> launch readiness gate
-> handover gate
-> orchestrator-controlled final acceptance
```

## Documentation-level trace

| Step | Orchestrator action | Primary package references | Accepted output |
|---:|---|---|---|
| 1 | Read owner TZ and runtime seed, create a bootstrap task packet, then choose exactly one first profile route. | `00_start/ORCHESTRATOR_START.md`, `03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md`, `07_lifecycle/BOOTSTRAP_STAGE.md` | Valid bounded `NEXT_ACTION` for `requirements_analyst` or `designer` with a bootstrap `TASK_PACKET`. |
| 2 | Dispatch requirements analyst when input is incomplete, ambiguous, or not clearly design-ready. | `01_roles/REQUIREMENTS_ANALYST.md`, `07_lifecycle/REQUIREMENTS_STAGE.md` | Requirements baseline or GAP. |
| 3 | Dispatch requirements auditor when a requirements task ran. | `01_roles/AUDITOR.md`, `09_validators/RESULT_VALIDATION_RULES.md` | Audit pass before acceptance. |
| 4 | Run post-audit checkpoint after requirements audit pass. | `02_runtime/POST_AUDIT_GIT_CHECKPOINT.md`, `09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md` | Commit hash and accepted artifact record. |
| 5 | Dispatch designer directly from bootstrap only for sufficiently structured input, or after accepted requirements. | `01_roles/DESIGNER.md`, `07_lifecycle/DESIGN_STAGE.md` | Design docs and bounded task packets. |
| 6 | Dispatch design auditor, then checkpoint on pass. | `02_runtime/STATE_TRANSITION_RULES.md` | Accepted design state. |
| 7 | Dispatch one profile agent for one task packet. | `03_templates/TASK_PACKET_TEMPLATE.md`, role file for the target role | Structured `RESULT`. |
| 8 | Dispatch matching auditor. | `01_roles/AUDITOR.md`, `03_templates/AGENT_RESULT_TEMPLATE.md` | Audit pass, fail, blocked, or GAP route. |
| 9 | Checkpoint only after audit pass. | `02_runtime/ACCEPTED_STATE_LOCKING.md` | Accepted implementation artifact record. |
| 10 | Dispatch testing task if required. | `01_roles/TESTER.md`, `07_lifecycle/TESTING_STAGE.md` | Reproducible acceptance evidence. |
| 11 | Dispatch setup gate. | `03_templates/SETUP_TASK_TEMPLATE.md`, `07_lifecycle/SETUP_STAGE.md` | Dependency/configuration readiness without secret values. |
| 12 | Dispatch run/smoke gate. | `03_templates/RUN_SMOKE_CHECKLIST_TEMPLATE.md`, `07_lifecycle/RUN_STAGE.md` | Start/smoke evidence or documentation-only equivalent. |
| 13 | Dispatch launch readiness gate. | `03_templates/LAUNCH_READINESS_CHECKLIST_TEMPLATE.md`, `07_lifecycle/LAUNCH_STAGE.md` | Launch readiness statement without deployment. |
| 14 | Dispatch handover gate. | `03_templates/HANDOVER_CHECKLIST_TEMPLATE.md`, `07_lifecycle/HANDOVER_STAGE.md` | Handover index and final acceptance evidence map. |

## Bootstrap NEXT_ACTION examples

```text
INCOMPLETE_OR_AMBIGUOUS_INPUT:
  ACTION_TYPE: create_agent
  TARGET_ROLE: requirements_analyst
  TASK_ID: TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001
  TASK_PACKET: project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md
  DEPENDENCY_STATUS: ready
  BLOCKED_BY: NONE

SUFFICIENTLY_STRUCTURED_INPUT:
  ACTION_TYPE: create_agent
  TARGET_ROLE: designer
  TASK_ID: TASK_BOOTSTRAP_DESIGNER_001
  TASK_PACKET: project-runtime/bootstrap/TASK_BOOTSTRAP_DESIGNER_001.md
  DEPENDENCY_STATUS: ready
  BLOCKED_BY: NONE
```

Bootstrap `TASK_PACKET` must never be `NONE` for these first profile-agent
routes. Orchestrator-owned runtime seed, state, and log notes may support
bootstrap routing, but they are not task packet substitutes. The canonical
`project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md` path is the
only active task packet exception outside `ACTIVE_DOC_ROOT`, and only for the
first bootstrap profile-agent dispatch. Ordinary task packets outside
`ACTIVE_DOC_ROOT` remain invalid, and only one first bootstrap task packet may
be active at a time.

## Minimal task/audit/checkpoint cycle

```text
TASK_PACKET:
  TASK_ID: TASK_EXAMPLE_002_DOC
  TASK_STATUS: active
  TASK_TYPE: developer
  TARGET_ROLE: developer
  DEPENDENCY_STATUS: ready
  ALLOWED_FILE_CHANGES:
  - project-docs/example/07_reports/*
  AUDIT_REQUIREMENTS: mandatory
  TESTING_REQUIREMENTS: none
  DOCUMENTATION_REQUIREMENTS: optional
  FILESYSTEM_GOVERNANCE: agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
  RUNTIME_GOVERNANCE: agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
  RESULT_FORMAT: agent-system/03_templates/AGENT_RESULT_TEMPLATE.md

PROFILE_AGENT_RESULT:
  STATUS: pass
  CHANGED_FILES:
  - project-docs/example/07_reports/WORKFLOW_NOTE.md
  NEXT_RECOMMENDED_ACTION:
  - create matching auditor agent

AUDITOR_RESULT:
  STATUS: pass
  EVIDENCE:
  - result shape valid
  - changed files match allowed scope
  - no forbidden project-specific terms or secrets found
  NEXT_RECOMMENDED_ACTION:
  - run post-audit Git checkpoint

POST_AUDIT_GIT_CHECKPOINT:
  allowed only after auditor STATUS: pass
  records commit hash, branch, push status, accepted files, and task id
```

Profile-agent task packets must use the active documentation root, such as
`project-docs/example/*`, for allowed artifact changes. `project-runtime/*`
remains reserved for orchestrator-owned runtime seed, state, and log records.

## Setup, run, launch, and handover without deployment

For documentation-only or minimal projects, operational gates can be satisfied
with explicit documentation evidence:

```text
SETUP:
  Verify required tools are NONE or listed by name and purpose.
  Verify configuration variables are NONE or listed without values.

RUN:
  Verify the artifact can be inspected or rendered with a documented local
  command when applicable. If no command exists, record documentation-only
  evidence and the reason.

LAUNCH:
  Verify required accepted artifacts, known limitations, and owner-facing
  instructions exist. Do not deploy.

HANDOVER:
  List accepted artifacts, evidence references, maintenance notes, and final
  acceptance readiness. Do not mark the whole project completed directly.
```

## Invalid shortcuts

The following shortcuts contradict the universal flow:

```text
profile agent pass -> commit without audit
first profile create_agent -> TASK_PACKET: NONE
first profile TASK_PACKET -> plain handoff-only file
ordinary task packet outside ACTIVE_DOC_ROOT
multiple active first bootstrap task packets at the same time
audit fail -> commit accepted state
setup/run/launch/handover -> skipped when required evidence is missing
handover agent -> marks whole project completed directly
```
