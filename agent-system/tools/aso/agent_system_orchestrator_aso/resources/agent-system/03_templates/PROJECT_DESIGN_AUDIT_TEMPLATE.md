# PROJECT_DESIGN_AUDIT

Use this template for independent audit of `PROJECT_DESIGNER` outputs created
by a requirements analyst acting in the project-designer responsibility profile.

This audit template applies to project type decisions, template selections,
project design briefs, functional requirements drafts, user roles and
scenarios, interface and visualization requirements, capability matrices, gap
registers, owner question cards, assumptions, deferred gaps, owner decisions,
and owner answer integration records.

```text
AUDIT_ID:
TASK_ID:
AUDITED_RESULT_REF:
AUDITED_AGENT_ROLE:
PROJECT_ID:
STATUS: pass | fail | blocked | gap
AUDITOR:
AUDIT_DATE:

REQUIRED_INPUTS:
  TASK_PACKET_REF:
  PROJECT_DESIGNER_RESULT_REF:
  PROJECT_TYPE_DECISION_REF:
  TEMPLATE_SELECTION_REF:
  DESIGN_DOC_REFS:
  GAP_REGISTER_REFS:
  OWNER_QUESTION_CARD_REFS:
  OWNER_DECISION_REFS:
  OWNER_ANSWER_INTEGRATION_REFS:
  VALIDATOR_EVIDENCE_REFS:

MANDATORY_AUDIT_GATE:
  INDEPENDENT_AUDITOR: yes | no
  SELF_AUDIT_ABSENT: yes | no
  OWNER_PRESENTATION_BLOCKED_UNTIL_PASS: yes | no
  DESIGN_ACCEPTANCE_BLOCKED_UNTIL_PASS: yes | no

PROJECT_DESIGNER_OUTPUT_CHECKS:
  ASO_BOUNDARY_STATUS: pass | fail | blocked
  SOURCE_TRACEABILITY_STATUS: pass | fail | blocked
  DESIGN_DOC_STATUS: pass | fail | blocked | not_applicable
  GAP_REGISTER_STATUS: pass | fail | blocked | not_applicable
  OWNER_QUESTION_STATUS: pass | fail | blocked | not_applicable
  OWNER_DECISION_LINK_STATUS: pass | fail | blocked | not_applicable
  ANSWER_INTEGRATION_STATUS: pass | fail | blocked | not_applicable
  EVIDENCE_STATUS: pass | fail | blocked

OWNER_QUESTION_AUDIT_CHECKLIST:
  ONE_QUESTION_PER_CARD: pass | fail | blocked | not_applicable
  LINKED_GAP_EXISTS: pass | fail | blocked | not_applicable
  OWNER_FACING_LANGUAGE: pass | fail | blocked | not_applicable
  TECHNICAL_IMPLEMENTATION_LANGUAGE_ABSENT: pass | fail | blocked | not_applicable
  QUESTION_IS_SPECIFIC_AND_ANSWERABLE: pass | fail | blocked | not_applicable
  OPTIONS_ARE_BOUNDED_AND_OWNER_FACING: pass | fail | blocked | not_applicable
  RECOMMENDED_OPTION_PRESENT: pass | fail | blocked | not_applicable
  RECOMMENDATION_REASON_PRESENT: pass | fail | blocked | not_applicable
  BLOCKING_STAGE_PRESENT: pass | fail | blocked | not_applicable
  CAN_CONTINUE_UNTIL_PRESENT: pass | fail | blocked | not_applicable
  BLOCKING_CLASSIFICATION_REASONABLE: pass | fail | blocked | not_applicable
  OVER_BLOCKING_ABSENT: pass | fail | blocked | not_applicable
  OWNER_IMPACT_PRESENT: pass | fail | blocked | not_applicable
  AUDIT_PASS_EVIDENCE_PRESENT_BEFORE_OWNER_ROUTING: pass | fail | blocked | not_applicable

CORRECTION_REQUIRED:
  REQUIRED: yes | no
  REASON_CODES:
    - technical_question
    - vague_question
    - missing_recommendation
    - missing_recommendation_reason
    - missing_or_invalid_blocking_stage
    - over_blocking
    - missing_gap_link
    - missing_audit_evidence
    - other
  CORRECTION_TASK_REF:
  SUPERSEDED_ARTIFACT_REFS:
  REAUDIT_REQUIRED: yes | no

EVIDENCE:
  VALIDATION_COMMANDS:
    - <command and result>
  MANUAL_CHECKS:
    - <check and result>
  SAMPLE_ARTIFACTS_CHECKED:
    - <path/ref>
  FINDINGS:
    - <finding or NONE>

NEXT_RECOMMENDED_ACTION:
```

## Pass Rules

Auditor `STATUS: pass` is forbidden unless all applicable required checks are
`pass` or explicitly `not_applicable` with a reason. `OWNER_QUESTION_STATUS`
cannot pass when any presentable owner question lacks independent audit pass
evidence.

`OWNER_PRESENTATION_BLOCKED_UNTIL_PASS` must be `yes` for every owner question
card. A card with `draft`, `audit_pending`, `blocked`, `failed`, missing audit
evidence, or self-audit evidence must not be presented to the owner.

## Fail Rules

Auditor `STATUS: fail` is required when an accessible question card is
technical, vague, missing a recommendation, missing a recommendation reason,
missing blocking fields, over-blocking without rationale, linked to the wrong
gap, or marked presentable without independent audit evidence.

Auditor `STATUS: blocked` is required when required artifacts or validator
evidence are unavailable and a manual equivalent check cannot be completed.

## Evidence Requirements

Audit evidence must identify the exact artifact refs checked, the validator or
manual checklist used, and the result for each required check. Evidence must be
sufficient for a later auditor to confirm that no unaudited owner question could
be routed and that no design artifact was accepted before mandatory audit.
