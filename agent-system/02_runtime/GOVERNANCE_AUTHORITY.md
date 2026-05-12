# GOVERNANCE_AUTHORITY

## Purpose

This document defines immutable governance rules, authority precedence, conflict resolution, and governance freeze semantics for deterministic orchestration.

## Immutable rules

These rules cannot be overridden by task packet, NEXT_ACTION, handoff, or agent RESULT.

1. One agent receives exactly one bounded task.
2. A completed agent context is not reused.
3. Runtime state comes from filesystem files, not conversational memory.
4. `NEXT_ACTION.md` contains the single next permitted action.
5. Orchestrator does not design, implement, audit, test, document, or answer GAPs.
6. Profile agents do not modify `project-runtime/`.
7. Ordinary project agents do not modify `agent-system/`.
8. Task packets must be inside `ACTIVE_DOC_ROOT` unless explicitly governed as system/bootstrap documents.
9. Deprecated/archive documents are not active source-of-truth.
10. Designer and developer pass require auditor review.
11. Profile agents cannot declare project completion.
12. Completion requires orchestrator finalization.
13. Active GAPs/blockers stop dependent dispatch.
14. Runtime/governance violations stop dispatch until correction.

## Authority precedence

When instructions conflict, the highest applicable authority wins:

```text
1. Immutable governance rules
2. Runtime state schema and state transition rules
3. Filesystem governance
4. Role instructions
5. Task packet
6. NEXT_ACTION operational instruction
7. Handoff prompt
8. Agent RESULT recommendation
```

A lower authority cannot relax or bypass a higher authority.

## Conflict handling

| Conflict | Resolution |
|---|---|
| Task packet conflicts with mandatory workflow | Treat as workflow violation; do not dispatch. |
| NEXT_ACTION conflicts with transition table | Treat as invalid runtime state; enter correction. |
| Role instruction conflicts with task packet | Role/governance wins unless explicitly governed and audited. |
| Owner answer changes requirements/architecture | Route through designer/audit or bounded correction task. |
| Archive/deprecated doc appears in REQUIRED_DOCS | Treat task packet as invalid. |

## Governance freeze

Governance freeze is active when any of the following occurs:

- runtime schema violation;
- schema/template mismatch;
- invalid transition;
- task packet outside ACTIVE_DOC_ROOT;
- deprecated/superseded task selected for dispatch;
- ordinary agent changed forbidden files;
- universal package is being changed;
- manual runtime intervention occurred;
- finalization invariant fails.

During freeze:

```text
PROJECT_STATUS: blocked
CURRENT_PHASE: correction | blocked
NEXT_ACTION.ACTION_TYPE: correction | wait_for_owner | stop
```

No normal project `create_agent` dispatch is allowed.

## Freeze exit criteria

Freeze exits only when:

- runtime files validate against schema;
- transition table permits NEXT_ACTION;
- schema/templates are aligned;
- package version/changelog are updated if package docs changed;
- superseded/deprecated tasks are not active;
- active GAPs/blockers are routed correctly;
- NEXT_ACTION is regenerated from validated runtime state.

## Manual intervention boundary

The project owner may perform emergency runtime correction. After manual intervention, the orchestrator must not continue dispatch from memory. It must reread all runtime files, validate the state tuple, and regenerate NEXT_ACTION or enter correction/wait.
