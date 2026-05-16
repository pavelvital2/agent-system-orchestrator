# ORCHESTRATOR_RUNTIME_LOOP

## Назначение

Этот файл должен перечитываться оркестратором перед каждым новым действием.

Цель — не позволять оркестратору полагаться на накопленный контекст.

## Runtime loop

Перед каждым новым действием оркестратор обязан выполнить цикл:

1. Перечитать:
   - `agent-system/01_roles/ORCHESTRATOR.md`
   - `agent-system/PACKAGE_VERSIONING.md`
   - `agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md`
   - `agent-system/02_runtime/ALLOWED_ORCHESTRATOR_ACTIONS.md`
   - `agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md`
   - `agent-system/02_runtime/GOVERNANCE_AUTHORITY.md`
   - `agent-system/02_runtime/ACTION_STATE_SEMANTICS.md`
   - `agent-system/02_runtime/STATE_TRANSITION_RULES.md`
   - `agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md`
   - `agent-system/02_runtime/VIOLATION_RECOVERY.md`
   - `agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md`
   - `agent-system/02_runtime/AGENT_LIFECYCLE.md`
   - `agent-system/03_templates/TASK_PACKET_TEMPLATE.md`
   - `agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md`
   - `agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md`
   - `agent-system/03_templates/AGENT_RESULT_TEMPLATE.md`
   - `agent-system/04_state/RUNTIME_STATE_SCHEMA.md`
   - `agent-system/05_gap_flow/GAP_FLOW.md`
   - `agent-system/05_gap_flow/GAP_REGISTER_TEMPLATE.md`
   - `agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md`
   - `agent-system/06_logs/ORCHESTRATOR_EVENTS_LOG_TEMPLATE.md`
   - `agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md`
   - `project-runtime/PROJECT_STATE.md`
   - `project-runtime/CURRENT_GATE.md`
   - `project-runtime/NEXT_ACTION.md`
   - `project-runtime/GAP_REGISTER.md`
   - `project-runtime/AGENT_RESULTS_LOG.md`
   - `project-runtime/TASK_REGISTRY.md`
   - `project-runtime/ACCEPTED_ARTIFACTS.md`
   - `project-runtime/ORCHESTRATOR_EVENTS_LOG.md`
   - `project-runtime/STATUS_SUMMARY.md`


2. Определить следующий шаг только из `NEXT_ACTION.md`.

3. Проверить, что действие входит в whitelist из `ALLOWED_ORCHESTRATOR_ACTIONS.md`.

4. Проверить filesystem governance.

Оркестратор обязан определить, требуется ли task-packet validation.

Task-packet validation применяется только если:

- `NEXT_ACTION.ACTION_TYPE` равен `create_agent`;
- или `NEXT_ACTION.TASK_PACKET` не равен `NONE`;
- или planned action явно ссылается на task packet.

Если task-packet validation требуется, оркестратор обязан проверить, что task packet:

- соответствует `TASK_PACKET_TEMPLATE.md`;
- содержит обязательные секции;
- не нарушает mandatory workflow;
- не нарушает filesystem governance.

Для `wait_for_owner`, `update_state`, `finalize`, `stop` и `correction` без task packet значение `TASK_PACKET: NONE` допустимо, если full runtime state tuple разрешён `STATE_TRANSITION_RULES.md`.

Оркестратор не должен считать `TASK_PACKET: NONE` отсутствующим task packet для таких non-dispatch actions.

Любой profile-agent `create_agent` всегда требует валидный task packet.
Для первого profile-agent dispatch этот packet должен быть валидным bootstrap
task packet, созданным по:

```text
agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
```

Canonical first-dispatch path convention:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

`TASK_PACKET: NONE` is forbidden for first profile-agent dispatch. A bootstrap
handoff file is not a task packet substitute unless it is explicitly full
task-packet-equivalent and satisfies bootstrap task packet validation.

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

profile_agent(pass) → auditor when `AUDIT_REQUIREMENTS` makes audit mandatory
requirements_analyst(pass) → auditor when audit mandatory
designer(pass) → auditor when audit mandatory
developer(pass) → auditor when audit mandatory
tester(pass) → auditor when audit mandatory
technical_writer(pass) → auditor when audit mandatory
devops_setup_engineer(pass) → auditor when audit mandatory
release_manager(pass) → auditor when audit mandatory
tester(pass) → technical_writer (если required)
tester(fail) → developer
tester(blocked) → orchestrator
tester(gap) → orchestrator

When audit is mandatory, a profile-agent `STATUS: pass` must not route directly
to another profile role, another lifecycle phase, terminal completion, or Git
checkpoint. It must route to an auditor first. The post-audit Git checkpoint is
allowed only after auditor `STATUS: pass`.

Если RESULT агента нарушает mandatory workflow:

