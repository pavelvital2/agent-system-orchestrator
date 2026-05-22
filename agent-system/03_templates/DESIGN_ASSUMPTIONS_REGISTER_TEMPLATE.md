# DESIGN_ASSUMPTIONS_REGISTER

Use this template to record assumptions that help the designer continue
without pretending the owner has already decided.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:

ASSUMPTIONS:
  - ASSUMPTION_ID:
    STATEMENT:
    WHY_THIS_IS_REASONABLE:
    OWNER_VISIBLE_IMPACT:
    USED_IN_DOCUMENTS:
    REVIEW_TRIGGER:
    IF_WRONG_THEN:
    PROMOTE_TO_GAP: yes | no | already_linked
    GAP_REFS:
    QUESTION_REFS:
    AUDIT_REFS:
```

## Field rules

- Assumptions must be stated in plain product language.
- An assumption must not replace a required owner decision.
- If an assumption can change workflow, roles, business rules, acceptance, or
  first-version scope, it must be promoted to a GAP or linked to an existing
  GAP.
