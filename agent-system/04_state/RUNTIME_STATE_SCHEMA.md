# RUNTIME_STATE_SCHEMA

## Назначение

Этот документ определяет обязательную схему runtime state файлов проекта.
This document defines runtime state structure only.

Цель:
- предотвратить drift runtime state;
- сделать orchestration deterministic;
- исключить хранение состояния проекта только в контексте оркестратора;
- стандартизировать структуру runtime state файлов;
- отделить operational state от проектной документации.

Runtime state не является проектной документацией. Runtime state — это operational source-of-truth для оркестратора.

Runtime state validation must also comply with:

```text
agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/VIOLATION_RECOVERY.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
agent-system/PACKAGE_VERSIONING.md
agent-system/09_validators/VALIDATOR_SPEC.md
agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
```

---

## Обязательные runtime files

Минимальный набор runtime-файлов:

```text
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/GAP_REGISTER.md
project-runtime/TASK_REGISTRY.md
project-runtime/ACCEPTED_ARTIFACTS.md
project-runtime/AGENT_RESULTS_LOG.md
project-runtime/ORCHESTRATOR_EVENTS_LOG.md
project-runtime/STATUS_SUMMARY.md
```

Если какого-либо файла нет, оркестратор обязан создать его из шаблона или остановить pipeline в `wait_for_owner`, если шаблон отсутствует.

---

## Общие правила runtime state

Runtime state:

- обновляет только оркестратор;
- не обновляют профильные агенты;
- должен перечитываться оркестратором перед каждым действием;
- не должен заменять project docs;
- не должен содержать полный текст task packets;
- не должен содержать большие отчёты агентов;
- должен ссылаться на файлы, а не копировать их полностью;
- должен хранить только operational status.

Запрещено:
- хранить business requirements в runtime state;
- хранить architecture decisions в runtime state;
- хранить кодовые решения в runtime state;
- использовать runtime state как giant execution document.

---

# PROJECT_STATE.md schema

## Назначение

`PROJECT_STATE.md` фиксирует общее operational состояние проекта.

## Обязательные поля

```text
PROJECT_NAME:
PROJECT_ROOT:
TZ_PATH:
ACTIVE_DOC_ROOT:
PACKAGE_VERSION:
GOVERNANCE_RULESET_VERSION:
RUNTIME_SCHEMA_VERSION:
CURRENT_PHASE:
PROJECT_STATUS:
```

## CURRENT_PHASE допустимые значения

```text
bootstrap
design
design_audit
implementation
implementation_audit
testing
documentation
correction
blocked
finalization
completed
```

## PROJECT_STATUS допустимые значения

```text
active
blocked
completed
archived
```

## Branches

`PROJECT_STATE.md` должен содержать секцию:

```text
## Active branches
```

Формат ветки:

```text
BRANCH_ID:
STATUS: active | blocked | completed | archived
CURRENT_TASK:
CURRENT_AGENT_ROLE:
DEPENDENCIES:
BLOCKED_BY:
```

Если активных веток нет:

```text
NONE
```

## Completed milestones

Формат:

```text
- <milestone id>: <short result>
```

Если нет:

```text
NONE
```

## Active risks

Формат:

```text
- <risk id or short risk>
```

Если нет:

```text
NONE
```

## Active blockers

Формат:

```text
- <blocker id or short blocker>
```

Если нет:

```text
NONE
```

## Active gaps

Формат:

```text
- <GAP_ID>
```

Если нет:

```text
NONE
```

## Last accepted result

Формат:

```text
ROLE:
TASK:
DATE:
STATUS:
RESULT_REF:
```

---

# CURRENT_GATE.md schema

## Назначение

`CURRENT_GATE.md` фиксирует текущий gate pipeline.

## Обязательные поля

```text
GATE_ID:
GATE_NAME:
GATE_TYPE:
STATUS:
OWNER_ROLE:
TASK_ID:
TASK_PACKET:
```

## GATE_TYPE допустимые значения

```text
bootstrap
design
audit
implementation
testing
documentation
correction
finalization
terminal
```

## STATUS допустимые значения

```text
open
passed
failed
blocked
skipped
```

`skipped` допустим только если skip явно разрешён task packet или governance.

## Entry criteria

Секция обязательна:

```text
## Entry criteria
- <criterion>
```

Если отсутствуют:

```text
- NONE
```

## Exit criteria

Секция обязательна:

