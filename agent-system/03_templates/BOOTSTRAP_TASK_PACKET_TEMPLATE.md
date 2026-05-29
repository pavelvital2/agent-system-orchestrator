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

The `<TARGET_ROLE>` placeholder must be populated by the selected bootstrap
route. It must not be omitted or rendered as an empty role segment.

Examples:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md
project-runtime/bootstrap/TASK_BOOTSTRAP_SOLUTION_ARCHITECT_001.md
```

`TASK_PACKET: NONE` is never valid for the first profile-agent dispatch.
A bootstrap handoff file may not be used as a task packet substitute.

---

# TASK PACKET

## TASK_ID

```text
TASK_BOOTSTRAP_<TARGET_ROLE>_001
```

## TASK_STATUS

```text
active
```

## TASK_KIND

```text
bootstrap
```

## TASK_COMPLEXITY

```text
xhigh
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

## TASK_TYPE

```text
requirements_analyst | solution_architect
```

## TARGET_ROLE

```text
requirements_analyst | solution_architect
```

Rules:

- `TARGET_ROLE` must match `TASK_TYPE`.
- Use `requirements_analyst` when source input is incomplete, ambiguous, or not
  clearly design-ready.
- Use `solution_architect` only when source input is sufficiently structured
  for design routing under `agent-system/07_lifecycle/BOOTSTRAP_STAGE.md`.
- `designer` is a deprecated compatibility alias for old bootstrap packets.

## AGENT_LIFECYCLE_POLICY

```text
one_agent_one_task_delete_after_result
```

## REASONING_LEVEL

```text
VALUE: xhigh
OVERRIDE_REASON: NONE
```

## REASONING_LEVEL_REQUIRED

```text
xhigh
```

## DEPENDENCIES

```text
- bootstrap validation passed
```

## DEPENDENCY_STATUS

```text
ready
```

## REQUESTED_BY_ROLE

```text
NONE
```

## REQUESTED_BY_TASK

```text
NONE
```

## RESEARCH_QUESTION_ID

```text
NONE
```

## RESEARCH_PURPOSE

```text
NONE
```

## RESEARCH_QUESTIONS

```text
NONE
```

## ALLOWED_SOURCES

```text
NONE
```

## FORBIDDEN_SOURCES

```text
NONE
```

## EXPECTED_EVIDENCE

```text
NONE
```

## EXPECTED_OUTPUT

```text
NONE
```

## RETURN_TO_REQUESTER_AFTER_AUDIT_PASS

```text
no
```

## RETURN_TO_ROLE_AFTER_AUDIT_PASS

```text
none
```

## RETURN_TASK_AFTER_AUDIT_PASS

```text
NONE
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
- agent-system/01_roles/REQUIREMENTS_ANALYST.md when TARGET_ROLE is requirements_analyst
- agent-system/01_roles/SOLUTION_ARCHITECT.md when TARGET_ROLE is solution_architect
- agent-system/01_roles/DESIGNER.md only for deprecated TARGET_ROLE designer compatibility packets
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
```

Role document mapping:

```text
TARGET_ROLE: requirements_analyst
Role doc: agent-system/01_roles/REQUIREMENTS_ANALYST.md

TARGET_ROLE: solution_architect
Role doc: agent-system/01_roles/SOLUTION_ARCHITECT.md

TARGET_ROLE: designer
Role doc: agent-system/01_roles/DESIGNER.md (deprecated alias wrapper)
```

Do not derive role document paths by lower-case `TARGET_ROLE` interpolation.

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
- BOOTSTRAP_CONTINUATION_STATUS: downstream_task_packet | gap | blocked | wait_for_owner
- BOOTSTRAP_CONTINUATION_REF: path or route reference
```

## RESULT_CONTRACT

```text
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

Rules:

- the profile-agent RESULT must include the assigned `TASK_ID`, `ROLE`, and
  `AGENT_INSTANCE_ID`;
- `REUSE_ALLOWED` must be `false`;
- `AGENT_TERMINATION_REQUIRED` must be `true`;
- profile-agent execution evidence must be tied to a dispatch receipt before
  the RESULT can pass audit.

## ALLOWED_FILE_CHANGES

For `requirements_analyst`:

```text
- project-docs/00_requirements/*
```

For `solution_architect`:

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
- bootstrap output cannot be accepted unless it contains a valid downstream
  dispatchable TASK_PACKET, explicit GAP, explicit BLOCKED route, or explicit
  wait_for_owner route;
- when research or design continuation is needed, the solution architect must
  create a full schema-valid downstream research/design continuation task
  packet or return GAP/BLOCKED/wait_for_owner;
- no forbidden file changes are made;
- no profile agent commits or pushes.
```

## EVIDENCE_REQUIREMENTS

```text
- list read documents;
- list changed files or NONE;
- provide scope and forbidden-change verification.
- cite dispatch receipt project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json;
- cite canonical candidate artifact package manifest at
  project-runtime/artifacts/candidates/<TASK_ID>/manifest.json when an artifact
  package is created.
```

## EXPECTED_ARTIFACT_PACKAGE

```text
project-runtime/artifacts/candidates/TASK_BOOTSTRAP_<TARGET_ROLE>_001/manifest.json
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
project-runtime/results/worker/RESULT_TASK_BOOTSTRAP_<TARGET_ROLE>_001_ATTEMPT_001.md
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
solution_architect(pass) -> auditor
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
- a handoff file is not a task packet substitute;
- post-bootstrap accepted checkpoint is blocked by
  `bootstrap_continuation_missing` when `BOOTSTRAP_CONTINUATION_STATUS` is
  absent, invalid, or not backed by a valid continuation route;
- post-audit Git checkpoint remains orchestrator-owned and audit-pass only.

## RESULT_FORMAT

```text
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

## TERMINAL_CONDITIONS

```text
NONE
```

## NOTES

```text
This packet is for bootstrap intake only and must not introduce project-specific
implementation terms into universal package governance.

Created by orchestrator during bootstrap. This does not make orchestrator a
profile execution role.
```
