# PACKAGE_VERSIONING

## Purpose

This document defines minimal package versioning policy for the universal orchestration package. It is not a release manifest and does not list every artifact.

## Version fields

Recommended fields:

```text
PACKAGE_VERSION:
GOVERNANCE_RULESET_VERSION:
RUNTIME_SCHEMA_VERSION:
```

Runtime state should reference the active governance/schema version so a long-running orchestrator does not mix package semantics.

## Version semantics

```text
PATCH  = wording, formatting, or non-semantic clarification
MINOR  = compatible hardening; new validation or fields that do not change accepted state meaning
MAJOR  = changes to mandatory transitions, role authority, filesystem authority, terminal semantics, required runtime files, or status meanings
```

## Package update rules

1. Universal package changes occur only through owner-authorized bounded package update task.
2. Normal project agents cannot change `agent-system/`.
3. Package update activates governance freeze for normal project dispatch.
4. Runtime schema, templates, runtime loop, and governance docs must be compatible before freeze exits.
5. Package change must be recorded in `GOVERNANCE_CHANGELOG.md`.
6. Existing project runtime state that lacks newly mandatory fields enters correction/wait flow, not silent inference.

## Compatibility rule

A package version is valid only when:

```text
RUNTIME_STATE_SCHEMA.md
PROJECT_STATE_TEMPLATE.md
CURRENT_GATE_TEMPLATE.md
NEXT_ACTION_TEMPLATE.md
GAP_REGISTER_TEMPLATE.md
AGENT_RESULTS_LOG_TEMPLATE.md
ORCHESTRATOR_RUNTIME_LOOP.md
```

are mutually compatible for the active version.
