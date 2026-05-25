# DESIGN_GAP_AUDIT_CORRECTION_RULES

## Purpose

This document defines audit and correction rules for `PROJECT_DESIGNER`
outputs in corrected P4 design/gap governance.

It is a documentation-first validator rule set. It specifies what auditors and
manual validation must check before ASO can present owner questions, integrate
owner answers, or pass a design/gap gate. It does not add runtime daemon
behavior, live agent dispatch, checkpoint execution, product generation, or
semantic TZ reading by ASO.

## Source Documents

```text
agent-system/01_roles/PROJECT_DESIGNER.md
agent-system/02_runtime/PROJECT_DESIGN_GAP_GOVERNANCE_P4_CONTRACT.md
agent-system/03_templates/PROJECT_DESIGN_AUDIT_TEMPLATE.md
agent-system/03_templates/OWNER_QUESTION_QUEUE_TEMPLATE.md
agent-system/05_gap_flow/OWNER_QUESTION_FLOW.md
agent-system/09_validators/schemas/gap_register.schema.json
agent-system/09_validators/schemas/owner_question_card.schema.json
agent-system/09_validators/schemas/owner_answer_record.schema.json
```

## Required Audit Surface

Auditors must treat the following `PROJECT_DESIGNER` outputs as audit-required
before acceptance or owner presentation:

- project type decision records;
- template selection records;
- project design briefs and related requirements/design documents;
- design assumptions and deferred gap registers;
- gap registers;
- owner question cards;
- owner question queues;
- owner decision or answer records;
- owner answer integration records.

ASO may validate shape, links, statuses, routing order, and audit evidence. ASO
must not judge the semantic correctness of a product recommendation by code
alone and must not infer question text from TZ.

## Owner Question Audit Checklist

Each owner question card must pass these checks before `ready_for_owner` or
owner presentation is allowed:

```text
ONE_QUESTION_PER_CARD
LINKED_GAP_EXISTS
GAP_REQUIRES_OWNER_INPUT
OWNER_FACING_LANGUAGE
TECHNICAL_IMPLEMENTATION_LANGUAGE_ABSENT
QUESTION_IS_SPECIFIC_AND_ANSWERABLE
OPTIONS_ARE_BOUNDED_AND_OWNER_FACING
RECOMMENDED_OPTION_PRESENT
RECOMMENDED_OPTION_MATCHES_OPTIONS
RECOMMENDATION_REASON_PRESENT
BLOCKING_STAGE_PRESENT
CAN_CONTINUE_UNTIL_PRESENT
BLOCKING_CLASSIFICATION_REASONABLE
OVER_BLOCKING_ABSENT
OWNER_IMPACT_PRESENT
ONE_QUESTION_AT_A_TIME_ROUTING
INDEPENDENT_AUDIT_PASS_EVIDENCE_PRESENT
```

Hard fail examples:

- asking the owner to choose a framework, database, API style, queue,
  scheduler, worker, deployment, hosting, ORM, webhook, polling, or RBAC
  mechanism;
- using vague wording such as "What do you want here?" without a linked gap,
  context, options, owner impact, and recommendation;
- omitting `recommended_option` or `recommendation_reason`;
- marking a non-blocking preference as `blocking_now` without a stage-specific
  rationale;
- marking the card `ready_for_owner` or `presented` without independent audit
  pass evidence;
- presenting more than one owner question at the same time.

## Correction Flow

When audit or validation finds a defective owner question card, the card must
not be presented to the owner. The auditor returns `STATUS: fail` or
`STATUS: blocked` with a finding that identifies the reason code and artifact
ref.

Reason codes:

```text
technical_question
vague_question
missing_recommendation
missing_recommendation_reason
missing_or_invalid_blocking_stage
missing_or_invalid_can_continue_until
over_blocking
missing_gap_link
missing_or_failed_audit_evidence
one_question_routing_violation
```

Correction sequence:

1. The orchestrator creates a bounded correction task for a fresh profile agent
   acting in the `PROJECT_DESIGNER` responsibility profile.
2. The correction task includes the failed audit, original question card, linked
   gap, relevant design docs, and this rule document as required inputs.
3. The project designer revises or replaces the card using owner-facing product
   language and preserves the original card as superseded when replacement is
   needed.
4. Technical questions are translated into product, workflow, UX, business,
   content, acceptance, or operational decisions. The owner is never asked to
   pick engineering mechanisms.
5. Vague questions are rewritten to name the decision, why it matters, bounded
   options, recommendation, reason, owner impact, blocking stage, and
   continuation stage.
6. Missing recommendations or reasons are added by the project designer. ASO
   must not generate them.
7. Over-blocking cards are corrected by changing the linked gap blocking type
   to `deferred_until_stage`, `non_blocking_assumption`, or `optional` when the
   project can safely continue, or by recording the rationale for
   `blocking_now`.
8. The corrected artifacts return to independent audit. Owner presentation
   remains blocked until the new audit passes.

Auditors must not correct the card themselves, choose owner answers, or turn a
failed question into a presentable card by waiver.

## Evidence Requirements

Audit or correction evidence must include:

- task packet or correction task ref;
- audited result ref;
- artifact refs for design docs, gap registers, question cards, answer records,
  and integration records checked;
- validator command output or manual checklist results;
- explicit `STATUS` for the owner question checklist;
- reason codes for every failed question card;
- superseded and replacement artifact refs when a card is replaced;
- independent audit result ref for every card marked `ready_for_owner`;
- confirmation that no owner question was presented before audit pass;
- confirmation that no ASO code semantically read TZ or generated owner
  questions.

## Validation Mapping

Existing design governance validators should map these audit concerns to rule
ids where applicable:

```text
DG4_QUESTION_002: options incomplete
DG4_QUESTION_004: recommended option missing
DG4_QUESTION_005: recommendation does not match options
DG4_QUESTION_006: recommendation reason missing
DG4_QUESTION_007: blocking stage or continuation stage missing
DG4_QUESTION_008: technical implementation language present
DG4_AUDIT_001: question ready or presented without audit pass evidence
DG4_ROUTING_001: routing mode is not one_question_at_a_time
DG4_ROUTING_002: multiple owner questions active
DG4_ROUTING_003: next question requested while another is presented
DG4_LINK_001: owner-input gap has no question card
DG4_LINK_003: question links to unknown gap
DG4_GATE_002: unanswered blocking gap blocks stage crossing
```

When no executable validator exists for a check, the auditor must apply the
manual checklist in `PROJECT_DESIGN_AUDIT_TEMPLATE.md`. Missing executable
coverage is not a reason to skip mandatory audit.
