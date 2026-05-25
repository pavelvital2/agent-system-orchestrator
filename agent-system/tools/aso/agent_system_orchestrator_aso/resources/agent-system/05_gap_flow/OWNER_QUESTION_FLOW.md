# OWNER_QUESTION_FLOW

## Purpose

This document defines the corrected P4 owner question flow semantics.

Owner questions are authored by a profile agent, audited independently, and
routed by ASO one card at a time. ASO validates and routes existing question
cards; it must not semantically read TZ, infer product intent, generate owner
questions from TZ, choose owner answers, or treat owner input as accepted design
without the required governed update.

## Artifact Boundary

The owner question flow uses these artifacts:

- gap record: the missing decision or information that requires owner input;
- owner question card: one non-technical, owner-facing question linked to one
  gap;
- owner question queue: deterministic routing metadata for audited cards;
- owner answer or decision record: the owner's explicit answer linked back to
  the question and gap;
- owner answer integration record: the governed design update, when the answer
  changes accepted requirements, design, scope, acceptance, behavior, content,
  or launch posture.

ASO may read these artifacts only to validate shape, links, status, audit
evidence, and deterministic routing order. ASO must not derive question content
from TZ or owner context.

## Question Authorship Rules

Owner question cards must be authored by a profile agent acting in an assigned
requirements analyst or project designer capacity.

Each card must:

- ask one clear non-technical product, workflow, business, interface, content,
  priority, acceptance, or operational question;
- link to exactly one `GAP_ID`;
- include bounded owner-facing options;
- include one recommended option and a plain-language recommendation reason;
- state `BLOCKING_STAGE` and `CAN_CONTINUE_UNTIL`;
- state owner impact in plain language;
- carry audit evidence before it becomes presentable.

The author may recommend a product option, but the owner must explicitly answer.
The auditor must verify that the question is non-technical, useful to the
owner, linked to the gap, and not shifting engineering responsibility to the
owner.

Forbidden owner questions include framework, database, queue, ORM, deployment,
transport, API style, worker, scheduler, hosting, or other implementation
mechanism choices. Acronyms such as RBAC, REST, ORM, webhook, polling, and API
must be translated into owner-facing product behavior before audit can pass.

## Status Model

Owner question cards use these flow statuses:

| Status | Meaning | Allowed next statuses |
|---|---|---|
| `draft` | The profile agent is still authoring the question. It is not eligible for audit or owner presentation. | `audit_pending`, `superseded`, `blocked` |
| `audit_pending` | The card is complete enough for independent audit, but audit has not passed. | `ready_for_owner`, `draft`, `superseded`, `blocked` |
| `ready_for_owner` | Independent audit passed and the card is eligible for one-at-a-time routing. | `presented`, `superseded`, `blocked` |
| `presented` | ASO has selected this one audited card as the current owner question. | `answered`, `superseded`, `blocked` |
| `answered` | The owner explicitly answered the presented card and a linked answer or decision record exists. | `integrated`, `superseded`, `blocked` |
| `integrated` | The answer has been reflected in accepted source-of-truth, or no design update was required and that fact is recorded. | `superseded` |
| `superseded` | The card is no longer active because another governed artifact replaced it. | none |
| `blocked` | The card cannot advance because required link, audit, queue, or status evidence is missing or invalid. | `draft`, `audit_pending`, `superseded` |

Schema fields may use legacy labels in existing artifacts until DG4_060 updates
validators. The semantic equivalents are:

| Flow status | Legacy schema label, if encountered |
|---|---|
| `audit_pending` | `ready_for_audit` |
| `presented` | `presented_to_owner` |
| `integrated` | `closed` only when accepted source-of-truth evidence is present |
| `blocked` | `audit_failed` or invalid/missing evidence that prevents progress |

New documentation and templates should use the P4 flow statuses above.

## Queue Model

The queue is a deterministic routing view over existing question cards. It is
not an authoring mechanism.

A queue entry must include:

```text
QUEUE_ID:
QUESTION_ID:
GAP_ID:
STATUS:
AUDIT_STATUS:
AUDIT_REF:
BLOCKING_STAGE:
CAN_CONTINUE_UNTIL:
QUEUE_POSITION:
SELECTION_ELIGIBLE:
PRESENTATION_STATE:
ANSWER_RECORD_ID:
SUPERSEDES:
SUPERSEDED_BY:
UPDATED_AT:
```

`PRESENTATION_STATE` values are:

```text
queued | current | presented | answered | integrated | skipped | blocked
```

Queue ordering must be stable and deterministic:

1. lower `CAN_CONTINUE_UNTIL` lifecycle stage first;
2. lower `BLOCKING_STAGE` lifecycle stage first;
3. lower numeric `QUEUE_POSITION` first;
4. lexical `QUESTION_ID` as a final tie breaker.

If lifecycle stage order is unknown, the queue must fail closed and mark the
affected entry `blocked` until the profile agent or auditor corrects the
artifact.

## Next-Question Selection Rules

ASO may select the next owner question only from existing audited cards.

An entry is eligible when all conditions are true:

