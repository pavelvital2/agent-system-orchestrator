# RUNTIME_STATE_SCHEMA

## Назначение

Этот документ определяет обязательную схему runtime state файлов проекта.

Цель:
- предотвратить drift runtime state;
- сделать orchestration deterministic;
- исключить хранение состояния проекта только в контексте оркестратора;
- стандартизировать переходы между агентами;
- отделить operational state от проектной документации.

Runtime state не является проектной документацией. Runtime state — это operational source-of-truth для оркестратора.

---

## Обязательные runtime files

Минимальный набор runtime-файлов:

```text
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/GAP_REGISTER.md
project-runtime/AGENT_RESULTS_LOG.md
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
NEXT_REQUIRED_ACTION:
```

## Правила

- каждая завершённая agent task должна иметь запись;
- RESULT_REF должен ссылаться на место хранения полного RESULT или содержать краткий RESULT, если он небольшой;
- log не должен заменять project docs;
- log не должен становиться giant execution document.

---

# Runtime transition rules

## designer pass

Если designer возвращает `STATUS: pass`:

```text
NEXT_ACTION:
ACTION_TYPE: create_agent
TARGET_ROLE: auditor
```

Designer не может напрямую вести к developer.

---

## developer pass

Если developer возвращает `STATUS: pass`:

```text
NEXT_ACTION:
ACTION_TYPE: create_agent
TARGET_ROLE: auditor
```

Developer не может напрямую вести к tester или technical_writer.

---

## auditor pass

Если auditor возвращает `STATUS: pass`, следующий шаг определяется audited task packet:

- после design audit → следующий planned implementation/correction task;
- после implementation audit → tester, если testing required;
- иначе next task согласно task packet.

---

## tester pass

Если tester возвращает `STATUS: pass`:

- если documentation required → technical_writer;
- если documentation not required → orchestrator finalization.

---

## technical_writer pass

Если technical_writer возвращает `STATUS: pass`:

```text
NEXT_ACTION:
ACTION_TYPE: finalize
TARGET_ROLE: orchestrator
```

Technical writer не переводит проект в completed самостоятельно.

---

## blocked

Если агент возвращает `STATUS: blocked`:

- runtime/environment blocker → designer;
- technical blocker → designer или developer correction task;
- missing owner input → project_owner;
- missing file/instruction → project_owner или correction flow.

---

## gap

Если агент возвращает `STATUS: gap`:

- GAP фиксируется в `GAP_REGISTER.md`;
- зависимая ветка переводится в blocked;
- независимые ветки могут продолжаться, если они явно есть в `NEXT_ACTION.md` или runtime state.

---

# Terminal state rules

Проект может получить:

```text
CURRENT_PHASE: completed
PROJECT_STATUS: completed
```

только после orchestrator finalization.

Перед finalization оркестратор обязан проверить:

- нет active GAP;
- нет active blockers;
- все mandatory audit gates passed;
- mandatory testing passed;
- mandatory documentation completed;
- NEXT_ACTION может быть safely set to stop;
- CURRENT_GATE может быть set to terminal/passed.

Ни один профильный агент не имеет права выставлять project completed.

---

# Workflow violation

Если runtime state нарушает schema или mandatory workflow:

```text
CURRENT_PHASE: correction
PROJECT_STATUS: blocked
NEXT_ACTION:
ACTION_TYPE: correction
TARGET_ROLE: orchestrator
```

Оркестратор обязан остановить dispatch новых агентов до correction.

Примеры workflow violation:

- designer → developer без audit;
- developer → tester без audit;
- task packet вне ACTIVE_DOC_ROOT;
- REQUIRED_DOCS содержит deprecated docs;
- обычный агент изменил `project-runtime/`;
- technical_writer объявил project completed;
- tester изменил код;
- auditor изменил проверяемый код.

---

# Versioning

Runtime schema может изменяться только через отдельную задачу на обновление universal package.

Изменения schema должны быть:
- зафиксированы в файле;
- применены к шаблонам runtime state;
- учтены в ORCHESTRATOR_RUNTIME_LOOP;
- при необходимости проверены тестовым pipeline.
