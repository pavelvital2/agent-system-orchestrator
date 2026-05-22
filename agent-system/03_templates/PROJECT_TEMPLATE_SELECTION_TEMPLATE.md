# PROJECT_TEMPLATE_SELECTION

Use this template to record which documentation or planning template family
fits the project design pass.

This record does not create application templates, generated code templates, or
domain packs.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | needs_owner_answer | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:

SELECTED_TEMPLATE_FAMILY:
SELECTION_GOAL:
OWNER_FACING_REASON:

DOCUMENTS_TO_PRODUCE:
  - DOCUMENT_NAME:
    PURPOSE:
    OWNER_VISIBLE: yes | no
    REQUIRED_FOR_STAGE:

DOCUMENTS_NOT_USED:
  - DOCUMENT_NAME:
    REASON:

FIT_CHECK:
  WORKFLOW_COVERED: yes | no | partial
  USER_ROLES_COVERED: yes | no | partial
  BUSINESS_RULES_COVERED: yes | no | partial
  INTERFACE_BEHAVIOR_COVERED: yes | no | partial
  VISUALIZATION_COVERED: yes | no | partial | not_applicable
  REPORTS_EXPORTS_COVERED: yes | no | partial | not_applicable
  NOTIFICATIONS_COVERED: yes | no | partial | not_applicable

OPEN_POINTS_FOR_OWNER:
  - GAP_ID:
    QUESTION_ID:
    PLAIN_LANGUAGE_QUESTION:
```

## Field rules

- `SELECTED_TEMPLATE_FAMILY` describes the documentation path, such as simple
  workflow app, operational dashboard, content-managed site, approval process,
  or reporting tool.
- `OWNER_FACING_REASON` must explain why the selected documentation path helps
  clarify the product.
- `DOCUMENTS_NOT_USED` prevents scope expansion by stating why unrelated
  records are unnecessary.
