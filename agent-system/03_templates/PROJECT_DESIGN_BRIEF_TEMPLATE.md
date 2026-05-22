# PROJECT_DESIGN_BRIEF

Use this template to summarize the product design in language suitable for the
owner, auditors, and downstream profile agents.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | needs_owner_answer | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:

PROJECT_NAME:
ONE_PARAGRAPH_SUMMARY:
PRIMARY_USERS:
OWNER_GOALS:
USER_GOALS:
BUSINESS_RULES_SUMMARY:
MAIN_WORKFLOW:
KEY_SCREENS_OR_TOUCHPOINTS:
REPORTS_EXPORTS:
NOTIFICATIONS:
APPROVALS:
OPERATIONS_NEEDS:
CONTENT_OR_TEXT_NEEDS:

IN_SCOPE_FOR_FIRST_VERSION:
OUT_OF_SCOPE_FOR_FIRST_VERSION:
ACCEPTANCE_SUMMARY:

OPEN_DECISIONS:
  - GAP_ID:
    QUESTION_ID:
    DECISION_NEEDED:
    WHY_IT_MATTERS:
```

## Field rules

- `ONE_PARAGRAPH_SUMMARY` must avoid implementation detail and explain what the
  product lets users accomplish.
- `MAIN_WORKFLOW` must be understandable without engineering knowledge.
- `IN_SCOPE_FOR_FIRST_VERSION` and `OUT_OF_SCOPE_FOR_FIRST_VERSION` must be
  specific enough to prevent later scope ambiguity.
- Any unresolved decision affecting scope, workflow, business rules, interface
  behavior, or acceptance must link to a GAP or owner question.
