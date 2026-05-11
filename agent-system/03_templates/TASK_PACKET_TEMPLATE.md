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

## TASK_TITLE

Краткое название bounded-задачи.

Пример:

```text
Implement local task service
```

---

## TASK_TYPE

```text
designer
developer
auditor
tester
technical_writer
```

Задача должна относиться только к одному типу роли.

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
