# CAPABILITY_MATRIX_DRAFT

Use this template to map requested capabilities to users, priority, scope, and
open decisions.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | needs_owner_answer | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:

CAPABILITIES:
  - CAPABILITY_ID:
    CAPABILITY_NAME:
    OWNER_FACING_DESCRIPTION:
    USERS_OR_ROLES:
    WORKFLOW_AREA:
    PRIORITY: must | should | could | later
    FIRST_VERSION_STATUS: included | deferred | excluded | needs_owner_answer
    ACCEPTANCE_CHECK:
    DEPENDS_ON:
    GAP_REFS:
    QUESTION_REFS:
    AUDIT_REFS:

SUMMARY:
  INCLUDED_COUNT:
  DEFERRED_COUNT:
  EXCLUDED_COUNT:
  NEEDS_OWNER_ANSWER_COUNT:
```

## Field rules

- Each capability must be understandable as a product function or owner-visible
  outcome.
- `DEPENDS_ON` may reference other capability ids, owner decisions, or accepted
  design records.
- Any `needs_owner_answer` row must link to a GAP and question card.
