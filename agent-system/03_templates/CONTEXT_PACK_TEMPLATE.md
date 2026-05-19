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
