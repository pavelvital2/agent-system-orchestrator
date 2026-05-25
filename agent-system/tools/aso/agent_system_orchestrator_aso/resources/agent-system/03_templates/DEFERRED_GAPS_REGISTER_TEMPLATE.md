# DEFERRED_GAPS_REGISTER

Use this template to track known gaps that do not block the current design
stage but must be answered before a later stage.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
AUDIT_REFS:

DEFERRED_GAPS:
  - GAP_ID:
    GAP_SUMMARY:
    OWNER_VISIBLE_IMPACT:
    WHY_CAN_CONTINUE_NOW:
    BLOCKING_STAGE:
    CAN_CONTINUE_UNTIL:
    QUESTION_ID:
    QUESTION_STATUS:
    CURRENT_OWNER_SAFE_ASSUMPTION:
    AFFECTED_DOCUMENTS:
    AUDIT_REFS:
```

## Field rules

- `WHY_CAN_CONTINUE_NOW` must explain why current work remains valid without
  the answer.
- `BLOCKING_STAGE` and `CAN_CONTINUE_UNTIL` must be explicit stage names, not
  relative timing.
- Deferred gaps must not hide first-version scope, acceptance, approval, or
  workflow decisions that are blocking now.
