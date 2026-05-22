# PROJECT_TYPE_DECISION

Use this template to record the plain-language project type selected by the
project designer after reviewing owner-provided input.

This record must describe the project as the owner would recognize it. It must
not choose implementation technologies.

```text
PROJECT_ID:
DOCUMENT_ID:
STATUS: draft | ready_for_audit | accepted | needs_owner_answer | superseded
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:

PROJECT_TYPE:
SHORT_DESCRIPTION:
PRIMARY_AUDIENCE:
PRIMARY_OUTCOME:

WHY_THIS_TYPE_FITS:
OWNER_VALUE:
MAIN_WORKFLOW_SUMMARY:

TYPE_OPTIONS_CONSIDERED:
  A. <plain-language option>
  B. <plain-language option>
  C. <plain-language option or NONE>
SELECTED_OPTION:
SELECTION_REASON:

OPEN_POINTS_FOR_OWNER:
  - GAP_ID:
    QUESTION_ID:
    PLAIN_LANGUAGE_QUESTION:
```

## Field rules

- `PROJECT_TYPE` must be a product or service category, such as customer
  request portal, booking workflow, internal approval tool, catalog, dashboard,
  content site, learning experience, or reporting workspace.
- `WHY_THIS_TYPE_FITS` must cite owner needs, user workflow, or business
  outcome.
- `TYPE_OPTIONS_CONSIDERED` must be owner-facing alternatives, not technology
  stacks.
- Missing owner choices must link to GAPs and question cards instead of being
  hidden as assumptions.
