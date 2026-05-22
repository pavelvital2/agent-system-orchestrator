# PROJECT_DESIGN_GAP_GOVERNANCE_P4_CONTRACT

## Purpose

This document defines the corrected P4 governance contract for ASO package
version `3.6.0`, governance ruleset version `3.6.0`, Runtime Schema version
`3.1.0`, and design/gap governance schema version `1.0.0`.

P4 adds designer-led project design, gap governance, owner question cards,
deferred blockers, and audited owner decision flow. It does not redefine the
Runtime Schema `3.1.0` sidecar envelope and does not install product-intake
automation.

## Authority Boundary

ASO is a deterministic governance and control conveyor. ASO validates process
shape, required files, schemas, allowed transitions, gap/question artifacts,
owner-decision receipts, and audit state.

ASO may:

- validate that required design, gap, and owner-question artifacts exist;
- validate schema, format, link, and status consistency;
- gate lifecycle transitions when a blocking gap remains unresolved;
- route audited owner questions one at a time;
- render reports and preserve receipts;
- invoke one fresh profile agent per task packet;
- invoke one fresh auditor agent for mandatory independent audit.

ASO must not:

- semantically interpret TZ or owner input as product requirements;
- infer business intent from raw text as deterministic code;
- decide which product capabilities the owner needs;
- replace the project designer or requirements analyst;
- generate owner questions from TZ content by script;
- ask non-engineer owners to choose implementation technologies;
- mark a product plan accepted without audited design artifacts.

The project designer or requirements analyst reads TZ and owner context by
meaning, produces design artifacts, identifies gaps, authors owner-facing
question cards, and recommends bounded options. The auditor verifies coherence,
owner-facing language, non-technical phrasing, source linkage, and stage
blocking rules. ASO validates and gates the artifacts; it does not perform the
designer's reasoning.

## Superseded Branch

The branch `upgrade/product-intake-capability-p4-v3.6.0` is superseded and
non-authoritative. It must remain untouched in remote history and must not be
merged as the P4 line. The authoritative corrected P4 branch is
`upgrade/project-design-gap-governance-p4-v3.6.0`.

## Owner Question Policy

Owner questions must be useful for a non-engineer product owner. They must ask
about product behavior, business use, workflow, interface behavior, content,
priority, acceptance expectations, or operational constraints in plain
language.

Allowed owner question categories:

- functionality;
- user workflow;
- user roles in plain language;
- business rules;
- interface behavior;
- information visualization;
- report or export expectations;
- notifications;
- approval behavior;
- operational constraints;
- content and text choices;
- priority and scope choices;
- acceptance expectations.

Forbidden owner question categories:

- framework, library, database, queue, ORM, deployment, transport, or hosting
  mechanism selection;
- implementation acronym questions such as RBAC, REST, webhook, polling, ORM,
  worker, scheduler, or cache choices unless translated into owner-facing
  product behavior;
- questions that shift engineering design responsibility from the profile
  agents to the owner.

Each owner question card must contain:

```text
question_id
linked_gap_id
question
why_it_matters
options
recommended_option
recommendation_reason
blocking_stage
can_continue_until
owner_impact
status
```

Owner interaction is sequential. Internal gap registers may list many gaps, but
ASO must present audited owner questions one card at a time.

## Gap Blocking Policy

Every gap must state how it affects the project flow. A gap may be:

- `blocking_now`: the current stage cannot continue;
- `deferred_until_stage`: work may continue until the named stage;
- `non_blocking_assumption`: work may continue under an explicit bounded
  assumption;
- `optional`: the gap is not required for the current accepted scope.

Each gap record must contain:

```text
gap_id
description
source_reference
gap_type
user_impact
blocking_type
blocking_stage
can_continue_until
linked_question_card
status
```

ASO may allow work to continue while unanswered gaps are deferred. ASO must
block crossing the gap's blocking stage when owner input is still missing and
no accepted bounded assumption exists.

The auditor must verify that gap categorization is reasonable, deferral does
not hide an immediate blocker, assumptions are visible and bounded, and no
engineering decision is pushed to the owner.

## Runtime Schema Boundary

Runtime Schema remains `3.1.0`. P4 adds governance artifacts, design/gap
policies, owner-question policy, and later validators. It does not change the
P2/P3 runtime sidecar envelope and does not silently migrate active
`project-runtime/` state.

## Non-Goals

P4 does not add:

- ASO product-intake code that semantically reads TZ;
- autonomous product question generation by deterministic code;
- runtime daemon;
- live agent dispatch;
- checkpoint executor;
- product application generation;
- external workers or distributed queue infrastructure;
- external API calls;
- secret collection.
