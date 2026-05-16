# TASK_PACKET_TEMPLATE

## Назначение

Этот шаблон определяет обязательную структуру bounded task packet.

Каждая bounded-задача проекта должна существовать как отдельный markdown-файл, созданный проектировщиком по этому шаблону.

Цель шаблона:
- стандартизировать task packets;
- минимизировать context drift;
- обеспечить deterministic orchestration;
- ограничить scope агента;
- обеспечить стабильный audit flow;
- обеспечить минимальный REQUIRED_DOCS package.

---

# TASK PACKET

## TASK_ID

```text
<TASK_ID>
```

Правила:
- TASK_ID должен быть уникальным;
- TASK_ID нельзя переиспользовать;
- superseded task должен получать новый TASK_ID;
- TASK_ID должен быть стабильным после audit acceptance.

Пример:

```text
TASK_DEV_APP_001
```

---

## TASK_STATUS

```text
active | completed | superseded | deprecated
```

Rules:

- only `active` task packets may be selected by `NEXT_ACTION`;
- `completed` task packets are historical accepted/completed records;
- `superseded` task packets cannot be dispatched;
- `deprecated` task packets cannot be used as source-of-truth.

---

## SUPERSEDES

```text
<TASK_ID | NONE>
```

## SUPERSEDED_BY

```text
<TASK_ID | NONE>
```

Rules:

- replacing a task requires a new `TASK_ID`;
- old and new task packets cannot both be active;
- superseded task packets must not appear in `NEXT_ACTION`;
- superseded task packets must not be included in `REQUIRED_DOCS` for new work.

---

## CORRECTION_OF

```text
<TASK_ID | RESULT_REF | NONE>
```

## SOURCE_RESULT_REF

```text
<RESULT_REF | NONE>
```

## ATTEMPT_NO

```text
<number | NONE>
```

## FAILURE_TYPE

```text
governance | workflow | filesystem | runtime_state | audit | testing | gap | blocked | none
```

Rules:

- correction must be a bounded task;
- correction must use a fresh agent context;
- correction must not silently expand scope unless designer creates a new bounded task;
- correction must follow mandatory audit/testing/documentation path;
- SOURCE_RESULT_REF must reference the result or violation that triggered correction when applicable;
- SOURCE_RESULT_REF must be `NONE` only when no triggering result or violation applies;
- FAILURE_TYPE must classify the correction trigger;
- FAILURE_TYPE must be `none` only when the task is not a correction or no correction trigger applies.

---

## TASK_TITLE

Краткое название bounded-задачи.

Пример:

```text
Implement local task service
```

---

## TASK_TYPE

```text
requirements_analyst
designer
developer
auditor
tester
technical_writer
devops_setup_engineer
release_manager
```

Задача должна относиться только к одному profile execution role type.

Control pseudo-roles `orchestrator`, `project_owner`, and `none` are not valid
TASK_TYPE values unless a governance-only exception is explicitly documented.

---

## TARGET_ROLE

```text
<requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager>
```

Rules:
- TARGET_ROLE is the role that must execute this task;
- TARGET_ROLE must match TASK_TYPE for profile execution tasks unless the packet explicitly documents a governed exception;
- control pseudo-roles `orchestrator`, `project_owner`, and `none` are valid only in control/routing fields such as NEXT_ROLE_ON_* where the template permits them;
- a task packet must not assign work to multiple profile roles.

---

## DEPENDENCIES

```text
- <TASK_ID | audit result | runtime gate | NONE>
```

Rules:
- dependencies must be explicit and bounded;
- a dependency is ready only after required audit/checkpoint gates are satisfied;
- a task must not be dispatched while a required dependency is failed, blocked, superseded, or missing.

---

## DEPENDENCY_STATUS

```text
ready | blocked | pending | none
```

Rules:
- `ready` means all listed dependencies are satisfied for dispatch;
- `blocked` means at least one dependency prevents dispatch;
- `pending` means dependency work is known but incomplete;
- `none` is allowed only when DEPENDENCIES is `NONE`.

---

## PURPOSE

