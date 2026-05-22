# OWNER_DECISION

Use this template when a governed owner decision is required to answer a GAP, resolve a blocker, approve a scope change, or choose between valid bounded options.

Owner decisions are decision records.
They do not by themselves update accepted source-of-truth.
If the decision changes requirements, design, task scope, acceptance criteria, runtime behavior, launch posture, or accepted artifacts, a governed update and audit must record the accepted source-of-truth change.

```text
DECISION_ID:
STATUS: proposed | decided | superseded | accepted
SOURCE_QUESTION_ID:
QUESTION_CARD_REF:
SOURCE_GAP_ID:
SOURCE_BLOCKER_ID:
SOURCE_TASK:
QUESTION:
CONTEXT:
OPTIONS:
  A. <option>
  B. <option>
  C. <option>
RECOMMENDED_OPTION: A | B | C | NONE
RECOMMENDATION_REASON:
OWNER_DECISION:
OWNER_CONFIRMATION: explicit | pending
AFFECTED_TASKS:
AFFECTED_ARTIFACTS:
ACCEPTED_SOURCE_OF_TRUTH_UPDATE:
ACCEPTED_ARTIFACT_REF:
DECIDED_BY:
DATE:
SUPERSEDES:
SUPERSEDED_BY:
NOTES:
```

## Field rules

- `QUESTION` must be owner-facing and answerable.
- `SOURCE_QUESTION_ID` is required when the decision answers an owner question
  card.
- `QUESTION_CARD_REF` must point to the audited question card, or `NONE` for
  owner decisions that did not originate from a card.
- `SOURCE_GAP_ID` must match the linked question card gap when a question card
  exists.
- `CONTEXT` must summarize the reason the decision is needed without copying full task packets or reports.
- `OPTIONS` must list bounded choices; use `NONE` only if the owner must provide a free-form value.
- `RECOMMENDED_OPTION` may be `NONE` only when the agent cannot recommend a valid option.
- `OWNER_DECISION` remains `PENDING` until the owner answers.
- `OWNER_CONFIRMATION` must be `explicit` before the decision can be recorded as
  `decided`; recommendations, defaults, silence, or inferred chat context are
  not confirmation.
- `AFFECTED_TASKS` must list task ids or `NONE`.
- `AFFECTED_ARTIFACTS` must list bounded artifact refs or `NONE`.
- `ACCEPTED_SOURCE_OF_TRUTH_UPDATE` is required before a GAP depending on this decision can close.
- `DATE` must be an explicit date, not a relative date.
