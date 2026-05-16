# BOOTSTRAP_TASK_PACKET_TEMPLATE

## Purpose

This template defines the canonical first task packet produced by the
orchestrator during bootstrap before the first profile-agent dispatch.

Bootstrap task packets are orchestrator-created runtime inputs. Profile agents
may read them as their assigned task packet, but profile agents must not edit
them.

Canonical path convention:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

Examples:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md
project-runtime/bootstrap/TASK_BOOTSTRAP_DESIGNER_001.md
```

`TASK_PACKET: NONE` is never valid for the first profile-agent dispatch.
A bootstrap handoff file may not be used as a task packet substitute unless it
is explicitly full task-packet-equivalent and satisfies this template.

---

# BOOTSTRAP TASK PACKET

## TASK_ID

```text
TASK_BOOTSTRAP_<TARGET_ROLE>_001
```

## TASK_STATUS

```text
active
```

## SUPERSEDES

```text
NONE
```

## SUPERSEDED_BY

```text
NONE
```

## CORRECTION_OF

```text
NONE
```

## SOURCE_RESULT_REF

```text
NONE
```

## ATTEMPT_NO

```text
1
```

## FAILURE_TYPE

```text
none
```

## TASK_TITLE

```text
Bootstrap intake for <requirements analysis | design>
```

## REQUESTER

```text
orchestrator
```

Rules:

- `REQUESTER` records that the orchestrator created this runtime input during
  bootstrap;
- it does not make `orchestrator` a valid profile execution role.

## TASK_TYPE

```text
requirements_analyst | designer
```

## TARGET_ROLE

```text
requirements_analyst | designer
```

Rules:

- `TARGET_ROLE` must match `TASK_TYPE`.
- Use `requirements_analyst` when source input is incomplete, ambiguous, or not
  clearly design-ready.
- Use `designer` only when source input is sufficiently structured for design
  routing under `agent-system/07_lifecycle/BOOTSTRAP_STAGE.md`.

## DEPENDENCIES

```text
- bootstrap validation passed
```

## DEPENDENCY_STATUS

```text
ready
```

## PURPOSE

```text
Give the first profile agent one bounded bootstrap intake task using the owner
source input and universal package governance.
```

## SOURCE_OF_TRUTH

```text
- project-input/TZ.md
- agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
```

## REQUIRED_DOCS

```text
- project-input/TZ.md
- agent-system/01_roles/<TARGET_ROLE_ROLE_FILE>.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
```

## INPUTS

```text
- owner-provided source input
- current runtime state
```

## READ_INPUTS

```text
- project-runtime/PROJECT_STATE.md
- project-runtime/CURRENT_GATE.md
- project-runtime/NEXT_ACTION.md
```

## SCOPE_IN

```text
- read only the REQUIRED_DOCS and READ_INPUTS listed in this packet;
- perform the first bounded intake task for the assigned role;
- return RESULT using AGENT_RESULT_TEMPLATE;
- identify gaps or blockers instead of resolving ambiguity by assumption.
```

## SCOPE_OUT

```text
- do not edit bootstrap task packets;
- do not edit project-runtime files;
- do not edit agent-system files;
- do not perform audit, Git checkpoint, deployment, or final acceptance;
- do not expand scope beyond first intake for the assigned role.
```

## EXPECTED_OUTPUTS

```text
- RESULT according to agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

## ALLOWED_FILE_CHANGES

For `requirements_analyst`:

```text
- project-docs/00_requirements/*
```

For `designer`:

```text
- project-docs/01_architecture/*
- project-docs/03_tasks/*
```

## FORBIDDEN_FILE_CHANGES

```text
- agent-system/*
- project-runtime/*
- project-archive/*
- project-input/*
- .git/*
- .env
- secrets/*
- credentials/*
```

## ACCEPTANCE_CRITERIA

```text
- RESULT uses agent-system/03_templates/AGENT_RESULT_TEMPLATE.md;
- changed files, if any, are within ALLOWED_FILE_CHANGES;
- gaps or blockers are reported instead of guessed;
- no forbidden file changes are made;
- no profile agent commits or pushes.
```

## EVIDENCE_REQUIREMENTS

```text
- list read documents;
- list changed files or NONE;
- provide scope and forbidden-change verification.
```

## SETUP_HOOKS

```text
NONE
```

## LAUNCH_HOOKS

```text
NONE
```

## RESULT_PATH

```text
project-runtime/agent-results/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

## RISK_REQUIREMENTS

```text
- incomplete owner input;
- ambiguous requirements;
- insufficient design readiness.
```

## MANDATORY_WORKFLOW

```text
requirements_analyst(pass) -> auditor
designer(pass) -> auditor
blocked -> orchestrator
gap -> orchestrator
```

## NEXT_ROLE_ON_PASS

```text
auditor
```

## NEXT_ROLE_ON_FAIL

```text
orchestrator
```

## NEXT_ROLE_ON_BLOCKED

```text
orchestrator
```

## NEXT_ROLE_ON_GAP

```text
orchestrator
```

## AUDIT_REQUIREMENTS

```text
mandatory
```

## TESTING_REQUIREMENTS

```text
none
```

## DOCUMENTATION_REQUIREMENTS

```text
optional
```

## FILESYSTEM_GOVERNANCE

```text
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
```

Rules:

- the bootstrap task packet is created under `project-runtime/bootstrap/` by
  the orchestrator;
- the bootstrap task packet is read-only for profile agents;
- profile agents may change only files listed in `ALLOWED_FILE_CHANGES`;
- profile agents must not stage, commit, or push.

## RUNTIME_GOVERNANCE

```text
agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
agent-system/04_state/RUNTIME_STATE_SCHEMA.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
```

Rules:

- first profile dispatch must reference this valid bootstrap task packet path;
- first profile dispatch must not use `TASK_PACKET: NONE`;
- a handoff file is not a task packet substitute unless explicitly full
  task-packet-equivalent;
- post-audit Git checkpoint remains orchestrator-owned and audit-pass only.

## RESULT_FORMAT

```text
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

## TERMINAL_CONDITIONS

```text
NONE
```

## NEXT_RECOMMENDED_ACTION

```text
- create matching auditor task after profile-agent STATUS: pass;
- route blocked or gap results according to orchestrator governance.
```

## NOTES

```text
This packet is for bootstrap intake only and must not introduce
project-specific implementation terms into universal package governance.
```
