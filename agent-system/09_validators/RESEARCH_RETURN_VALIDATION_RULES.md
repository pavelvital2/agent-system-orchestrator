# RESEARCH_RETURN_VALIDATION_RULES

## Purpose

This document defines documentation-first validation checks for research
dependencies and requester return routing.

## Source documents

```text
agent-system/02_runtime/REQUESTER_RETURN_PROTOCOL.md
agent-system/07_lifecycle/DESIGN_RESEARCH_LOOP.md
agent-system/03_templates/RESEARCH_REQUEST_TEMPLATE.md
agent-system/03_templates/RESEARCH_RESULT_TEMPLATE.md
agent-system/03_templates/DESIGN_CONTINUATION_TASK_TEMPLATE.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/04_state/RUNTIME_STATE_SCHEMA.md
```

## Required catches

A research dependency or requester return route is invalid when:

- `TASK_KIND: research_dependency` lacks requester return metadata;
- research dependency is used for an owner decision that should be a GAP;
- research dependency is used for a technical obstacle that should be blocked;
- `RETURN_TO_REQUESTER_AFTER_AUDIT_PASS: yes` lacks
  `RETURN_TO_ROLE_AFTER_AUDIT_PASS` or `RETURN_TASK_AFTER_AUDIT_PASS`;
- research output routes directly to requester continuation before audit pass;
- audit fail, blocked, or gap routes to requester continuation;
- continuation task reads unaudited research as accepted input;
- `NEXT_ACTION` drops required requester return context during dependency
  routing;
- task registry omits requester return metadata for dependency tasks.

## Valid route

```text
requester task
-> research_dependency task
-> research RESULT
-> auditor
-> audit pass
-> post-audit Git checkpoint if required
-> requester continuation task
```

This route is sequential. It does not allow generalized parallel orchestration.
