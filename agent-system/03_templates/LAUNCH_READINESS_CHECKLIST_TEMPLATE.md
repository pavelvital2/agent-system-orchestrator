# LAUNCH_READINESS_CHECKLIST_TEMPLATE

Use this template to verify launch readiness before any release, exposure, owner acceptance, or final handover step.

```text
TASK_ID:
TASK_TITLE:
TARGET_ROLE: release_manager
LIFECYCLE_STAGE: launch

PURPOSE:
<what launch readiness this checklist verifies>

REQUIRED_DOCS:
- <path>

READ_INPUTS:
- <accepted implementation evidence>
- <audit evidence>
- <testing evidence>
- <setup evidence>
- <run evidence>
- <documentation evidence>
- <owner decisions> | NONE

LAUNCH_READINESS_CHECKLIST:
- required gates passed:
- accepted artifacts identified:
- owner-facing instructions:
- known limitations:
- open risks and deferred items:
- rollback or recovery notes:
- final audit or final review requirement:
- deployment authorization, if any:

SCOPE_OUT:
- do not deploy unless a dedicated governed task explicitly authorizes deployment;
- do not override missing audit, testing, setup, run, or owner-decision evidence;
- do not make product or acceptance decisions for the owner.

ACCEPTANCE_CRITERIA:
- required implementation, audit, testing, setup, run, and documentation evidence exists;
- owner-facing instructions are complete enough for use or acceptance;
- known limitations and open risks are documented or explicitly marked `NONE`;
- rollback or recovery notes exist when applicable;
- final audit or final review routing is explicit.

EVIDENCE_REQUIRED:
- evidence map from launch criteria to accepted artifacts;
- blocker/risk list or `NONE`;
- owner-facing instruction readiness statement;
- rollback/recovery readiness statement;
- final audit routing recommendation.

AUDIT_REQUIRED: yes
NEXT_RECOMMENDED_ACTION:
- create launch audit, handover task, or orchestrator-controlled launch step according to task packet.
```
