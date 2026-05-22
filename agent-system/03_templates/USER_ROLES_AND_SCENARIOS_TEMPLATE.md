# USER_ROLES_AND_SCENARIOS

Use this template to describe who uses the product and what each role needs to
do.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | needs_owner_answer | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:

USER_ROLES:
  - ROLE_ID:
    ROLE_NAME:
    ROLE_DESCRIPTION:
    MAIN_GOALS:
    CAN_DO:
    CANNOT_DO_OR_LIMITS:
    NEEDS_DIFFERENT_PERMISSIONS: yes | no | needs_owner_answer
    GAP_REFS:
    QUESTION_REFS:

SCENARIOS:
  - SCENARIO_ID:
    ROLE_ID:
    SCENARIO_NAME:
    STARTING_POINT:
    STEPS:
    SUCCESS_RESULT:
    ALTERNATE_RESULT:
    ACCEPTANCE_CHECK:
    GAP_REFS:
    QUESTION_REFS:
```

## Field rules

- Role names must be plain labels such as customer, manager, administrator,
  reviewer, author, viewer, or operator.
- Permission questions must be phrased as what people can see, change, approve,
  or manage.
- Scenarios must describe real user actions and outcomes.