```text
## Exit criteria
- <criterion>
```

Если отсутствуют:

```text
- NONE
```

## Required next role

```text
designer | developer | auditor | tester | technical_writer | orchestrator | project_owner | none
```

## Gate evidence

Формат:

```text
## Gate evidence
- <file/result/command reference>
```

Если нет:

```text
- NONE
```

---

# NEXT_ACTION.md schema

## Назначение

`NEXT_ACTION.md` фиксирует единственное следующее разрешённое действие.

Оркестратор не должен выбирать действие из памяти. Он должен читать `NEXT_ACTION.md`.

## Обязательные поля

```text
ACTION_ID:
ACTION_TYPE:
TARGET_ROLE:
TASK_ID:
TASK_PACKET:
DEPENDENCY_STATUS:
BLOCKED_BY:
```

## ACTION_TYPE допустимые значения

```text
create_agent
route_result
update_state
wait_for_owner
correction
finalize
stop
```

## TARGET_ROLE допустимые значения

```text
designer
developer
auditor
tester
technical_writer
orchestrator
project_owner
none
```

## DEPENDENCY_STATUS допустимые значения

```text
ready
blocked
completed
not_applicable
```

## REQUIRED_UNIVERSAL_DOCS

Секция обязательна:

```text
REQUIRED_UNIVERSAL_DOCS:
- <path>
```

Если нет:

```text
- NONE
```

## REQUIRED_PROJECT_DOCS

Секция обязательна:

```text
REQUIRED_PROJECT_DOCS:
- <path>
```

Если нет:

```text
- NONE
```

## EXPECTED_RESULT

Секция обязательна:

```text
EXPECTED_RESULT:
- <expected format or file>
```

Обычно:

