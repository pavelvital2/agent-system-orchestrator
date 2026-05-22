# PROJECT_DESIGN_DOCUMENT_TEMPLATES

## Purpose

These templates support the project design documentation pass.

They are filled by `PROJECT_DESIGNER` or `requirements_analyst` profile
agents after reading owner-provided project input. ASO orchestration must not
semantically read TZ content, infer project requirements from TZ, or generate
owner questions from TZ by itself.

The templates are documentation records, not generated application templates
and not domain packs.

## Required document set

Use these records together for a complete design pass:

- `PROJECT_TYPE_DECISION_TEMPLATE.md`
- `PROJECT_TEMPLATE_SELECTION_TEMPLATE.md`
- `PROJECT_DESIGN_BRIEF_TEMPLATE.md`
- `FUNCTIONAL_REQUIREMENTS_TEMPLATE.md`
- `USER_ROLES_AND_SCENARIOS_TEMPLATE.md`
- `ADMIN_INTERFACE_REQUIREMENTS_TEMPLATE.md`
- `VISUALIZATION_REQUIREMENTS_TEMPLATE.md`
- `CAPABILITY_MATRIX_DRAFT_TEMPLATE.md`
- `DESIGN_ASSUMPTIONS_REGISTER_TEMPLATE.md`
- `DEFERRED_GAPS_REGISTER_TEMPLATE.md`
- `OWNER_ANSWER_INTEGRATION_TEMPLATE.md`

## Owner-facing content rule

Content intended for the owner must use plain product language:

- functionality;
- workflow;
- user roles;
- business rules;
- interface behavior;
- visualization;
- reports and exports;
- notifications;
- approvals;
- operations;
- content and text;
- priority and scope;
- acceptance.

Owner-facing content must not ask the owner to select implementation
technologies or engineering mechanisms.

## Linkage fields

Every document should preserve traceability with these fields when applicable:

```text
SOURCE_REF:
GAP_REFS:
QUESTION_REFS:
OWNER_DECISION_REFS:
AUDIT_REFS:
STATUS: draft | ready_for_audit | accepted | needs_owner_answer | deferred | superseded
```

Use `NONE` when a field does not apply.

## Validation Evidence

Workspace-visible correction evidence for `TASK_ASO_DG4_030_DESIGN_DOCUMENT_TEMPLATES`:

- Human readability checked: each template uses headings and plain field names intended for review as documentation records.
- Non-technical owner language checked: owner-facing fields ask about product behavior, workflows, roles, scope, reports, approvals, content, and acceptance instead of implementation mechanisms.
- Linkage fields checked: templates include traceability fields such as `SOURCE_REF`, `GAP_REFS`, `QUESTION_REFS`, `OWNER_DECISION_REFS`, `AUDIT_REFS`, and `STATUS` where applicable; use `NONE` when a field does not apply.
- Template boundary checked: this set contains documentation records only, not generated application templates, generated code templates, or domain packs.
- ASO boundary checked: ASO orchestration must not semantically read TZ content, infer project requirements from TZ, or generate owner questions from TZ by itself; profile agents fill these records after reading owner-provided project input.
- Whitespace correction checked: added template files must end with a single newline and must not contain an extra blank line at EOF.
