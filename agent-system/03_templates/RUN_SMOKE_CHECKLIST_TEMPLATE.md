# RUN_SMOKE_CHECKLIST_TEMPLATE

Use this template for run and smoke verification tasks after setup readiness exists.

```text
TASK_ID:
TASK_TITLE:
TARGET_ROLE: devops_setup_engineer | tester
LIFECYCLE_STAGE: run

PURPOSE:
<what runtime readiness this checklist verifies>

REQUIRED_DOCS:
- <path>

READ_INPUTS:
- <setup readiness evidence path>
- <accepted implementation/audit evidence path>

START_COMMAND:
- working directory:
- command:
- expected startup signal:

SMOKE_COMMAND:
- working directory:
- command:
- expected pass signal:

LOG_REVIEW:
- log source or command:
- critical error patterns to check:
- expected result:

RUN_GATE_CHECKLIST:
- application start:
- smoke command/checklist:
- logs or runtime output reviewed:
- critical errors absent:
- blockers or failures:

SCOPE_OUT:
- do not change runtime behavior unless explicitly in scope;
- do not deploy;
- do not expose secrets or print secret values.

ACCEPTANCE_CRITERIA:
- application starts with the documented command or equivalent manual evidence;
- smoke command or checklist passes;
- logs or runtime output are inspected;
- no unresolved critical errors, crash loops, or required service failures remain.

EVIDENCE_REQUIRED:
- command results;
- startup readiness signal;
- smoke pass evidence;
- log review summary;
- unresolved error list or `NONE`.

AUDIT_REQUIRED: yes when required by task packet
NEXT_RECOMMENDED_ACTION:
- route to launch readiness, correction, or audit according to task packet.
```