```text
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

## Instruction for orchestrator

Секция обязательна:

```text
## Instruction for orchestrator
<one precise instruction>
```

Правила:
- инструкция должна быть одна;
- инструкция не должна содержать скрытые подзадачи;
- если нужно несколько действий, каждое действие должно стать отдельным NEXT_ACTION после завершения предыдущего.

---

# GAP_REGISTER.md schema

## Назначение

`GAP_REGISTER.md` фиксирует GAP, которые требуют решения владельца проекта или correction flow.

## Active gaps

Формат:

```text
GAP_ID:
STATUS: open | answered | closed | superseded
SOURCE_ROLE:
SOURCE_TASK:
TYPE: business | functional | technical | documentation | acceptance | runtime
BLOCKS:
QUESTION_TO_OWNER:
RECOMMENDED_OPTIONS:
OWNER_ANSWER:
RESOLUTION_TASK:
CREATED_AT:
UPDATED_AT:
```

Если активных GAP нет:

```text
NONE
```

## Closed gaps

Формат:

```text
GAP_ID:
RESOLUTION:
CLOSED_BY:
CLOSED_AT:
```

Если закрытых GAP нет:

```text
NONE
```

## GAP routing rules

- business GAP → project_owner;
- functional GAP → project_owner или designer, если вопрос технически проектный;
- technical GAP → designer;
- documentation GAP → designer или technical_writer;
- acceptance GAP → designer;
- runtime GAP → designer, если не требуется business decision.

Оркестратор не решает GAP по существу.

---

# AGENT_RESULTS_LOG.md schema

## Назначение

`AGENT_RESULTS_LOG.md` фиксирует краткую историю результатов агентов.

Он не должен содержать полные большие отчёты, если они сохранены отдельными файлами.

## Формат записи

```text
DATE:
ROLE:
TASK:
STATUS:
RESULT_REF:
CHANGED_FILES:
NEXT_RECOMMENDED_ACTION:
```

## Правила

- каждая завершённая agent task должна иметь запись;
- failed, blocked, gap, and orchestrator-classified violation entries must be logged before recovery routing;
- Profile-agent RESULT STATUS remains limited to pass | fail | blocked | gap; violation is a log/recovery classification only.
- RESULT_REF должен ссылаться на место хранения полного RESULT или содержать краткий RESULT, если он небольшой;
- `NEXT_RECOMMENDED_ACTION` records the advisory next action emitted by the agent RESULT;
- legacy consumers may display `NEXT_REQUIRED_ACTION`, but new log entries must use `NEXT_RECOMMENDED_ACTION`;
- log не должен заменять project docs;
- log не должен становиться giant execution document.

---

# TASK_REGISTRY.md schema

## Назначение

`TASK_REGISTRY.md` фиксирует operational lifecycle state задач и их traceability.

## Формат записи

```text
TASK_ID:
TASK_TITLE:
TASK_TYPE:
OWNER_ROLE:
STATUS:
TASK_PACKET:
DEPENDENCIES:
RESULT_REFS:
AUDIT_REFS:
CORRECTION_LINKS:
COMMIT_HASH:
CREATED_AT:
UPDATED_AT:
```

## STATUS допустимые значения

```text
pending
ready
running
audit_pending
audit_passed
checkpoint_done
blocked
failed
superseded
completed
```

## Правила

- `DEPENDENCIES` must list prerequisite task ids or `NONE`;
- `RESULT_REFS` must reference bounded RESULT records or `NONE`;
- `AUDIT_REFS` must reference bounded audit records or `NONE`;
- `CORRECTION_LINKS` must reference correction tasks/results or `NONE`;
- `COMMIT_HASH` is required after a successful post-audit Git checkpoint and may be `NONE` before checkpoint;
- task registry entries must not contain full task packet, RESULT, or audit contents.

---

# ACCEPTED_ARTIFACTS.md schema

## Назначение

`ACCEPTED_ARTIFACTS.md` фиксирует acceptance state артефактов по bounded references.

## Формат записи

```text
ARTIFACT_ID:
ARTIFACT_TYPE:
ARTIFACT_REF:
STATUS:
SOURCE_TASK:
SOURCE_RESULT_REF:
AUDIT_REF:
SUPERSEDES:
SUPERSEDED_BY:
COMMIT_HASH:
ACCEPTED_AT:
UPDATED_AT:
NOTES:
```

## STATUS допустимые значения

```text
draft
accepted
failed
superseded
```

## Правила

- `draft`, `accepted`, `failed`, and `superseded` must remain distinct states;
- `ARTIFACT_REF`, `SOURCE_RESULT_REF`, and `AUDIT_REF` must be bounded references or `NONE`;
- superseded artifacts must remain traceable through `SUPERSEDES` and `SUPERSEDED_BY`;
- `COMMIT_HASH` is required after a successful post-audit Git checkpoint and may be `NONE` before checkpoint;
- accepted artifacts registry entries must not contain full artifact contents.

---

# ORCHESTRATOR_EVENTS_LOG.md schema

## Назначение

`ORCHESTRATOR_EVENTS_LOG.md` фиксирует material orchestrator events and routing decisions.

## Формат записи

```text
DATE:
EVENT_TYPE:
ACTOR:
TASK_ID:
GATE_ID:
ACTION_ID:
STATUS:
SUMMARY:
INPUT_REFS:
OUTPUT_REFS:
COMMIT_HASH:
NEXT_ACTION_REF:
```

## EVENT_TYPE допустимые значения

```text
bootstrap
owner_pause
validator_result
checkpoint
manual_intervention
task_dispatch
result_route
audit_route
correction_route
state_update
violation_recovery
```

## ACTOR допустимые значения

```text
orchestrator
project_owner
validator
system
```

## Правила

- bootstrap, owner pause, validator result, checkpoint, and manual intervention events must be representable;
- `COMMIT_HASH` is required for successful checkpoint events and must be `NONE` otherwise;
- `INPUT_REFS`, `OUTPUT_REFS`, and `NEXT_ACTION_REF` must use bounded references or `NONE`;
- orchestrator events log entries must not contain full task packet, RESULT, or audit contents.

---

# STATUS_SUMMARY.md schema

## Назначение

`STATUS_SUMMARY.md` фиксирует compact operational summary текущего состояния.

## Обязательные поля

```text
PROJECT_STATUS:
CURRENT_PHASE:
CURRENT_GATE:
GATE_STATUS:
LAST_ACCEPTED_RESULT:
LAST_FAILED_RESULT:
ACTIVE_BLOCKERS:
ACTIVE_GAPS:
NEXT_ACTION:
LAUNCH_READINESS:
UPDATED_AT:
PROJECT_STATE_REF:
CURRENT_GATE_REF:
NEXT_ACTION_REF:
TASK_REGISTRY_REF:
ACCEPTED_ARTIFACTS_REF:
AGENT_RESULTS_LOG_REF:
ORCHESTRATOR_EVENTS_LOG_REF:
```

## LAUNCH_READINESS допустимые значения

```text
not_started
not_ready
blocked
ready
launched
not_applicable
```

## Правила

- `PROJECT_STATUS` must match `PROJECT_STATE.md`;
- `CURRENT_GATE` and `GATE_STATUS` must match `CURRENT_GATE.md`;
- `LAST_ACCEPTED_RESULT` and `LAST_FAILED_RESULT` must reference bounded result records or `NONE`;
- `ACTIVE_BLOCKERS` must list blocker ids or `NONE`;
- `ACTIVE_GAPS` must list GAP ids or `NONE`;
- `NEXT_ACTION` must summarize exactly one governed next action;
- `LAUNCH_READINESS` must summarize launch gate state when applicable, otherwise `not_applicable`.

---

## Runtime state tuple validation

The orchestrator must validate the combined runtime state tuple before dispatch:

```text
PROJECT_STATE.CURRENT_PHASE
PROJECT_STATE.PROJECT_STATUS
PROJECT_STATE.ACTIVE_DOC_ROOT
PROJECT_STATE.PACKAGE_VERSION
PROJECT_STATE.GOVERNANCE_RULESET_VERSION
PROJECT_STATE.RUNTIME_SCHEMA_VERSION
CURRENT_GATE.GATE_TYPE
CURRENT_GATE.STATUS
CURRENT_GATE.OWNER_ROLE
CURRENT_GATE.TASK_ID
CURRENT_GATE.TASK_PACKET
NEXT_ACTION.ACTION_TYPE
NEXT_ACTION.TARGET_ROLE
NEXT_ACTION.TASK_ID
NEXT_ACTION.TASK_PACKET
NEXT_ACTION.DEPENDENCY_STATUS
GAP_REGISTER.active_gaps
TASK_REGISTRY.task_statuses
TASK_REGISTRY.dependencies
TASK_REGISTRY.result_refs
TASK_REGISTRY.audit_refs
TASK_REGISTRY.correction_links
TASK_REGISTRY.commit_hashes
ACCEPTED_ARTIFACTS.artifact_statuses
ACCEPTED_ARTIFACTS.audit_refs
ORCHESTRATOR_EVENTS_LOG.latest_events
STATUS_SUMMARY.project_status
STATUS_SUMMARY.current_gate
STATUS_SUMMARY.last_accepted_result
STATUS_SUMMARY.last_failed_result
STATUS_SUMMARY.active_blockers
STATUS_SUMMARY.active_gaps
STATUS_SUMMARY.next_action
STATUS_SUMMARY.launch_readiness
PROJECT_STATE.active_blockers
PROJECT_STATE.active_branches
```

A set of runtime files can be locally valid but globally invalid.
If tuple validation fails, the orchestrator must enter correction flow.

## Schema/template parity

The following templates must be compatible with this schema:

```text
agent-system/04_state/PROJECT_STATE_TEMPLATE.md
agent-system/04_state/CURRENT_GATE_TEMPLATE.md
agent-system/04_state/NEXT_ACTION_TEMPLATE.md
agent-system/04_state/TASK_REGISTRY_TEMPLATE.md
agent-system/04_state/ACCEPTED_ARTIFACTS_TEMPLATE.md
agent-system/05_gap_flow/GAP_REGISTER_TEMPLATE.md
agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md
agent-system/06_logs/ORCHESTRATOR_EVENTS_LOG_TEMPLATE.md
agent-system/06_logs/STATUS_SUMMARY_TEMPLATE.md
```

If schema and templates conflict, bootstrap is invalid and governance freeze applies.

# Transition authority

This document defines runtime state structure only.

Authoritative runtime transition rules, forbidden transitions, terminal completion rules, and invalid-state detection are defined in:

```text
agent-system/02_runtime/STATE_TRANSITION_RULES.md
```

Detailed documentation-first runtime consistency checks are defined in:

```text
agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
```

Structural runtime state validation in this schema does not authorize role, phase, gate, action, terminal, GAP, blocker, or workflow transitions.

If runtime state is structurally invalid, or if a runtime state tuple is incompatible with authoritative transition rules, recovery routing is governed by:

```text
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/VIOLATION_RECOVERY.md
```

---

# Versioning

Runtime schema может изменяться только через отдельную задачу на обновление universal package.

Изменения schema должны быть:
- зафиксированы в файле;
- применены к шаблонам runtime state;
- учтены в ORCHESTRATOR_RUNTIME_LOOP;
- при необходимости проверены тестовым pipeline.
