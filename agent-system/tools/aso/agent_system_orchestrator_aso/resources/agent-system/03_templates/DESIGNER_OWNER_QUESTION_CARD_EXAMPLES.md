# DESIGNER_OWNER_QUESTION_CARD_EXAMPLES

## Purpose

These examples show owner question cards authored by a project designer and
then audited before ASO routes them. ASO may validate and route these existing
cards one at a time; it must not generate the question text or infer product
intent from raw TZ content.

## Functional Question Card

```text
question_id: Q-001
linked_gap_id: GAP-001
status: ready_for_owner
question: Should each employee see only their own requests, or should managers see all requests for their team?
why_it_matters: This determines the first-version permission behavior and which screens need filtered views.
options:
  A: Employees see their own requests; managers see team requests.
  B: Everyone sees all requests.
  C: Only administrators can see all requests.
recommended_option: A
recommendation_reason: It supports ordinary employee privacy while still giving managers the operational view needed for approvals.
blocking_stage: IMPLEMENTATION
can_continue_until: DESIGN
owner_impact: The answer affects role behavior, list filters, and approval views.
audit_status: passed
audit_ref: project-runtime/results/audit/AUDIT_RESULT_Q-001.md
```

This is valid because it asks about user-visible behavior, not implementation
technology.

## Visualization Question Card

```text
question_id: Q-002
linked_gap_id: GAP-002
status: ready_for_owner
question: What should the dashboard show first when a manager opens it?
why_it_matters: The first screen should prioritize the information managers use most often.
options:
  A: Pending approvals and overdue items.
  B: Weekly totals and trend charts.
  C: A searchable list of all records.
recommended_option: A
recommendation_reason: Pending and overdue work is usually the most time-sensitive manager action.
blocking_stage: DESIGN
can_continue_until: REQUIREMENTS
owner_impact: The answer affects dashboard layout, navigation priority, and acceptance checks.
audit_status: passed
audit_ref: project-runtime/results/audit/AUDIT_RESULT_Q-002.md
```

## Forbidden Technical Rewrite

Do not ask:

```text
Should we use PostgreSQL or SQLite?
```

Ask the owner-facing product question instead:

```text
question_id: Q-003
linked_gap_id: GAP-003
status: ready_for_owner
question: Is the first version expected to be used by one person on one computer, or by multiple people at the same time?
why_it_matters: This affects launch expectations and whether shared access is required in the first version.
options:
  A: One person on one computer is enough for the first version.
  B: Multiple people must use it at the same time.
recommended_option: B
recommendation_reason: The source brief describes manager approvals, which usually requires shared access.
blocking_stage: DESIGN
can_continue_until: REQUIREMENTS
owner_impact: The answer affects first-version scope, setup expectations, and acceptance testing.
audit_status: passed
audit_ref: project-runtime/results/audit/AUDIT_RESULT_Q-003.md
```

The designer may use the owner answer as product intent. The solution
architect decides the technical mechanism later from accepted design inputs.
