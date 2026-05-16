# GAP_REGISTER

## Active gaps

If active gaps exist:

```text
GAP_ID:
STATUS: open | answered | closed | superseded
SOURCE_ROLE:
SOURCE_TASK:
TYPE: business | functional | technical | documentation | acceptance | runtime
BLOCKS:
QUESTION_TO_OWNER:
RECOMMENDED_OPTIONS:
RECOMMENDED_OPTION:
OWNER_DECISION_REF:
OWNER_ANSWER:
RESOLUTION_TASK:
ACCEPTED_SOURCE_OF_TRUTH_UPDATE:
ACCEPTED_ARTIFACT_REF:
CLOSURE_EVIDENCE:
CREATED_AT:
UPDATED_AT:
```

If no active gaps exist:

```text
NONE
```

## Closed gaps

If closed gaps exist:

```text
GAP_ID:
RESOLUTION:
OWNER_DECISION_REF:
ACCEPTED_SOURCE_OF_TRUTH_UPDATE:
ACCEPTED_ARTIFACT_REF:
CLOSURE_EVIDENCE:
CLOSED_BY:
CLOSED_AT:
```

If no closed gaps exist:

```text
NONE
```

## Blocking GAP rule

Only blocking issues belong in this register.

A GAP blocks the listed `BLOCKS` items until closure evidence points to an accepted source-of-truth update.
`STATUS: answered` means owner or designer input was received but closure is not yet accepted.
`STATUS: closed` is valid only when `ACCEPTED_SOURCE_OF_TRUTH_UPDATE` and `CLOSURE_EVIDENCE` are populated.

Non-blocking observations must be recorded in a findings register, not as active GAPs.
