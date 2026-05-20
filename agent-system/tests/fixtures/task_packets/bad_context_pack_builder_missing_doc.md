# TASK PACKET

```text
TASK_ID: TASK_FIXTURE_CONTEXT_PACK_BUILD_MISSING_DOC
TASK_STATUS: active
TASK_KIND: normal
TASK_TYPE: developer
TARGET_ROLE: developer
```

## Required docs

- `agent-system/tests/fixtures/task_packets/missing_context_doc.md`

## Forbidden write paths

```text
project-input/**
project-runtime/**
project-archive/**
```

## Acceptance criteria

- Missing required docs fail under strict mode.
