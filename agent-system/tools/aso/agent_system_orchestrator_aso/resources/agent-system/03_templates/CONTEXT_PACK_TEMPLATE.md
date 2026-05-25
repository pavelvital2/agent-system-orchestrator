# CONTEXT_PACK_TEMPLATE

## Purpose

This template describes the bounded JSON context pack passed between agent tasks.
The JSON form is canonical in `agent-system/03_templates/CONTEXT_PACK_TEMPLATE.json`.

## Required Fields

- `task_id`: receiving bounded task identifier.
- `required_docs`: bounded source documents or fixture files with `path`,
  `sections`, and `why_needed`.
- `forbidden_docs`: repository-relative path prefixes that must not appear in
  required context.
- `source_of_truth`: authoritative paths included in `required_docs`.
- `accepted_artifact_packages`: optional accepted package paths under
  `project-runtime/artifacts/accepted/` that the pack consumes.
- `rendered_views`: optional rendered view paths under
  `project-runtime/rendered/` that the pack consumes.
- `context_mode`: `routine`, `debug`, `explain`, or `violation_recovery`.
- `reference_docs`: optional debug/explain/recovery references, each with an
  authorization reason or validator-required marker.
- `context_budget`: explicit limits for document count, sections per document,
  and generated JSON characters.

## Context Budget

Context packs must use bounded, audit-visible limits:

- `max_docs`
- `max_sections_per_doc`
- `max_chars_total`

## Builder Hints

Dry-run proposal builders may add metadata such as `required_docs_reason`,
`section_hints`, per-document `sha256`, and `estimated_chars`. Validators must
preserve the safety boundary: no runtime mutation, dispatch, commits, pushes,
checkpoint execution, or owner approval.

## Runtime Context Boundary

Context packs must not consume raw, candidate, rejected, lifecycle, dispatch,
checkpoint, or mutable runtime-state artifacts. Runtime context is allowed only
after acceptance or deterministic rendering:

- accepted packages under `project-runtime/artifacts/accepted/`;
- rendered views under `project-runtime/rendered/`.

Candidate packages under `project-runtime/artifacts/candidates/` are agent
output proposals. They become context-pack consumable only after a governed
acceptance step materializes an immutable accepted package.

## Routine Orchestrator Boundary

Routine orchestrator context packs must follow
`ORCHESTRATOR_RUNTIME_CONTRACT.json` `handoff_context_builder_contract`: runtime
contract sections, current state refs, current task packet, current
event/result/artifact refs, and target-role-specific docs only. They must not
include the full governance corpus, all role docs, all templates, full
changelog, release notes, or all validator docs. Reference docs require
`debug`, `explain`, or `violation_recovery` mode with an explicit reason, or a
validator-required marker.
