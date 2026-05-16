# REQUESTER_RETURN_PROTOCOL

## Purpose

This document defines deterministic return routing when one bounded task
requests a research dependency or other audited dependency before it can safely
continue.

The protocol prevents the orchestrator from guessing the return target and
prevents unaudited research from influencing requester continuation.

## Return metadata

Every task packet that represents a requester-created dependency must include:

```text
REQUESTED_BY_ROLE:
REQUESTED_BY_TASK:
RETURN_TO_REQUESTER_AFTER_AUDIT_PASS: yes | no
RETURN_TO_ROLE_AFTER_AUDIT_PASS:
RETURN_TASK_AFTER_AUDIT_PASS:
```

Rules:

- `REQUESTED_BY_ROLE` is the profile role that identified the dependency.
- `REQUESTED_BY_TASK` is the original bounded task that cannot safely continue
  without the dependency result.
- `RETURN_TO_REQUESTER_AFTER_AUDIT_PASS` controls whether the orchestrator may
  route back to requester continuation after the dependency is accepted.
- `RETURN_TO_ROLE_AFTER_AUDIT_PASS` is the exact role to dispatch after audit
  pass, or `none` if no return is allowed.
- `RETURN_TASK_AFTER_AUDIT_PASS` is the exact continuation task id or task
  packet reference, or `NONE` if no return is allowed.

The same return metadata must be recorded in `TASK_REGISTRY.md` for the
dependency task. `NEXT_ACTION.md` must preserve the return context whenever it
routes an audited dependency toward requester continuation.

## Research dependency route

Research dependencies use:

```text
TASK_KIND: research_dependency
```

A research dependency is not a GAP and not a BLOCKER.

```text
GAP:
  Missing decision or information that requires the project owner or accepted
  source-of-truth update.

RESEARCH_DEPENDENCY:
  Missing factual evidence that can be found through allowed sources such as
  code, documents, data, APIs, web sources, logs, or other task-approved
  sources.

BLOCKER:
  Technical obstacle preventing execution, such as missing access, missing
  file, missing credentials, broken environment, failed command, or unavailable
  dependency.
```

## Mandatory audited return chain

The only valid research-return chain is:

```text
requesting role
-> research_dependency task
-> research executor role
-> RESULT
-> auditor
-> audit pass
-> optional post-audit Git checkpoint if configured
-> requester continuation task
```

If audit fails:

```text
research_dependency task
-> auditor fail
-> correction task
-> repeat audit
```

The orchestrator must not return to the requester after audit `fail`,
`blocked`, `gap`, formally invalid research RESULT, or missing audit.

## Orchestrator rules

The orchestrator must:

- validate the dependency task packet before dispatch;
- validate that return metadata exists and is internally consistent;
- route research RESULT to an independent auditor before requester return;
- treat research `RECOMMENDED_NEXT_ACTION` and `NEXT_RECOMMENDED_ACTION` as
  advisory only;
- route to requester continuation only after independent audit pass and any
  required checkpoint;
- use `RETURN_TO_ROLE_AFTER_AUDIT_PASS` and `RETURN_TASK_AFTER_AUDIT_PASS`
  exactly as recorded;
- enter correction if return metadata is missing, contradictory, deprecated,
  superseded, or points outside allowed task-packet lifecycle.

The orchestrator must not:

- infer a return target from conversation history, informal notes, or memory;
- send raw unaudited research to the requester continuation task;
- mark dependent work `ready` before audit pass;
- collapse research, audit, and continuation into one action;
- use this protocol to create generalized parallel or DAG orchestration.

## Continuation task

Requester continuation tasks use:

```text
TASK_KIND: design_continuation | task_continuation
```

For design research, the continuation task must use `TASK_KIND:
design_continuation` and must include accepted research result references and
audit result references in `DEPENDENCIES`, `INPUTS`, or `READ_INPUTS`.

Continuation is invalid if it reads or relies on a research result that has not
passed independent audit.
