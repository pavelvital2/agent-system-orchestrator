# TASK PACKET

```text
TASK_ID: TASK_FIXTURE_CONTEXT_PACK_BUILD_FORBIDDEN_ROOT
TASK_STATUS: active
TASK_KIND: normal
TASK_TYPE: developer
TARGET_ROLE: developer
```

## Required docs

- `project-input/private-context.md`

## Forbidden write paths

```text
project-input/**
project-runtime/**
project-archive/**
```

## Acceptance criteria

- Forbidden-root task packet fails.
