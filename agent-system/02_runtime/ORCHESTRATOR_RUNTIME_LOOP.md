# ORCHESTRATOR_RUNTIME_LOOP

## Назначение

Этот файл должен перечитываться оркестратором перед каждым новым действием.

Цель — не позволять оркестратору полагаться на накопленный контекст.

## Runtime loop

Перед каждым новым действием оркестратор обязан выполнить цикл:

1. Перечитать:
   - `agent-system/01_roles/ORCHESTRATOR.md`
   - `agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md`
   - `agent-system/02_runtime/ALLOWED_ORCHESTRATOR_ACTIONS.md`
   - `agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md`
   - `agent-system/04_state/RUNTIME_STATE_SCHEMA.md`
   - `project-runtime/PROJECT_STATE.md`
   - `project-runtime/CURRENT_GATE.md`
   - `project-runtime/NEXT_ACTION.md`
   - `project-runtime/GAP_REGISTER.md`


2. Определить следующий шаг только из `NEXT_ACTION.md`.

3. Проверить, что действие входит в whitelist из `ALLOWED_ORCHESTRATOR_ACTIONS.md`.

4. Проверить filesystem governance.

Оркестратор обязан проверить, что task packet:

- соответствует `TASK_PACKET_TEMPLATE.md`;
- содержит обязательные секции;
- не нарушает mandatory workflow;
- не нарушает filesystem governance.

Оркестратор обязан сверить planned action с:

- `ACTIVE_DOC_ROOT`;
- разрешёнными зонами изменения файлов для роли;
- запретом на использование `project-archive/` как active source;
- запретом на изменение `project-runtime/` обычными агентами;
- запретом на изменение `agent-system/` обычными агентами;
- правилом, что task packets должны находиться внутри `ACTIVE_DOC_ROOT`.

Если planned action нарушает filesystem governance:
- dispatch агента запрещён;
- pipeline переводится в workflow violation;
- `NEXT_ACTION` должен быть остановлен;
- требуется correction flow.

5. Проверить runtime state schema.

Оркестратор обязан проверить, что:
- runtime state соответствует `RUNTIME_STATE_SCHEMA.md`;
- обязательные runtime files существуют;
- обязательные поля присутствуют;
- workflow transitions не нарушены;
- runtime state не содержит deprecated references;
- terminal state не выставлен преждевременно.

Если runtime state нарушает schema:
- dispatch новых агентов запрещён;
- pipeline переводится в correction flow;
- `CURRENT_PHASE` должен быть `correction`;
- `PROJECT_STATUS` должен быть `blocked`.

6. Проверить mandatory workflow transitions.

Оркестратор обязан валидировать:

designer → auditor
developer → auditor
tester(pass) → technical_writer (если required)
tester(fail) → developer
tester(blocked) → orchestrator
tester(gap) → orchestrator

Если RESULT агента нарушает mandatory workflow:

- pipeline нельзя продолжать;
- runtime state должен быть переведён в workflow violation;
- dispatch следующего агента запрещён;
- violation должен быть возвращён на correction flow.

7. Проверить routing blocked/gap issues.

Если blocked/gap относится к:

- runtime environment;
- deployment behavior;
- runtime configuration;
- portability;
- infrastructure/runtime mismatch;
- technical execution environment;

и проблема не требует business decision owner-а,

оркестратор обязан:

- маршрутизировать issue проектировщику;
- не переводить pipeline в wait_for_owner.

8. Если следующий шаг требует агента:
   - создать нового агента;
   - назначить ровно одну задачу;
   - передать универсальные инструкции роли;
   - передать только REQUIRED_DOCS из task packet;
   - передать шаблон результата.

9. Дождаться RESULT от агента.

10. Проверить только формальную корректность RESULT:
   - есть `STATUS`;
   - есть `ROLE`;
   - есть `TASK`;
   - есть `CHANGED_FILES` или указано `NONE`;
   - есть `EVIDENCE`;
   - есть `RISKS`;
   - есть `NEXT_REQUIRED_ACTION`.

11. Действовать по STATUS:
   - `pass` → перейти к следующему gate;
   - `fail` → вернуть задачу на исправление профильному агенту;
   - `blocked` → зафиксировать блокер;
   - `gap` → зафиксировать GAP и остановить зависимую ветку.

12. Обновить runtime state:
   - `PROJECT_STATE.md`
   - `CURRENT_GATE.md`
   - `NEXT_ACTION.md`
   - при необходимости `GAP_REGISTER.md`

13. Повторить цикл перед следующим действием.

## Запрет

Оркестратор не имеет права продолжать работу на основании памяти, если runtime-файлы не перечитаны.
