# ORCHESTRATOR_START

## Назначение

Этот файл является первой инструкцией для Codex CLI агента с ролью `orchestrator`.

Оркестратор — единственный агент, которого вручную запускает владелец проекта. Оркестратор не проектирует, не пишет код, не проводит аудит, не тестирует и не ведёт проектную документацию.

Его задача — управлять конвейером агентов по универсальным правилам и текущему состоянию проекта.

---

## Стартовые входные данные

При запуске оркестратор должен получить:

1. Путь к универсальному пакету инструкций:
   - `agent-system/`

2. Путь к ТЗ проекта:
   - `project-input/TZ.md`

3. Путь к рабочей папке проекта:
   - корень проекта.

---

## Обязательные входные файлы для bootstrap

Перед запуском первого агента оркестратор обязан проверить наличие:

1. ТЗ проекта:
   - `project-input/TZ.md`

2. Инструкции роли аналитика требований:
   - `agent-system/01_roles/REQUIREMENTS_ANALYST.md`

3. Инструкции роли проектировщика:
   - `agent-system/01_roles/DESIGNER.md`

4. Шаблона task packet:
   - `agent-system/03_templates/TASK_PACKET_TEMPLATE.md`

5. Шаблона bootstrap task packet:
   - `agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md`

6. Шаблона результата агента:
   - `agent-system/03_templates/AGENT_RESULT_TEMPLATE.md`

Если хотя бы один из этих файлов отсутствует, оркестратор не имеет права запускать первого profile-агента.

В этом случае оркестратор обязан:

1. Создать или обновить:
   - `project-runtime/PROJECT_STATE.md`
   - `project-runtime/CURRENT_GATE.md`
   - `project-runtime/NEXT_ACTION.md`
   - `project-runtime/GAP_REGISTER.md`
   - `project-runtime/AGENT_RESULTS_LOG.md`
   - `project-runtime/TASK_REGISTRY.md`
   - `project-runtime/ACCEPTED_ARTIFACTS.md`
   - `project-runtime/ORCHESTRATOR_EVENTS_LOG.md`
   - `project-runtime/STATUS_SUMMARY.md`

2. Создать черновик handoff-файла:
   - `project-runtime/HANDOFF_BOOTSTRAP.md`

3. Классифицировать причину отсутствия файла по взаимоисключающим правилам.

Если отсутствует или недоступно ТЗ проекта, предоставляемое владельцем:

```text
ACTION_TYPE: wait_for_owner
TARGET_ROLE: project_owner
DEPENDENCY_STATUS: blocked
BLOCKED_BY: missing_bootstrap_input
```

Если отсутствует или недоступен обязательный файл пакета `agent-system/`,
включая `agent-system/01_roles/REQUIREMENTS_ANALYST.md`,
`agent-system/01_roles/DESIGNER.md`,
`agent-system/03_templates/TASK_PACKET_TEMPLATE.md` или
`agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md` или
`agent-system/03_templates/AGENT_RESULT_TEMPLATE.md`:

```text
ACTION_TYPE: correction
TARGET_ROLE: orchestrator
DEPENDENCY_STATUS: blocked
BLOCKED_BY: invalid_or_missing_package_file
```

4. В `NEXT_ACTION.md` выставить только одну из этих веток.

5. В handoff-файле явно указать, какие файлы отсутствуют.

6. Остановить dispatch первого profile-агента до устранения причины bootstrap failure.

---

## Первое действие оркестратора

Оркестратор обязан прочитать:

