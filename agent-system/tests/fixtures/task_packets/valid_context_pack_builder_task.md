# TASK PACKET

```text
TASK_ID: TASK_FIXTURE_CONTEXT_PACK_BUILD_VALID
TASK_STATUS: active
TASK_KIND: normal
TASK_TYPE: developer
TARGET_ROLE: developer
```

## Required docs

- `agent-system/03_templates/TASK_PACKET_TEMPLATE.md`
- `agent-system/03_templates/CONTEXT_PACK_TEMPLATE.json`
- `agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/validate_context_pack.py`

## Source-of-truth docs

- `agent-system/03_templates/TASK_PACKET_TEMPLATE.md`
- `agent-system/03_templates/CONTEXT_PACK_TEMPLATE.json`
- `agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/validate_context_pack.py`

## Allowed write paths

- `agent-system/tools/aso/**`
- `agent-system/tools/aso/tests/**`
- `agent-system/tests/fixtures/context_pack/**`
- `agent-system/tests/fixtures/task_packets/**`

## Forbidden write paths

```text
project-input/**
project-runtime/**
project-archive/**
.tmp/**
tmp/**
```

## Acceptance criteria

- Builder emits a valid context pack for a valid task packet.
- Generated proposal passes validate-context-pack.
- Context budget is explicit and bounded.
