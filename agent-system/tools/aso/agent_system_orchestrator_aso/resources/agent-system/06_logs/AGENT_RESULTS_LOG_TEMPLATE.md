# AGENT_RESULTS_LOG

## Purpose

Short operational log of completed agent RESULT reports.

This file is updated by the orchestrator only.

It must not become a giant execution document and must not replace full RESULT files or project documentation.

## Entries

```text
DATE:
AGENT_INSTANCE_ID:
ROLE:
TASK:
TASK_ID:
STATUS:
RESULT_REF:
CHANGED_FILES:
NEXT_RECOMMENDED_ACTION:
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
```

## Rules

- each completed agent task must have one entry;
- each entry must identify the `AGENT_INSTANCE_ID` that produced the RESULT;
- failed, blocked, gap, and orchestrator-classified violation entries must be logged before recovery routing;
- profile-agent RESULT `STATUS` is limited to `pass`, `fail`, `blocked`, and `gap`;
- profile-agent RESULT entries must record `REUSE_ALLOWED: false` and
  `AGENT_TERMINATION_REQUIRED: true`;
- `violation` is an orchestrator-derived recovery/logging category, not a valid profile-agent RESULT `STATUS`;
- `RESULT_REF` must point to the full RESULT location or contain a bounded reference;
- new worker RESULT references must use
  `project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_<N>.md`;
- new audit RESULT references must use
  `project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_<N>.md`;
- `project-runtime/agent-results/` may be read as compatibility legacy
  evidence, but it is read-only for new RESULT references;
- `NEXT_RECOMMENDED_ACTION` records the advisory next action emitted by the agent RESULT;
- legacy consumers may display `NEXT_REQUIRED_ACTION`, but new log entries must use `NEXT_RECOMMENDED_ACTION`;
- the log must not store full large reports;
- ordinary profile agents must not edit this file.

## Invalid RESULT fallback

For a formally invalid RESULT, the orchestrator must write a deterministic bounded log entry without semantically inferring agent intent:

```text
DATE: <current runtime date if available, otherwise UNKNOWN>
AGENT_INSTANCE_ID: <AGENT_INSTANCE_ID if safely extractable, otherwise unknown>
ROLE: <handoff TARGET_ROLE if available, otherwise unknown>
TASK: <current NEXT_ACTION.TASK_ID if available, otherwise unknown>
TASK_ID: <current NEXT_ACTION.TASK_ID if available, otherwise unknown>
STATUS: violation
RESULT_REF: <raw invalid RESULT reference>
CHANGED_FILES: <unknown unless safely extractable>
NEXT_RECOMMENDED_ACTION: correction
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
```
