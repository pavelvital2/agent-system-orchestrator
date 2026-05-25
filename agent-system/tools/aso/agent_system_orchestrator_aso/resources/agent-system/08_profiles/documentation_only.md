# Project profile: documentation_only

## When to use

Use this profile for tasks whose deliverables are documents, templates, specifications, runbooks, checklists, guides, or other non-code artifacts.

## Required gates and checks

- Verify the document purpose, audience, source-of-truth inputs, and ownership.
- Check consistency with existing terminology, lifecycle, templates, and governance.
- Confirm links, paths, references, examples, and acceptance criteria are accurate.
- Validate that documentation does not imply authority beyond core runtime and governance rules.
- Confirm no secrets, credentials, private data, or project-specific terminology leak into universal documents unless explicitly in scope.

## Typical artifacts

- specifications;
- task packets;
- checklists;
- runbooks;
- templates;
- evidence matrices;
- handover or operational notes.

## Test expectations

- Review for completeness against source requirements.
- Link, path, and heading checks where practical.
- Template shape validation when documents are consumed by agents.
- Terminology and scope checks for project-agnostic content.
- No runtime tests are required unless the documentation describes executable procedures that can be safely smoke checked.

## Setup considerations

- Document any tooling needed to render, lint, validate, or publish documents.
- Keep generated documentation outputs clearly separated from source documents when applicable.
- Avoid requiring access to private systems unless explicitly in scope.

## Launch considerations

- Confirm document version, changelog, source references, and acceptance criteria alignment when release is in scope.
- Confirm published paths or handover locations are known.
- Confirm documentation does not bypass required audit or owner-decision flows.

## Handover considerations

- Provide source paths, intended readers, update procedure, validation checks, and known open questions.
- Identify documents that must stay synchronized with runtime, templates, or lifecycle rules.
