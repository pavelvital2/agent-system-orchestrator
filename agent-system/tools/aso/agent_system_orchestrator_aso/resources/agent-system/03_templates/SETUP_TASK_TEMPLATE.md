# SETUP_TASK_TEMPLATE

Use this template for bounded setup tasks that verify dependencies, configuration, environment variable inventory, setup scripts, and local run preparation.

```text
TASK_ID:
TASK_TITLE:
TARGET_ROLE: devops_setup_engineer
LIFECYCLE_STAGE: setup

PURPOSE:
<what setup readiness this task verifies>

REQUIRED_DOCS:
- <path>

READ_INPUTS:
- <accepted implementation/audit/setup evidence path> | NONE

SCOPE_IN:
- verify dependency prerequisites and installation commands;
- verify configuration templates or creation instructions;
- inventory required environment variable names and purposes without values;
- verify migrations, seed/setup scripts, build scripts, or initialization commands;
- verify local run instructions are present and reproducible.

SCOPE_OUT:
- do not add, print, infer, or request secret values;
- do not deploy;
- do not change product requirements or application behavior outside setup scope;
- do not bypass required audit gates.

ALLOWED_FILE_CHANGES:
- <path> | NONE

FORBIDDEN_FILE_CHANGES:
- credential files;
- local secret files;
- files outside allowed changes.

SETUP_GATE_CHECKLIST:
- dependencies:
- configuration templates:
- environment variables without secrets:
- migrations/setup scripts:
- local run instructions:
- blockers or gaps:

ACCEPTANCE_CRITERIA:
- dependencies and required tools are documented or verified;
- configuration templates or instructions are present;
- environment variables are named with purpose and required/optional status, without values;
- required migrations, setup scripts, build steps, or initialization commands are documented or verified;
- local run instructions include working directory, command sequence, and expected readiness signal.

EVIDENCE_REQUIRED:
- commands run and concise results;
- files inspected or changed;
- secret-handling statement;
- setup readiness conclusion.

AUDIT_REQUIRED: yes
NEXT_RECOMMENDED_ACTION:
- create setup audit or route according to task packet.
```
