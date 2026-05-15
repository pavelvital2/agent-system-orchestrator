# PACKAGE_VERSIONING

## Purpose

This document defines minimal package versioning policy for the universal orchestration package. It is not a release manifest and does not list every artifact.

## Runtime version fields

Mandatory runtime version fields:

```text
PACKAGE_VERSION:
GOVERNANCE_RULESET_VERSION:
RUNTIME_SCHEMA_VERSION:
```

`PROJECT_STATE.md` must contain these fields and reference the active values unless a governed migration task explicitly changes them.

## Active version constants

```text
CURRENT_PACKAGE_VERSION: 1.2.0
CURRENT_GOVERNANCE_RULESET_VERSION: 1.2.0
CURRENT_RUNTIME_SCHEMA_VERSION: 1.1.0
```

These constants define the active package/governance/schema tuple for runtime validation. They are policy constants, not a release manifest.

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
4. Runtime schema, templates, runtime loop, and governance docs in the compatibility set must be compatible before freeze exits.
5. Package change must be recorded in `GOVERNANCE_CHANGELOG.md`.
6. Existing project runtime state that lacks newly mandatory fields enters correction/wait flow, not silent inference.

## Compatibility rule

A package version is valid only when the compatibility set is mutually compatible for the active package version, governance ruleset version, and runtime schema version.

The compatibility set includes at minimum:

```text
RUNTIME_STATE_SCHEMA.md
PROJECT_STATE_TEMPLATE.md
CURRENT_GATE_TEMPLATE.md
NEXT_ACTION_TEMPLATE.md
GAP_REGISTER_TEMPLATE.md
AGENT_RESULTS_LOG_TEMPLATE.md
ORCHESTRATOR_RUNTIME_LOOP.md
ALLOWED_ORCHESTRATOR_ACTIONS.md
FILESYSTEM_GOVERNANCE.md
GOVERNANCE_AUTHORITY.md
STATE_TRANSITION_RULES.md
VIOLATION_RECOVERY.md
ACCEPTED_STATE_LOCKING.md
```
