# HANDOVER_CHECKLIST_TEMPLATE

Use this template to transfer accepted artifacts, documentation, runbooks, maintenance notes, and final acceptance evidence.

```text
TASK_ID:
TASK_TITLE:
TARGET_ROLE: release_manager | technical_writer
LIFECYCLE_STAGE: handover

PURPOSE:
<what handover readiness this checklist verifies>

REQUIRED_DOCS:
- <path>

READ_INPUTS:
- <accepted artifacts registry or equivalent>
- <requirements/design/implementation evidence>
- <audit/testing/setup/run/launch evidence>
- <documentation evidence>
- <owner decisions> | NONE

HANDOVER_CHECKLIST:
- accepted artifacts:
- documentation index:
- runbook references:
- verified setup/run/smoke commands:
- maintenance notes:
- known limitations and open risks:
- rollback/recovery/support notes:
- final acceptance evidence:

SCOPE_OUT:
- do not mark the whole project completed directly;
- do not include unverified behavior as accepted documentation;
- do not expose secrets or local-only credential material.

ACCEPTANCE_CRITERIA:
- accepted artifacts are listed with source evidence;
- documentation and runbook references are present;
- verified setup, run, smoke, rollback, and recovery commands are included where applicable;
- maintenance notes identify routine operation, update constraints, and ownership boundaries when applicable;
- limitations, open risks, deferred work, and accepted exceptions are documented or explicitly marked `NONE`.

EVIDENCE_REQUIRED:
- accepted artifact list;
- documentation/runbook index;
- verified command list;
- maintenance notes;
- final acceptance readiness statement.

AUDIT_REQUIRED: yes when required by task packet
NEXT_RECOMMENDED_ACTION:
- route to final audit or orchestrator-controlled final acceptance according to task packet.
```
