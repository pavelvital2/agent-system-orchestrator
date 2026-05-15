# EVIDENCE_MATRIX

Use this template to trace analytical claims, decisions, acceptance criteria, and launch readiness back to bounded evidence.

The evidence matrix is not a replacement for project documentation, task packets, test reports, audit reports, or runtime state.
It is an index that links claims and decisions to their source material.

```text
MATRIX_ID:
SCOPE:
STATUS: draft | accepted | superseded
SOURCE_TASKS:
OWNER:
UPDATED_AT:
```

## Evidence rows

```text
EVIDENCE_ID:
DECISION_AREA: requirements | design | discovery | migration | data | API | infra | launch
CLAIM_OR_DECISION:
SOURCE_OF_TRUTH_REF:
EVIDENCE_REF:
EVIDENCE_TYPE: requirement | design_doc | discovery_note | migration_plan | data_sample | API_contract | infra_check | launch_check | command_output | test_result | audit_result | owner_decision | runtime_state
CONFIDENCE: high | medium | low | unknown
STATUS: proposed | accepted | rejected | superseded
AFFECTED_TASKS:
AFFECTED_ARTIFACTS:
GAP_ID:
FINDING_ID:
OWNER_DECISION_ID:
NOTES:
```

If no rows exist:

```text
NONE
```

## Rules

- Every row must use bounded references, not copied source documents.
- `DECISION_AREA` must support requirements, design, discovery, migration, data, API, infra, and launch decisions.
- `SOURCE_OF_TRUTH_REF` must point to the accepted or proposed document that the claim depends on.
- `EVIDENCE_REF` must point to the observed evidence, result, command, report, audit, owner decision, or runtime-state record.
- Low or unknown confidence that blocks dependent work must be routed as a GAP.
- Non-blocking concerns must be linked through `FINDING_ID`.
