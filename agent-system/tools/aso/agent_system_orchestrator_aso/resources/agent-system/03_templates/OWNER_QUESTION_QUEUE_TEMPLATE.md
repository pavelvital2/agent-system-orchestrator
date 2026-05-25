# OWNER_QUESTION_QUEUE

Use this template to record deterministic one-question-at-a-time routing for
audited owner question cards.

The queue routes existing cards only. It must not contain generated question
text from ASO and must not replace the question card, gap record, answer record,
or audit evidence.

```text
QUEUE_ID:
PROJECT_ID:
STATUS: draft | audit_pending | ready_for_owner | presented | answered | integrated | superseded | blocked
SELECTION_POLICY: one_question_at_a_time
CURRENT_QUESTION_ID:
CURRENT_GAP_ID:
CURRENT_PRESENTATION_REF:
BLOCKED_REASON:
UPDATED_AT:

ENTRIES:
  - QUESTION_ID:
    GAP_ID:
    STATUS: draft | audit_pending | ready_for_owner | presented | answered | integrated | superseded | blocked
    AUDIT_STATUS: pending | passed | failed | not_required
    AUDIT_REF:
    BLOCKING_STAGE:
    CAN_CONTINUE_UNTIL:
    QUEUE_POSITION:
    SELECTION_ELIGIBLE: yes | no
    PRESENTATION_STATE: queued | current | presented | answered | integrated | skipped | blocked
    ANSWER_RECORD_ID:
    SUPERSEDES:
    SUPERSEDED_BY:
    UPDATED_AT:
```

## Field Rules

- `STATUS` summarizes the queue, not the owner's answer.
- `SELECTION_POLICY` must be `one_question_at_a_time`.
- `CURRENT_QUESTION_ID` is `NONE` unless exactly one entry is selected for
  presentation.
- `CURRENT_GAP_ID` must match the selected question card and gap record.
- `CURRENT_PRESENTATION_REF` points to a routing receipt or `NONE`.
- `BLOCKED_REASON` is required when `STATUS: blocked`.
- `AUDIT_STATUS: passed` and a non-empty `AUDIT_REF` are required before an
  entry may use `STATUS: ready_for_owner` or `PRESENTATION_STATE: current`.
- `SELECTION_ELIGIBLE: yes` is valid only for `STATUS: ready_for_owner`.
- At most one entry may have `PRESENTATION_STATE: current` or
  `PRESENTATION_STATE: presented`.
- `ANSWER_RECORD_ID` is `NONE` until the owner explicitly answers the presented
  card.
- `SUPERSEDES` and `SUPERSEDED_BY` are `NONE` unless a governed replacement
  question exists.

## Routing Check

Before selecting the next question, validate:

```text
ONE_CURRENT_OR_PRESENTED: pass | fail
ALL_READY_HAVE_AUDIT_PASS: pass | fail
ALL_IDS_LINKED: pass | fail
DETERMINISTIC_ORDER_UNAMBIGUOUS: pass | fail
NO_SUPERSEDED_ENTRY_SELECTED: pass | fail
NO_ANSWERED_ENTRY_SELECTED: pass | fail
```

Any `fail` blocks owner presentation until a profile agent or auditor corrects
the artifact.
