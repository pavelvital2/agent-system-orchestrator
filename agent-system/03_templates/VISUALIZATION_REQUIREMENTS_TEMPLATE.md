# VISUALIZATION_REQUIREMENTS

Use this template when the project includes dashboards, charts, tables, status
views, summaries, reports, or exports.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | needs_owner_answer | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:

VISUALIZATION_ITEMS:
  - VISUAL_ID:
    TITLE:
    AUDIENCE:
    QUESTION_IT_ANSWERS:
    INFORMATION_SHOWN:
    GROUPING_OR_FILTERS:
    REFRESH_EXPECTATION:
    ACTIONS_FROM_VIEW:
    EXPORT_NEEDED: yes | no | needs_owner_answer
    ACCEPTANCE_CHECK:
    GAP_REFS:
    QUESTION_REFS:

REPORTS_AND_EXPORTS:
  - REPORT_ID:
    REPORT_NAME:
    AUDIENCE:
    PURPOSE:
    INFORMATION_INCLUDED:
    FORMAT_EXPECTATION:
    FREQUENCY:
    OWNER_APPROVAL_NEEDED: yes | no | needs_owner_answer
    GAP_REFS:
    QUESTION_REFS:
```

## Field rules

- `QUESTION_IT_ANSWERS` must state the business or operational question the
  visualization helps answer.
- `INFORMATION_SHOWN` must use owner-recognizable terms.
- `REFRESH_EXPECTATION` must be phrased as an owner-visible expectation, such
  as immediate, daily, weekly, monthly, or on request.
