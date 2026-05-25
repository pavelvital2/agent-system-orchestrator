# ADMIN_INTERFACE_REQUIREMENTS

Use this template to describe owner-visible administration and interface
behavior.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | needs_owner_answer | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:

ADMIN_NEEDS:
  - NEED_ID:
    ADMIN_ROLE:
    TASK:
    INFORMATION_SHOWN:
    ACTIONS_ALLOWED:
    CONFIRMATION_OR_APPROVAL_NEEDED:
    HISTORY_NEEDED:
    ACCEPTANCE_CHECK:
    GAP_REFS:
    QUESTION_REFS:

INTERFACE_BEHAVIOR:
  - BEHAVIOR_ID:
    SCREEN_OR_TOUCHPOINT:
    USER_ACTION:
    SYSTEM_RESPONSE:
    EMPTY_STATE:
    ERROR_OR_PROBLEM_STATE:
    SUCCESS_STATE:
    CONTENT_OR_LABEL_NOTES:
    GAP_REFS:
    QUESTION_REFS:

OPERATIONS_NOTES:
  DAILY_OR_WEEKLY_TASKS:
  PEOPLE_RESPONSIBLE:
  MANUAL_STEPS_TO_KEEP:
  MANUAL_STEPS_TO_REPLACE:
```

## Field rules

- `ADMIN_NEEDS` must focus on what administrators can view, change, approve,
  export, or monitor.
- `INTERFACE_BEHAVIOR` must describe what users see and what happens after
  their actions.
- Do not ask the owner to choose internal implementation mechanisms.