Краткая цель задачи.

Правила:
- только одна bounded цель;
- без скрытых подзадач;
- без “и заодно”.

---

## SOURCE_OF_TRUTH

Список документов, которые являются source-of-truth для этой задачи.

Пример:

```text
- project-docs/01_architecture/DATA_MODEL.md
- project-docs/01_architecture/WEB_CONTRACT.md
```

SOURCE_OF_TRUTH должен быть подмножеством REQUIRED_DOCS.

---

## SCOPE_IN

Список того, что агент обязан сделать.

Правила:
- каждый пункт должен быть проверяемым;
- scope должен быть bounded;
- scope не должен требовать чтения всего проекта;
- scope не должен подразумевать скрытые задачи.

Пример:

```text
- реализовать SQLite persistence
- реализовать create task flow
- реализовать delete task flow
```

---

## SCOPE_OUT

Список того, что агенту запрещено делать.

Правила:
- scope OUT обязателен;
- scope OUT должен ограничивать expansion behavior;
- если есть высокий риск scope creep — он должен быть явно перечислен.

Пример:

```text
- не добавлять auth
- не добавлять search
- не менять architecture docs
```

---

## REQUIRED_DOCS

Минимальный набор документов, разрешённых агенту.

Правила:
- REQUIRED_DOCS должен быть минимальным;
- нельзя передавать весь проект;
- нельзя передавать deprecated docs;
- нельзя передавать giant execution docs;
- документы должны находиться внутри ACTIVE_DOC_ROOT, кроме runtime/system docs;
- агент не должен читать документы вне REQUIRED_DOCS.

Пример:

```text
- project-docs/03_tasks/TASK_DEV_APP_001.md
- project-docs/01_architecture/DATA_MODEL.md
- project-docs/01_architecture/WEB_CONTRACT.md
```

---

## INPUTS

Внешние входные данные задачи.

Примеры:
- RESULT предыдущего агента;
- runtime state;
- uploaded file;
- external config.

Если inputs отсутствуют:

```text
NONE
```

---

## READ_INPUTS

Inputs or external package documents the agent must read in addition to REQUIRED_DOCS.

Examples:
- task graph;
- acceptance criteria;
- prior RESULT reference;
- owner decision record.

If no additional inputs are required:

```text
NONE
```

READ_INPUTS must not expand scope beyond this task packet.

---

## EXPECTED_OUTPUTS

Что агент должен вернуть.

Пример:

```text
- updated app.py
- RESULT according to AGENT_RESULT_TEMPLATE
```

---

## ALLOWED_FILE_CHANGES

Какие файлы или зоны проекта разрешено изменять.

Пример:

```text
- app.py
- src/tasks/*
```

Правила:
- список должен быть bounded;
- wildcard разрешён только если он действительно необходим;
- изменение файлов вне списка считается workflow violation.

---

## FORBIDDEN_FILE_CHANGES

Какие файлы запрещено изменять.

Пример:

```text
- agent-system/*
- project-runtime/*
- project-archive/*
```

---

## ACCEPTANCE_CRITERIA

Проверяемые критерии завершения задачи.

Правила:
- каждый критерий должен быть проверяемым;
- критерии не должны быть расплывчатыми;
- критерии должны соответствовать scope IN;
- acceptance criteria не должны расширять scope.

Пример:

```text
- task persists after restart
- status supports only active/done
- delete removes task from SQLite
```

---

## EVIDENCE_REQUIREMENTS

Какой evidence обязан предоставить агент.

Примеры:
- command output;
- HTTP response;
- screenshot;
- test log;
- RESULT reference;
- file diff summary.

Если evidence не требуется:

```text
NONE
```

---

## SETUP_HOOKS

Setup actions or checks required before task execution.

Examples:
- verify local dependencies are installed;
- confirm runtime state file exists;
- ensure required service is stopped before editing.

If no setup hook is required:

```text
NONE
```

Rules:
- setup hooks must be bounded and non-secret;
- setup hooks must not perform deployment or launch unless explicitly in scope;
- setup hooks must not bypass task dependencies or audit gates.

---