- `STATUS: ready_for_owner`;
- audit status is pass;
- `AUDIT_REF` points to independent audit pass evidence;
- question card and queue entry link to the same `QUESTION_ID` and `GAP_ID`;
- linked gap still requires owner input;
- no answer record already exists for the question;
- the card is not superseded;
- no other queue entry is currently selected as `current` or `presented`.

Selection must produce exactly one next question. If zero entries are eligible,
ASO returns no question and records why the flow is waiting or complete. If more
than one entry ties after deterministic ordering, ASO must fail closed and mark
the queue blocked until the duplicate ordering is corrected.

ASO must not present a card with `draft`, `audit_pending`, `answered`,
`integrated`, `superseded`, or `blocked` status. ASO must not present a card
whose audit evidence is missing, failed, pending, self-authored, or unrelated to
the question card.

When a card is selected, ASO may mark that existing card `presented` only as a
confirmed governance write. A read-only helper may instead emit the selected
card without changing any file.

## Owner Decision Recording Rules

Owner answers require explicit confirmation. ASO must not infer an answer from
silence, partial chat context, recommendation text, or a default option.

An owner answer record must:

- link to exactly one `QUESTION_ID`;
- link to the same `GAP_ID` as the question card;
- reference the source question card;
- record the selected option or `FREE_TEXT`;
- include a plain-language answer summary;
- identify who answered and the explicit answer timestamp;
- state whether a design update is required;
- preserve `ACCEPTED_SOURCE_OF_TRUTH_UPDATE: PENDING` until the governed update
  is accepted, unless no update is required and that is audited or recorded as
  `NONE`;
- reference audit records when integration is accepted.

The owner answer changes the question status from `presented` to `answered`.
It does not close the linked gap by itself unless the answer record is already
the accepted source-of-truth for that bounded decision and the gap closure
evidence points to it.

If the answer affects requirements, design, scope, acceptance criteria,
workflow, business rules, interface behavior, reports, notifications,
approvals, or launch posture, a profile agent must create an owner answer
integration record and update the accepted design artifacts. Those updates
require audit before the question can become `integrated` and before the linked
gap can close.

## Linkage Rules

The following links must be consistent:

- gap `GAP_ID` -> question card `GAP_ID`;
- question card `QUESTION_ID` -> queue entry `QUESTION_ID`;
- queue entry `GAP_ID` -> question card `GAP_ID`;
- answer record `QUESTION_ID` and `GAP_ID` -> question card identifiers;
- integration record `QUESTION_ID`, `GAP_ID`, and `OWNER_DECISION_REF` -> answer
  record and question card;
- gap `OWNER_DECISION_REF` -> accepted answer or decision record;
- gap `ACCEPTED_SOURCE_OF_TRUTH_UPDATE` and `CLOSURE_EVIDENCE` -> accepted
  integration, audit, or source-of-truth artifact.

Mismatched links must block presentation, decision recording, integration, or
gap closure depending on where the mismatch is found.

## Optional Helper Command Semantics

DG4_060 may implement helper commands for routing and recording only. These
commands must remain governance-safe.

Read-only next question:

```bash
aso design questions next --root ROOT --json-out /tmp/next-question.json
```

Allowed behavior:

- validate existing gap, queue, question, and audit evidence;
- select exactly one eligible `ready_for_owner` card;
- emit the selected card and routing reason;
- exit with no selected question when none is eligible;
- fail closed when multiple current/presented cards or ambiguous ordering exist.

Forbidden behavior:

- reading TZ for meaning;
- generating or rewriting question wording;
- selecting an owner answer;
- writing presentation status without explicit confirmation.

Confirmed presentation write:

```bash
aso design questions present --root ROOT --question-id Q-001 --confirm-write
```

Allowed behavior:

- verify that `Q-001` is exactly the selected next question;
- change its status from `ready_for_owner` to `presented`;
- mark the queue entry `current` or `presented`;
- record only the routing receipt allowed by the active runtime/output policy.

Record owner decision:

```bash
aso design decision record --root ROOT --question-id Q-001 --answer A --dry-run
aso design decision record --root ROOT --question-id Q-001 --answer A --confirm-write
```

Allowed behavior:

- validate that `Q-001` is already `presented`;
- validate that answer `A` is an existing option, or explicitly record
  `FREE_TEXT`;
- create or update the bounded owner answer record only after
  `--confirm-write`;
- move the question to `answered`;
- leave the linked gap open or answered until accepted source-of-truth evidence
  exists.

Forbidden behavior:

- recording against a non-presented question;
- recording an answer for a mismatched `GAP_ID`;
- accepting a default recommendation without explicit owner confirmation;
- treating the answer as integrated design without the governed update and
  audit required by the gap closure rules.

## Validation Requirements

Validators and gates added by DG4_060 must fail closed when:

- any presentable card lacks audit pass evidence;
- a `draft` or `audit_pending` card is selected for owner presentation;
- more than one queue entry is `current` or `presented`;
- deterministic ordering yields more than one selected next question;
- question, gap, queue, answer, or integration identifiers disagree;
- an owner answer is recorded without explicit confirmation;
- a question is marked `integrated` without accepted source-of-truth evidence
  or a recorded no-update-needed decision.

These validations check process shape and evidence. They must not judge the
semantic correctness of a product recommendation by code alone.
