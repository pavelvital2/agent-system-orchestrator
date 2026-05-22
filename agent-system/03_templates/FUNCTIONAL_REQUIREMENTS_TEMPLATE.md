# FUNCTIONAL_REQUIREMENTS

Use this template to list what the project must do from the user and owner
point of view.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | needs_owner_answer | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:

REQUIREMENTS:
  - REQUIREMENT_ID:
    TITLE:
    USER_OR_ROLE:
    NEED:
    EXPECTED_BEHAVIOR:
    BUSINESS_RULES:
    ACCEPTANCE_CHECK:
    PRIORITY: must | should | could | later
    SCOPE_STATUS: in_scope | deferred | out_of_scope | needs_owner_answer
    SOURCE_REF:
    GAP_REFS:
    QUESTION_REFS:

REQUIREMENTS_NOT_INCLUDED:
  - ITEM:
    REASON:
    OWNER_DECISION_REF:
```

## Field rules

- `NEED` states the user or business need, not a technical solution.
- `EXPECTED_BEHAVIOR` describes observable product behavior.
- `ACCEPTANCE_CHECK` must be plain enough that the owner can confirm whether it
  is correct.
- Requirements with `needs_owner_answer` must link to a GAP or question card.
