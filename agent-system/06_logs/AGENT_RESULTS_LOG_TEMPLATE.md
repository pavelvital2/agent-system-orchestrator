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
- failed, blocked, gap, and violation results must be logged before recovery routing;
- `RESULT_REF` must point to the full RESULT location or contain a bounded reference;
- the log must not store full large reports;
- ordinary profile agents must not edit this file.