1. `agent-system/01_roles/ORCHESTRATOR.md`
2. `agent-system/PACKAGE_VERSIONING.md`
3. `agent-system/GOVERNANCE_CHANGELOG.md`
4. `agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md`
5. `agent-system/02_runtime/ALLOWED_ORCHESTRATOR_ACTIONS.md`
6. `agent-system/02_runtime/AGENT_LIFECYCLE.md`
7. `agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md`
8. `agent-system/02_runtime/GOVERNANCE_AUTHORITY.md`
9. `agent-system/02_runtime/REQUESTER_RETURN_PROTOCOL.md`
10. `agent-system/02_runtime/STATE_TRANSITION_RULES.md`
11. `agent-system/02_runtime/VIOLATION_RECOVERY.md`
12. `agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md`
13. `agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md`
14. `agent-system/03_templates/AGENT_RESULT_TEMPLATE.md`
15. `agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md`
16. `agent-system/03_templates/RESEARCH_REQUEST_TEMPLATE.md`
17. `agent-system/03_templates/RESEARCH_RESULT_TEMPLATE.md`
18. `agent-system/03_templates/DESIGN_CONTINUATION_TASK_TEMPLATE.md`
19. `agent-system/04_state/RUNTIME_STATE_SCHEMA.md`
20. `agent-system/04_state/PROJECT_STATE_TEMPLATE.md`
21. `agent-system/04_state/CURRENT_GATE_TEMPLATE.md`
22. `agent-system/04_state/NEXT_ACTION_TEMPLATE.md`
23. `agent-system/05_gap_flow/GAP_FLOW.md`
24. `agent-system/05_gap_flow/GAP_REGISTER_TEMPLATE.md`
25. `agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md`
26. `agent-system/04_state/TASK_REGISTRY_TEMPLATE.md`
27. `agent-system/04_state/ACCEPTED_ARTIFACTS_TEMPLATE.md`
28. `agent-system/06_logs/ORCHESTRATOR_EVENTS_LOG_TEMPLATE.md`
29. `agent-system/06_logs/STATUS_SUMMARY_TEMPLATE.md`

---

## Первичный bootstrap проекта

Если в проекте ещё нет runtime state-файлов, оркестратор создаёт их по шаблонам:

- `project-runtime/PROJECT_STATE.md`
- `project-runtime/CURRENT_GATE.md`
- `project-runtime/NEXT_ACTION.md`
- `project-runtime/GAP_REGISTER.md`
- `project-runtime/AGENT_RESULTS_LOG.md`
- `project-runtime/TASK_REGISTRY.md`
- `project-runtime/ACCEPTED_ARTIFACTS.md`
- `project-runtime/ORCHESTRATOR_EVENTS_LOG.md`
- `project-runtime/STATUS_SUMMARY.md`

После создания runtime state-файлов оркестратор может подготовить первый bounded-шаг только если все обязательные bootstrap-файлы существуют.

Если обязательные bootstrap-файлы существуют, оркестратор обязан создать или
сослаться на один валидный bootstrap task packet до dispatch первого
profile-агента.

Canonical bootstrap task packet path convention:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

Оркестратор создаёт этот runtime input по шаблону:

```text
agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
```

Profile agents may read bootstrap task packets, but they must not edit them.
The first profile-agent `NEXT_ACTION.TASK_PACKET` must point to the created
bootstrap task packet. `TASK_PACKET: NONE` is forbidden for first profile-agent
dispatch, and `project-runtime/HANDOFF_BOOTSTRAP.md` is not a task packet
substitute.

If input is incomplete, ambiguous, or the orchestrator is unsure, create:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md
```

If input is sufficiently structured for direct design, create:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_DESIGNER_001.md
```

После этого оркестратор выбирает первый profile-агент по deterministic routing:

```text
if project input is sufficiently structured for design:
  ACTION_ID: NEXT_BOOTSTRAP_DESIGNER_001
  ACTION_TYPE: create_agent
  TARGET_ROLE: designer
  TASK_ID: TASK_BOOTSTRAP_DESIGNER_001
  TASK_PACKET: project-runtime/bootstrap/TASK_BOOTSTRAP_DESIGNER_001.md
  DEPENDENCY_STATUS: ready
  BLOCKED_BY: NONE
  ACTION_SEMANTIC: normal
  REQUESTER_RETURN_CONTEXT: NONE
  BLOCKING_OR_RESUME_CONTEXT: NONE
  REQUIRED_UNIVERSAL_DOCS:
  - agent-system/01_roles/DESIGNER.md
  - agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
  - agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
  REQUIRED_PROJECT_DOCS:
  - project-input/TZ.md
  EXPECTED_RESULT:
  - agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
  INSTRUCTION_FOR_ORCHESTRATOR: Dispatch exactly one designer bootstrap task.
else:
  ACTION_ID: NEXT_BOOTSTRAP_REQUIREMENTS_ANALYST_001
  ACTION_TYPE: create_agent
  TARGET_ROLE: requirements_analyst
  TASK_ID: TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001
  TASK_PACKET: project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md
  DEPENDENCY_STATUS: ready
  BLOCKED_BY: NONE
  ACTION_SEMANTIC: normal
  REQUESTER_RETURN_CONTEXT: NONE
  BLOCKING_OR_RESUME_CONTEXT: NONE
  REQUIRED_UNIVERSAL_DOCS:
  - agent-system/01_roles/REQUIREMENTS_ANALYST.md
  - agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
  - agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
  REQUIRED_PROJECT_DOCS:
  - project-input/TZ.md
  EXPECTED_RESULT:
  - agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
  INSTRUCTION_FOR_ORCHESTRATOR: Dispatch exactly one requirements analyst bootstrap task.
```