## LAUNCH_HOOKS

Launch, run, or smoke actions allowed after task execution.

Examples:
- run local smoke command;
- start local development service for verification;
- capture launch readiness evidence.

If no launch hook is required:

```text
NONE
```

Rules:
- launch hooks must be explicit before an agent runs them;
- production launch requires a dedicated governed launch task;
- launch evidence must be recorded in RESULT when hooks are executed.

---

## RESULT_PATH

Where the orchestrator should store or reference the agent RESULT.

Example:

```text
project-runtime/agent-results/<TASK_ID>.md
```

If the runtime uses a log reference instead of a file path:

```text
project-runtime/AGENT_RESULTS_LOG.md#<RESULT_REF>
```

Rules:
- RESULT_PATH must be deterministic;
- RESULT_PATH must not contain secrets;
- RESULT_PATH must be compatible with filesystem governance and runtime state.

---

## RISK_REQUIREMENTS

Какие риски агент обязан явно указать.

Примеры:
- untested runtime behavior;
- temporary workaround;
- partial implementation;
- environment dependency.

Если рисков нет:

```text
NONE
```

---

## MANDATORY_WORKFLOW

Обязательный следующий workflow.

Пример:

```text
developer → auditor
```

или:

```text
tester(pass) → technical_writer
tester(fail) → developer
tester(blocked) → orchestrator
```

Workflow не должен противоречить:
- ORCHESTRATOR_RUNTIME_LOOP.md
- role instructions;
- governance rules.

---

## NEXT_ROLE_ON_PASS

Роль следующего агента при STATUS: pass.

Пример:

```text
auditor
```

Если terminal task:

```text
none
```

---

## NEXT_ROLE_ON_FAIL

Следующая роль при STATUS: fail.

Пример:

```text
developer
```

---

## NEXT_ROLE_ON_BLOCKED

Следующая роль при STATUS: blocked.

Обычно:

```text
orchestrator
```

---

## NEXT_ROLE_ON_GAP

Следующая роль при STATUS: gap.

Обычно:

```text
orchestrator
```

Allowed NEXT_ROLE_ON_* values use the control/target role enum:

```text
orchestrator
requirements_analyst
designer
developer
auditor
tester
technical_writer
devops_setup_engineer
release_manager
project_owner
none
```

---

## AUDIT_REQUIREMENTS

```text
mandatory
optional
none
```

Правила:
- после designer — mandatory;
- после developer — mandatory;
- optional допустим только если это явно разрешено governance.

---

## TESTING_REQUIREMENTS

```text
mandatory
optional
none
```

Если testing required:
- должен существовать отдельный tester task packet.

---

## DOCUMENTATION_REQUIREMENTS

```text
mandatory
optional
none
```

Если documentation required:
- должен существовать отдельный technical writer task packet.

---

## FILESYSTEM_GOVERNANCE

Task packet обязан соответствовать:

```text
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
```

Task packet не должен:
- использовать deprecated docs;
- изменять forbidden zones;
- нарушать ACTIVE_DOC_ROOT;
- смешивать runtime/docs/source zones.

---

## RUNTIME_GOVERNANCE

Task packet обязан соответствовать:

```text
agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
```

Task packet не должен:
- нарушать mandatory workflow transitions;
- bypass audit;
- bypass correction flow;
- bypass runtime routing rules.

Task packet обязан быть совместим с:
`agent-system/04_state/RUNTIME_STATE_SCHEMA.md`

Task packet must also be compatible with:

```text
agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/VIOLATION_RECOVERY.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
```

---

## RESULT_FORMAT

Агент обязан вернуть RESULT строго по:

```text
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

---

## TERMINAL_CONDITIONS

Если задача terminal:
- явно указать terminal conditions;
- указать, кто переводит pipeline в completed state.

Обычно:

```text
orchestrator finalization
```

---

## NOTES

Дополнительные bounded notes.

Правила:
- notes не должны расширять scope;
- notes не заменяют acceptance criteria;
- notes не должны содержать скрытых задач.

Если notes отсутствуют:

```text
NONE
```
