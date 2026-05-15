# EXPECTED_FLOW_EXAMPLE

## Purpose

This example traces a generic project from TZ intake through requirements,
design, task execution, audit, post-audit checkpoint, setup, run, launch, and
handover. It demonstrates orchestration order only; it does not deploy or
require credentials.

## Flow summary

```text
TZ
-> requirements task
-> requirements audit
-> post-audit Git checkpoint
-> design task
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
| 1 | Read owner TZ and runtime seed. | `00_start/ORCHESTRATOR_START.md`, `07_lifecycle/BOOTSTRAP_STAGE.md` | Valid bounded next action. |
| 2 | Dispatch requirements analyst. | `01_roles/REQUIREMENTS_ANALYST.md`, `07_lifecycle/REQUIREMENTS_STAGE.md` | Requirements baseline or GAP. |
| 3 | Dispatch requirements auditor. | `01_roles/AUDITOR.md`, `09_validators/RESULT_VALIDATION_RULES.md` | Audit pass before acceptance. |
| 4 | Run post-audit checkpoint. | `02_runtime/POST_AUDIT_GIT_CHECKPOINT.md`, `09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md` | Commit hash and accepted artifact record. |
| 5 | Dispatch designer. | `01_roles/DESIGNER.md`, `07_lifecycle/DESIGN_STAGE.md` | Design docs and bounded task packets. |
| 6 | Dispatch design auditor, then checkpoint on pass. | `02_runtime/STATE_TRANSITION_RULES.md` | Accepted design state. |
| 7 | Dispatch one profile agent for one task packet. | `03_templates/TASK_PACKET_TEMPLATE.md`, role file for the target role | Structured `RESULT`. |
| 8 | Dispatch matching auditor. | `01_roles/AUDITOR.md`, `03_templates/AGENT_RESULT_TEMPLATE.md` | Audit pass, fail, blocked, or GAP route. |
| 9 | Checkpoint only after audit pass. | `02_runtime/ACCEPTED_STATE_LOCKING.md` | Accepted implementation artifact record. |
| 10 | Dispatch testing task if required. | `01_roles/TESTER.md`, `07_lifecycle/TESTING_STAGE.md` | Reproducible acceptance evidence. |
| 11 | Dispatch setup gate. | `03_templates/SETUP_TASK_TEMPLATE.md`, `07_lifecycle/SETUP_STAGE.md` | Dependency/configuration readiness without secret values. |
| 12 | Dispatch run/smoke gate. | `03_templates/RUN_SMOKE_CHECKLIST_TEMPLATE.md`, `07_lifecycle/RUN_STAGE.md` | Start/smoke evidence or documentation-only equivalent. |
| 13 | Dispatch launch readiness gate. | `03_templates/LAUNCH_READINESS_CHECKLIST_TEMPLATE.md`, `07_lifecycle/LAUNCH_STAGE.md` | Launch readiness statement without deployment. |
| 14 | Dispatch handover gate. | `03_templates/HANDOVER_CHECKLIST_TEMPLATE.md`, `07_lifecycle/HANDOVER_STAGE.md` | Handover index and final acceptance evidence map. |

## Minimal task/audit/checkpoint cycle

```text
TASK_PACKET:
  TARGET_ROLE: developer
  AUDIT_REQUIRED: yes
  POST_AUDIT_GIT_CHECKPOINT_REQUIRED: yes
  ALLOWED_FILE_CHANGES:
  - project-runtime/example/docs/*

PROFILE_AGENT_RESULT:
  STATUS: pass
  CHANGED_FILES:
  - project-runtime/example/docs/WORKFLOW_NOTE.md
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
audit fail -> commit accepted state
setup/run/launch/handover -> skipped when required evidence is missing
handover agent -> marks whole project completed directly
```