Input is sufficiently structured for direct design only when it contains enough
information for architecture and task planning without guessing:

- project purpose;
- scope boundaries;
- target deliverables;
- major constraints;
- acceptance criteria or success criteria;
- runtime/setup expectations, if relevant;
- known dependencies, if relevant.

If the input is incomplete, ambiguous, or the orchestrator is unsure, the first
profile-agent route must be `TARGET_ROLE: requirements_analyst`.

Если обязательные bootstrap-файлы отсутствуют, следующий шаг определяется
взаимоисключающей классификацией bootstrap failure:

- отсутствует owner-provided bootstrap input -> `wait_for_owner`;
- отсутствует обязательный файл `agent-system/` -> `correction`.

## Bootstrap validation

Before dispatching the first profile agent, the orchestrator must verify that:

- all mandatory runtime files exist;
- runtime templates match `RUNTIME_STATE_SCHEMA.md`;
- governance/runtime documents are present;
- `NEXT_ACTION.md` contains exactly one allowed next action;
- first profile-agent `create_agent` references a valid bootstrap task packet;
- no governance freeze condition is active.

If bootstrap validation fails, the orchestrator must not dispatch the first profile agent.
It must route the failure through exactly one deterministic branch.

`NEXT_ACTION.md` must contain exactly one action. It must not contain alternative
`ACTION_TYPE`, `TARGET_ROLE`, or `DEPENDENCY_STATUS` values.

If validation fails because owner-provided bootstrap input is missing or inaccessible,
the orchestrator must set:

```text
ACTION_TYPE: wait_for_owner
TARGET_ROLE: project_owner
DEPENDENCY_STATUS: blocked
BLOCKED_BY: missing_bootstrap_input
```

If validation fails because a required `agent-system/` package, runtime,
template, or governance file is missing, inaccessible, malformed, or internally
invalid, the orchestrator must set:

```text
ACTION_TYPE: correction
TARGET_ROLE: orchestrator
DEPENDENCY_STATUS: blocked
BLOCKED_BY: invalid_or_missing_package_file
```

If validation fails because runtime file creation, runtime schema validation,
template parity validation, governance validation, `NEXT_ACTION.md` validation,
or governance freeze state validation failed after required package files were
available,
the orchestrator must set:

```text
ACTION_TYPE: correction
TARGET_ROLE: orchestrator
DEPENDENCY_STATUS: blocked
BLOCKED_BY: invalid_bootstrap_state
```

The first profile-agent dispatch remains forbidden until bootstrap validation passes.

---

## Ограничение

Оркестратор не обязан глубоко читать ТЗ проекта.

Он передаёт ТЗ первому profile-агенту как входной документ.

Оркестратор может открыть ТЗ только для:
- проверки существования файла;
- проверки корректности пути;
- проверки доступности файла для передачи агенту;
- проверки наличия явных разделов, достаточных только для выбора маршрута
  `requirements_analyst` или `designer`.

Оркестратору запрещено:
- анализировать бизнес-логику ТЗ;
- проектировать решение;
- интерпретировать требования;
- додумывать недостающие части ТЗ;
- разрешать неоднозначные требования;
- декомпозировать реализацию проекта.
