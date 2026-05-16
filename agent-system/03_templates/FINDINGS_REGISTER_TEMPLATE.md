# FINDINGS_REGISTER

Use this template to track non-blocking findings that should remain visible after an agent task, audit, discovery pass, migration review, setup check, launch review, or handover review.

Findings are not GAPs.
A finding must not block dependent dispatch unless it is promoted to a blocker or GAP through governed routing.

## Active findings

If active findings exist:

```text
FINDING_ID:
STATUS: open | accepted | deferred | promoted_to_gap | resolved | superseded
SEVERITY: info | low | medium | high
SOURCE_ROLE:
SOURCE_TASK:
FINDING_TYPE: requirement | design | discovery | migration | data | API | infra | launch | documentation | testing | runtime | governance
SUMMARY:
EVIDENCE_REF:
AFFECTED_TASKS:
AFFECTED_ARTIFACTS:
PROMOTED_GAP_ID:
OWNER_DECISION_ID:
RESOLUTION_REF:
CREATED_AT:
UPDATED_AT:
```

If no active findings exist:

```text
NONE
```

## Closed findings

If closed findings exist:

```text
FINDING_ID:
FINAL_STATUS: resolved | accepted | deferred | promoted_to_gap | superseded
RESOLUTION:
RESOLUTION_REF:
CLOSED_BY:
CLOSED_AT:
```

If no closed findings exist:

```text
NONE
```

## Rules

- Findings preserve traceability for non-blocking work.
- `SEVERITY: high` is allowed only if the finding still does not block the current governed action.
- If a finding blocks a dependent task, gate, artifact, owner decision, or acceptance criterion, it must be promoted to a GAP or blocker.
- `PROMOTED_GAP_ID` must be populated when `STATUS: promoted_to_gap`.
- Findings may link to evidence matrix rows, owner decisions, task results, audit reports, test reports, runtime-state records, or accepted artifacts.
