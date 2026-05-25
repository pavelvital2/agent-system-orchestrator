# OWNER_ANSWER_INTEGRATION

Use this template after the owner answers a question card and the design
documents need to be updated.

The record captures how the answer changes the design. It does not by itself
replace audit or accepted source-of-truth update requirements.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | superseded
QUESTION_ID:
GAP_ID:
QUESTION_REFS:
GAP_REFS:
OWNER_DECISION_REF:
ANSWER_RECEIVED_DATE:
ANSWER_SUMMARY:
SELECTED_OPTION:
OWNER_FREE_TEXT:

DESIGN_UPDATE_SUMMARY:
AFFECTED_DOCUMENTS:
  - DOCUMENT_REF:
    SECTION:
    CHANGE_SUMMARY:
    OLD_STATUS:
    NEW_STATUS:

REQUIREMENTS_UPDATED:
CAPABILITIES_UPDATED:
SCENARIOS_UPDATED:
BUSINESS_RULES_UPDATED:
INTERFACE_BEHAVIOR_UPDATED:
REPORTS_EXPORTS_UPDATED:
NOTIFICATIONS_UPDATED:
APPROVALS_UPDATED:
ASSUMPTIONS_RETIRED:
DEFERRED_GAPS_UPDATED:

REMAINING_OPEN_POINTS:
  - GAP_ID:
    QUESTION_ID:
    STATUS:
    WHY_STILL_OPEN:

AUDIT_REFS:
NEXT_STAGE_IMPACT:
```

## Field rules

- `ANSWER_SUMMARY` must use the owner's wording or a plain-language summary.
- `DESIGN_UPDATE_SUMMARY` must explain what changed in product behavior,
  workflow, roles, scope, acceptance, or content.
- Any remaining ambiguity must stay linked to a GAP or question card.
- Updated documents must be audited before the answer is treated as accepted
  design source-of-truth.