- pipeline нельзя продолжать;
- runtime state должен быть переведён в workflow violation;
- dispatch следующего агента запрещён;
- violation должен быть возвращён на correction flow.

Оркестратор обязан применять `ACTION_STATE_SEMANTICS.md` при различении:

- `wait_for_owner`;
- `pause`;
- `stop_terminal`;
- `completed`.

Если текущий `NEXT_ACTION` использует `stop` как временную паузу, dispatch запрещён и runtime state должен быть переведён в correction.

Если auditor RESULT имеет `STATUS: fail`, оркестратор обязан:

- запретить normal next task dispatch;
- запретить post-audit Git checkpoint;
- заблокировать зависимые ветки;
- route только в correction, governed update_state, or genuine wait_for_owner.

Если auditor RESULT имеет `STATUS: blocked` or `STATUS: gap`, оркестратор обязан:

- запретить normal next task dispatch;
- запретить post-audit Git checkpoint;
- заблокировать зависимые ветки;
- route only according to blocked/GAP governance.

Если auditor RESULT имеет `STATUS: pass`, оркестратор обязан:

- route first to `POST_AUDIT_GIT_CHECKPOINT.md`;
- validate `GIT_CHECKPOINT_VALIDATION_RULES.md` before staging;
- stage only accepted files allowed by the audited task packet;
- commit only after checkpoint validation passes;
- push only after a valid local commit exists;
- record branch, commit hash, push status, and accepted files;
- route to the next governed task only after successful checkpoint completion.

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
   - есть `SUMMARY`;
   - есть `READ_DOCS`;
   - есть `READ_INPUTS`;
   - есть `CHANGED_FILES` или указано `NONE`;
   - есть `CREATED_FILES`;
   - есть `DELETED_FILES`;
   - есть `COMMANDS_RUN`;
   - есть `EVIDENCE`;
   - есть `SCOPE_VERIFICATION`;
   - есть `FORBIDDEN_CHANGES_CHECK`;
   - есть `RISKS`;
   - есть `BLOCKERS`;
   - есть `GAPS`;
   - есть `NEXT_RECOMMENDED_ACTION`.

Формальная проверка RESULT должна требовать ровно обязательные поля из `AGENT_RESULT_TEMPLATE.md`:

```text
STATUS
ROLE
TASK
SUMMARY
READ_DOCS
READ_INPUTS
CHANGED_FILES
CREATED_FILES
DELETED_FILES
COMMANDS_RUN
EVIDENCE
SCOPE_VERIFICATION
FORBIDDEN_CHANGES_CHECK
RISKS
BLOCKERS
GAPS
NEXT_RECOMMENDED_ACTION
```

`NEXT_RECOMMENDED_ACTION` is an advisory profile-agent recommendation, not an
authoritative routing decision. Before acting on it, the orchestrator must
validate runtime state, task registry, current gate, transition rules, blockers,
and accepted artifacts.

Допустимые profile-agent `STATUS` values:

```text
pass
fail
blocked
gap
```

`violation` не является допустимым profile-agent RESULT `STATUS`.

`violation` является orchestrator-derived recovery/logging category для governance, workflow, filesystem, runtime-state или formally invalid RESULT handling.

Если RESULT format invalid, включая отсутствующие обязательные поля или недопустимый `STATUS`, оркестратор не имеет права route by status. Он должен зафиксировать orchestrator-classified `violation` log entry и перейти к governed correction/reformat согласно `VIOLATION_RECOVERY.md`.

11. Зафиксировать RESULT перед routing by STATUS.

После формальной проверки RESULT и до любого действия по `STATUS` оркестратор обязан:

- сохранить полный RESULT или получить deterministic `RESULT_REF`, по которому полный RESULT доступен;
- добавить bounded entry в `project-runtime/AGENT_RESULTS_LOG.md`;
- указать в entry поля `DATE`, `ROLE`, `TASK`, `STATUS`, `RESULT_REF`, `CHANGED_FILES`, `NEXT_RECOMMENDED_ACTION`;
- применить это правило для valid profile-agent `pass`, `fail`, `blocked`, `gap` results и для orchestrator-classified `violation` log entries.

Recovery/status routing запрещён, пока `AGENT_RESULTS_LOG.md` не получил bounded entry или deterministic reference на полный RESULT.

Если RESULT format invalid, violation/reformat routing также запрещён до bounded log entry или deterministic reference.

Для formally invalid RESULT bounded log entry должен быть заполнен детерминированно и без semantic inference of agent intent:

```text
DATE: current runtime date if available, otherwise UNKNOWN
ROLE: from handoff TARGET_ROLE, otherwise unknown
TASK: current NEXT_ACTION.TASK_ID, otherwise unknown
STATUS: violation
RESULT_REF: raw invalid RESULT reference
CHANGED_FILES: unknown unless safely extractable
NEXT_RECOMMENDED_ACTION: correction
```

