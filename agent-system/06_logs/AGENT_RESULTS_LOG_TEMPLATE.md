# AGENT_RESULTS_LOG

## Purpose

Short operational log of completed agent RESULT reports.

This file is updated by the orchestrator only.

It must not become a giant execution document and must not replace full RESULT files or project documentation.

## Entries

```text
DATE:
ROLE:
TASK:
STATUS:
RESULT_REF:
CHANGED_FILES:
NEXT_REQUIRED_ACTION:
```

## Rules

- each completed agent task must have one entry;
- failed, blocked, gap, and orchestrator-classified violation entries must be logged before recovery routing;
- profile-agent RESULT `STATUS` is limited to `pass`, `fail`, `blocked`, and `gap`;
- `violation` is an orchestrator-derived recovery/logging category, not a valid profile-agent RESULT `STATUS`;
- `RESULT_REF` must point to the full RESULT location or contain a bounded reference;
- the log must not store full large reports;
- ordinary profile agents must not edit this file.

## Invalid RESULT fallback

For a formally invalid RESULT, the orchestrator must write a deterministic bounded log entry without semantically inferring agent intent:

```text
DATE: <current runtime date if available, otherwise UNKNOWN>
ROLE: <handoff TARGET_ROLE if available, otherwise unknown>
TASK: <current NEXT_ACTION.TASK_ID if available, otherwise unknown>
STATUS: violation
RESULT_REF: <raw invalid RESULT reference>
CHANGED_FILES: <unknown unless safely extractable>
NEXT_REQUIRED_ACTION: correction
```