12. Действовать по STATUS:
   - profile-agent `pass` with mandatory audit → перейти к обязательному audit gate;
   - profile-agent `pass` without mandatory audit → route only by validated task packet, task registry, and transition rules;
   - auditor `pass` → выполнить post-audit Git checkpoint, then перейти к следующему governed gate;
   - `fail` → вернуть задачу на исправление профильному агенту;
   - `blocked` → зафиксировать блокер;
   - `gap` → зафиксировать GAP и остановить зависимую ветку.

13. Обновить runtime state:
   - `PROJECT_STATE.md`
   - `CURRENT_GATE.md`
   - `NEXT_ACTION.md`
   - `AGENT_RESULTS_LOG.md` для каждого agent result
   - `TASK_REGISTRY.md` для task lifecycle state
   - `ACCEPTED_ARTIFACTS.md` для accepted artifact state
   - `ORCHESTRATOR_EVENTS_LOG.md` для material orchestrator events
   - `STATUS_SUMMARY.md` для compact status summary
   - при необходимости `GAP_REGISTER.md`

14. Повторить цикл перед следующим действием.

## Mandatory validation order

Before any `create_agent`, `route_result`, `update_state`, `correction`, `finalize`, or `stop` action, the orchestrator must validate in this order:

1. universal package files exist;
2. package version / governance ruleset / runtime schema are compatible;
3. mandatory runtime files exist;
4. runtime state matches `RUNTIME_STATE_SCHEMA.md`;
5. full runtime state tuple is valid under `STATE_TRANSITION_RULES.md`;
6. action/state semantics are valid under `ACTION_STATE_SEMANTICS.md`;
7. `NEXT_ACTION.md` contains exactly one action;
8. `NEXT_ACTION.md` does not conflict with `GOVERNANCE_AUTHORITY.md`;
9. if `NEXT_ACTION.ACTION_TYPE` is `create_agent` or `NEXT_ACTION.TASK_PACKET` is not `NONE`, target task packet is active, not superseded, not deprecated;
10. if task-packet validation is required, target task packet is inside `ACTIVE_DOC_ROOT` unless it is explicitly governed as system/bootstrap/package correction material;
11. if task-packet validation is required, REQUIRED_DOCS do not include deprecated/archive documents;
12. if task-packet validation is not required, `TASK_PACKET: NONE` is valid only for `wait_for_owner`, `update_state`, `finalize`, `stop`, or `correction` when allowed by `STATE_TRANSITION_RULES.md`;
13. role/file permissions match `FILESYSTEM_GOVERNANCE.md`;
14. requested action is valid under governance-freeze rules.

If any validation fails, dispatch is forbidden.

Freeze absence is not a required validation condition for recovery actions.

Instead, when governance freeze is active, the orchestrator must validate that `NEXT_ACTION.ACTION_TYPE` is freeze-safe:

- `correction`;
- `wait_for_owner`;
- governed `update_state`;
- governed `stop` when stop invariants allow it;
- `create_agent` only for an explicitly bounded package-governance correction task when permitted by `STATE_TRANSITION_RULES.md`.

Normal project `create_agent`, `route_result`, and `finalize` actions are not freeze-safe.

A `create_agent` action during governance freeze is allowed only when it dispatches an explicitly bounded package-governance correction task and passes task-packet, filesystem, lifecycle, and transition validation.

## Governance freeze behavior

If governance freeze is active:

```text
PROJECT_STATUS: blocked
CURRENT_PHASE: correction | blocked
NEXT_ACTION.ACTION_TYPE: correction | wait_for_owner | update_state | stop | create_agent
```

During governance freeze, normal project `create_agent` dispatch is forbidden.

The orchestrator may only:

- enter correction flow;
- update runtime state into correction/wait/stop through governed `update_state`;
- request owner input;
- dispatch an explicitly bounded package-governance correction task through `create_agent` when transition rules permit it;
- stop through governed `stop` when stop invariants allow it;
- reread and revalidate runtime files.

## Post-update validation

After updating any runtime state file, the orchestrator must reread:

- `PROJECT_STATE.md`
- `CURRENT_GATE.md`
- `NEXT_ACTION.md`
- `GAP_REGISTER.md`
- `AGENT_RESULTS_LOG.md`
- `TASK_REGISTRY.md`
- `ACCEPTED_ARTIFACTS.md`
- `ORCHESTRATOR_EVENTS_LOG.md`
- `STATUS_SUMMARY.md`

Then it must validate the updated runtime state tuple before the next dispatch.

The orchestrator must not continue from memory after writing runtime state.

## Запрет

Оркестратор не имеет права продолжать работу на основании памяти, если runtime-файлы не перечитаны.
