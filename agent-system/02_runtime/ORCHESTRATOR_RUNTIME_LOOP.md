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
   - `agent-system/02_runtime/REQUESTER_RETURN_PROTOCOL.md`
   - `agent-system/02_runtime/ACTION_STATE_SEMANTICS.md`
   - `agent-system/02_runtime/STATE_TRANSITION_RULES.md`
   - `agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md`
   - `agent-system/02_runtime/VIOLATION_RECOVERY.md`
   - `agent-system/02_runtime/INCIDENT_RECOVERY.md`
   - `agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md`
   - `agent-system/02_runtime/AGENT_LIFECYCLE.md`
   - `agent-system/03_templates/TASK_PACKET_TEMPLATE.md`
   - `agent-system/03_templates/TASK_PROPOSAL_TEMPLATE.md`
   - `agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md`
   - `agent-system/03_templates/RESEARCH_REQUEST_TEMPLATE.md`
   - `agent-system/03_templates/RESEARCH_RESULT_TEMPLATE.md`
   - `agent-system/03_templates/DESIGN_CONTINUATION_TASK_TEMPLATE.md`
   - `agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md`
   - `agent-system/03_templates/WORKSPACE_IDENTITY_TEMPLATE.md`
   - `agent-system/03_templates/REPOSITORY_LOCK_TEMPLATE.md`
   - `agent-system/03_templates/CHECKPOINT_ELIGIBILITY_TEMPLATE.md`
   - `agent-system/03_templates/AGENT_RESULT_TEMPLATE.md`
   - `agent-system/04_state/RUNTIME_STATE_SCHEMA.md`
   - `agent-system/05_gap_flow/GAP_FLOW.md`
   - `agent-system/05_gap_flow/GAP_REGISTER_TEMPLATE.md`
   - `agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md`
   - `agent-system/06_logs/ORCHESTRATOR_EVENTS_LOG_TEMPLATE.md`
   - `agent-system/09_validators/WORKSPACE_IDENTITY_VALIDATION_RULES.md`
   - `agent-system/09_validators/TASK_PACKET_SCHEMA_VALIDATION_RULES.md`
   - `agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md`
   - `agent-system/09_validators/CHANGED_FILES_SCOPE_MATRIX.md`
   - `agent-system/09_validators/SECRET_SCAN_RULES.md`
   - `agent-system/09_validators/RESEARCH_RETURN_VALIDATION_RULES.md`
   - `agent-system/09_validators/REASONING_LEVEL_VALIDATION_RULES.md`
   - `agent-system/scripts/checkpoint_preflight.sh`
   - `agent-system/scripts/validate_task_packet.py`
   - `project-runtime/PROJECT_STATE.md`
   - `project-runtime/CURRENT_GATE.md`
   - `project-runtime/NEXT_ACTION.md`
   - `project-runtime/GAP_REGISTER.md`
   - `project-runtime/AGENT_RESULTS_LOG.md`
   - `project-runtime/TASK_REGISTRY.md`
   - `project-runtime/ACCEPTED_ARTIFACTS.md`
   - `project-runtime/ORCHESTRATOR_EVENTS_LOG.md`
   - `project-runtime/STATUS_SUMMARY.md`

Before trusting `NEXT_ACTION.md` for dispatch or checkpoint routing, the
orchestrator must run the workspace identity gate from:

```text
agent-system/09_validators/WORKSPACE_IDENTITY_VALIDATION_RULES.md
```

The gate must validate `PROJECT_NAME`, `PROJECT_SLUG`, `WORKSPACE_TYPE`,
`PROJECT_ROOT_EXPECTED`, `GIT_TOPLEVEL_ACTUAL`, `EXPECTED_REMOTE`,
`ACTUAL_REMOTE`, `EXPECTED_GIT_REMOTE`, `ACTUAL_GIT_REMOTE`,
`EXPECTED_BRANCH`, `ACTUAL_BRANCH`, and `PUSH_ALLOWED`.

The gate compares canonical repository identity, not raw remote strings.
Accepted equivalent raw remote forms are:

```text
https://github.com/OWNER/REPO
https://github.com/OWNER/REPO.git
github.com/OWNER/REPO
git@github.com:OWNER/REPO.git
git@<approved_ssh_host_alias>:OWNER/REPO.git
```

The SSH host alias form is valid only when the alias is explicitly accepted in
the repository lock or bounded evidence proves it resolves to `github.com`.

If the gate returns `repository_identity_mismatch`,
`repository_branch_mismatch`, `workspace_identity_leakage`,
`unapproved_ssh_host_alias`, `repository_lock_missing`, or
`push_without_repository_lock`, then profile-agent dispatch, checkpoint, commit,
and push are forbidden. Commit may proceed only as a governed local-only
checkpoint when the repository lock and active task packet explicitly permit
that exception.

For a new project workspace, runtime initialization must start from a safe
package-to-project workspace procedure:

```text
agent-system/scripts/init_project_workspace.sh
```

or an equivalent governed procedure that explicitly excludes `.git`, rejects
clone-renamed package checkouts, requires expected remote and branch inputs
before repository lock acceptance, blocks mismatched existing target `.git`
remote or branch, and creates or requires `WORKSPACE_IDENTITY` and
`REPOSITORY_LOCK` records.


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
- проходит `TASK_PACKET_SCHEMA_VALIDATION_RULES.md` или
  `agent-system/scripts/validate_task_packet.py`;
- содержит обязательные секции;
- не нарушает mandatory workflow;
- не нарушает filesystem governance.

`TASK_PROPOSAL` files are not dispatchable task packets. A proposal may be used
only as non-dispatchable planning input and must conform to:

```text
agent-system/03_templates/TASK_PROPOSAL_TEMPLATE.md
```

If `NEXT_ACTION.ACTION_TYPE: create_agent` references a `TASK_PROPOSAL`, a file
without `# TASK PACKET`, or a malformed task packet, dispatch is forbidden and
the route must enter governed correction with:

```text
invalid_task_packet_schema
```

Для `wait_for_owner`, `update_state`, `finalize`, `stop` и `correction` без task packet значение `TASK_PACKET: NONE` допустимо, если full runtime state tuple разрешён `STATE_TRANSITION_RULES.md`.

`TASK_PACKET_NONE_FILE_CHANGES_FORBIDDEN`: `TASK_PACKET: NONE` is forbidden for
file-changing corrections. It is allowed only for pure coordination or
orchestrator-owned runtime operations that do not change project, package,
implementation, task-packet, profile-result, or other non-runtime artifacts.
Any correction that creates, edits, deletes, restores, reverts, redacts, or
replaces files outside orchestrator-owned runtime state requires a full
correction task packet.

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

The `<TARGET_ROLE>` segment is mandatory. Any blank-role bootstrap placeholder
in current package docs, runtime state, task packets, or checkpointed content is
invalid and must route to governed correction before dispatch or push.

The first profile-agent `NEXT_ACTION` must still include every required field
from `agent-system/04_state/NEXT_ACTION_TEMPLATE.md`; for ordinary bootstrap
dispatch, requester-return and blocking/resume contexts are `NONE`.

`TASK_PACKET: NONE` is forbidden for first profile-agent dispatch. A bootstrap
handoff file is not a task packet substitute unless it is explicitly full
task-packet-equivalent and satisfies bootstrap task packet validation.

Оркестратор обязан сверить planned action с:

- `ACTIVE_DOC_ROOT`;
- разрешёнными зонами изменения файлов для роли;
- запретом на использование `project-archive/` как active source;
- запретом на изменение `project-runtime/` обычными агентами;
- запретом на изменение `agent-system/` обычными агентами;
- правилом, что task packets должны находиться внутри `ACTIVE_DOC_ROOT`, кроме
  единственного первого bootstrap task packet:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

The bootstrap exception is valid only when the role segment is populated by the
selected first profile route.

Ordinary task packets outside `ACTIVE_DOC_ROOT` remain invalid.

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
solution_architect(pass) → auditor when audit mandatory
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
- treat auditor pass as necessary but not sufficient for commit or push;
- verify the auditor RESULT includes explicit passing evidence statuses for
  changed files scope, task packet schema, repository identity, forbidden
  paths, runtime mutation, required evidence, secret exposure, and
  reasoning-level compliance;
- require these audit evidence labels before accepting auditor pass:

```text
CHANGED_FILES_SCOPE_STATUS
TASK_PACKET_SCHEMA_STATUS
REPOSITORY_IDENTITY_STATUS
FORBIDDEN_PATH_STATUS
RUNTIME_MUTATION_STATUS
EVIDENCE_STATUS
SECRET_EXPOSURE_STATUS
REASONING_LEVEL_COMPLIANCE
```

- when changed task-like files include `TASK_*.md`, `TASK_PROPOSAL*.md`, or
  `*_TASK_PACKET*.md`, require `VALIDATED_TASK_PACKETS` evidence listing each
  validated file, classification, and `TASK_PACKET_SCHEMA_STATUS`;
- treat a missing, failed, blocked, unknown, contradicted, or
  `potential_secret_exposure` audit status as invalid audit acceptance;
- before accepting design output that created or changed downstream task-like
  artifacts, verify the audit includes downstream task validation evidence for
  changed `TASK_*.md`, `TASK_PROPOSAL*.md`, and `*_TASK_PACKET*.md` files;
- treat invalid, ambiguous, or unvalidated downstream dispatchable task packets
  as blockers for audit acceptance, checkpoint, staging, commit, and push;
- run deterministic checkpoint preflight before staging;
- validate `GIT_CHECKPOINT_VALIDATION_RULES.md`,
  `CHANGED_FILES_SCOPE_MATRIX.md`, and `SECRET_SCAN_RULES.md`;
- record `CHECKPOINT_ELIGIBILITY_STATUS` in a checkpoint eligibility receipt;
- stage only accepted files allowed by the audited task packet;
- commit only after checkpoint validation passes;
- push only after a valid local commit exists;
- record branch, commit hash, commit status, push status, push remote/branch,
  `LAST_PUSH_TARGET_STATUS`, `PROJECT_CHECKPOINT_STATUS`, and accepted files;
- route to the next governed task only after successful checkpoint completion.

If checkpoint preflight finds a blocker after auditor `STATUS: pass` and the
blocker belongs to a check the auditor was required to perform, the
orchestrator must record:

```text
AUDIT_FALSE_PASS_DETECTED
FAILURE_TYPE: audit_miss
```

In that case staging, commit, push, and normal next-task dispatch are
forbidden. The orchestrator must route only to governed correction, blocked
handling, GAP handling, or genuine owner handling as permitted by the runtime
tuple. File-changing correction for `audit_miss` requires a full correction task
packet and its own independent audit before checkpoint can be attempted again.

If the audited task has `TASK_KIND: research_dependency` and
`RETURN_TO_REQUESTER_AFTER_AUDIT_PASS: yes`, the next governed task after audit
pass and any required checkpoint must be the exact requester continuation
encoded by:

```text
RETURN_TO_ROLE_AFTER_AUDIT_PASS
RETURN_TASK_AFTER_AUDIT_PASS
```

The orchestrator must not infer requester return targets from memory or
informal context.

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
   - before spawning a profile agent, resolve dispatch reasoning:
     `role_default_reasoning_level`, `task_packet_reasoning_level`,
     `gate_required_floor`, `final_required_dispatch_level`, and
     `requested_or_configured_reasoning_level` with
     `runner_config_evidence`;
   - compute `final_required_dispatch_level` as the highest applicable level
     among role default, task packet `REASONING_LEVEL`, and gate-required
     floor, using `low < medium < high < xhigh`;
   - record `TARGET_ROLE`, `TASK_ID`, `TASK_PACKET`,
     `REASONING_LEVEL_REQUIRED`, `REASONING_LEVEL_SOURCE`,
     `REASONING_LEVEL_RESOLVED`, `RUNNER_CONFIG_EVIDENCE`,
     `REASONING_LEVEL_COMPLIANCE`, and
     `SPAWN_LOG_REF` or `HANDOFF_LOG_REF` in the handoff, spawn log, or
     orchestrator transcript before RESULT routing;
   - do not claim knowledge of the profile agent's internal actual reasoning
     level unless the runner provides verifiable evidence;
   - if the requested or configured runner reasoning level is below required,
     classify the spawn as invalid dispatch: the worker RESULT is invalid,
     audit must fail or block, post-audit checkpoint is forbidden, commit/push
     are forbidden, and routing must enter governed correction;
   - создать нового агента;
   - назначить ровно одну задачу;
   - передать универсальные инструкции роли;
   - передать только REQUIRED_DOCS из task packet;
   - передать шаблон результата.

9. Дождаться RESULT от агента.

10. Проверить только формальную корректность RESULT:
   - есть `STATUS`;
   - есть `TASK_ID`;
   - есть `AGENT_INSTANCE_ID`;
   - есть `ROLE`;
   - есть `TASK`;
   - есть `SUMMARY`;
   - есть `READ_DOCS`;
   - есть `READ_INPUTS`;
   - есть `CHANGED_FILES` или указано `NONE`;
   - есть `CREATED_FILES`;
   - есть `DELETED_FILES`;
   - есть `COMMANDS_RUN`;
   - есть `TESTS_RUN`;
   - есть `EVIDENCE`;
   - есть `SCOPE_VERIFICATION`;
   - есть `FORBIDDEN_CHANGES_CHECK`;
   - есть `RISKS`;
   - есть `LIMITATIONS`;
   - есть `BLOCKERS`;
   - есть `GAPS`;
   - есть `NEXT_RECOMMENDED_ACTION`;
   - есть `REUSE_ALLOWED: false`;
   - есть `AGENT_TERMINATION_REQUIRED: true`.

Формальная проверка RESULT должна требовать ровно обязательные поля из `AGENT_RESULT_TEMPLATE.md`:

```text
STATUS
TASK_ID
AGENT_INSTANCE_ID
ROLE
TASK
SUMMARY
READ_DOCS
READ_INPUTS
CHANGED_FILES
CREATED_FILES
DELETED_FILES
COMMANDS_RUN
TESTS_RUN
EVIDENCE
SCOPE_VERIFICATION
FORBIDDEN_CHANGES_CHECK
RISKS
LIMITATIONS
BLOCKERS
GAPS
NEXT_RECOMMENDED_ACTION
REUSE_ALLOWED
AGENT_TERMINATION_REQUIRED
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
   - auditor `pass` → выполнить post-audit checkpoint eligibility preflight and, only if eligible, Git checkpoint, then перейти к следующему governed gate;
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

Before any `create_agent`, `route_result`, `update_state`, `correction`,
`finalize`, or `stop` action, and before any post-audit checkpoint, commit, or
push, the orchestrator must validate in this order:

1. universal package files exist;
2. package version / governance ruleset / runtime schema are compatible;
3. mandatory runtime files exist;
4. workspace identity and repository lock fields exist in runtime state or
   initialization material;
5. workspace identity gate passes under
   `WORKSPACE_IDENTITY_VALIDATION_RULES.md`;
6. canonical `EXPECTED_GIT_REMOTE` and `ACTUAL_GIT_REMOTE` match, using
   approved SSH alias evidence when an alias is present;
7. actual remote, branch, and toplevel are read from live Git commands for real
   repository checks, not trusted from cached runtime `ACTUAL_*` fields;
8. `EXPECTED_BRANCH` and live actual branch match;
9. critical baseline paths are tracked before first profile-agent dispatch and
   before first accepted checkpoint, unless explicit owner policy records the
   allowed exception;
10. `PUSH_ALLOWED` is false unless an accepted repository lock authorizes the
   current workspace type, canonical repository identity, branch, and
   checkpoint policy;
11. runtime state matches `RUNTIME_STATE_SCHEMA.md`;
12. full runtime state tuple is valid under `STATE_TRANSITION_RULES.md`;
13. action/state semantics are valid under `ACTION_STATE_SEMANTICS.md`;
14. `NEXT_ACTION.md` contains exactly one action;
15. `NEXT_ACTION.md` does not conflict with `GOVERNANCE_AUTHORITY.md`;
16. if `NEXT_ACTION.ACTION_TYPE` is `create_agent` or `NEXT_ACTION.TASK_PACKET` is not `NONE`, target task artifact declares `# TASK PACKET`, not `# TASK PROPOSAL`, and passes `TASK_PACKET_SCHEMA_VALIDATION_RULES.md`;
17. if `NEXT_ACTION.ACTION_TYPE` is `create_agent` or `NEXT_ACTION.TASK_PACKET` is not `NONE`, target task packet is active, not superseded, not deprecated;
18. if task-packet validation is required, target task packet is inside `ACTIVE_DOC_ROOT` unless it is the governed first bootstrap task packet at `project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md` or explicitly governed as system/package correction material;
19. if task-packet validation is required, REQUIRED_DOCS do not include deprecated/archive documents;
20. if task-packet validation is not required, `TASK_PACKET: NONE` is valid only for `wait_for_owner`, `update_state`, `finalize`, `stop`, or `correction` when allowed by `STATE_TRANSITION_RULES.md`;
20a. if `TASK_PACKET: NONE` is present, enforce
    `TASK_PACKET_NONE_FILE_CHANGES_FORBIDDEN` from
    `INCIDENT_RECOVERY.md`: no file-changing correction may proceed without a
    full correction task packet;
20b. if `TASK_PACKET: NONE` is paired with `TARGET_ROLE: orchestrator`, enforce
     `orchestrator_task_packet_none_project_artifact_route_forbidden`;
21. role/file permissions match `FILESYSTEM_GOVERNANCE.md`;
22. task packet `REASONING_LEVEL` is valid for allowed values, role default,
    and gate-required floor;
23. profile-agent dispatch reasoning is resolved and prepared for recording:
    `role_default_reasoning_level`, `task_packet_reasoning_level`,
    `gate_required_floor`, `final_required_dispatch_level`, and
    `requested_or_configured_reasoning_level` with
    `runner_config_evidence`; `final_required_dispatch_level` must be the
    highest applicable level among role default, task packet `REASONING_LEVEL`,
    and gate-required floor, using `low < medium < high < xhigh`; runner
    compliance must be based on runner configuration evidence, and the runtime
    must not claim internal actual reasoning unless runner evidence exists;
22. `TASK_KIND: research_dependency` and requester continuation routing are
    valid under `REQUESTER_RETURN_PROTOCOL.md`;
23. for design audit acceptance, changed downstream task-like artifacts are
    explicitly classified as dispatchable `TASK_PACKET` or non-dispatchable
    `TASK_PROPOSAL`; every changed dispatchable downstream `TASK_*.md` file
    passes task packet schema validation before auditor pass is accepted; and
    non-dispatchable proposals are not selected by `NEXT_ACTION.TASK_PACKET`;
24. before accepting auditor pass, the auditor RESULT includes explicit
    evidence statuses for changed file scope, task packet schema, repository
    identity, forbidden paths, runtime mutation, required evidence, secret
    exposure, and reasoning-level compliance;
25. when changed task-like files include `TASK_*.md`,
    `TASK_PROPOSAL*.md`, or `*_TASK_PACKET*.md`, the auditor RESULT lists
    `VALIDATED_TASK_PACKETS` with each path, classification, dispatchability,
    and `TASK_PACKET_SCHEMA_STATUS`;
26. before checkpoint, commit, or push, deterministic checkpoint preflight has
    run and produced `CHECKPOINT_ELIGIBILITY_STATUS: eligible` in a receipt
    based on `CHECKPOINT_ELIGIBILITY_TEMPLATE.md`;
27. checkpoint preflight covers workspace identity, Git target, changed file
    scope, task packet schema, runtime schema, and secret/sensitive artifact
    scan;
28. checkpoint preflight validates changed dispatchable task packets and
    non-dispatchable `TASK_PROPOSAL` files before `git add`; any
    `invalid_task_packet_schema` result blocks staging, commit, and push;
29. if checkpoint preflight detects a blocker after auditor pass for a check
    the auditor was required to perform, the route records
    `AUDIT_FALSE_PASS_DETECTED` with `FAILURE_TYPE: audit_miss` and forbids
    staging, commit, push, and normal next-task dispatch;
30. requested action is valid under governance-freeze rules.
31. if `wrong_remote_push`, `wrong_branch_push`,
    `invalid_task_packet_commit`, `forbidden_files`, `secret_exposure`,
    `runtime_corruption`, or `AUDIT_FALSE_PASS_DETECTED` is active, requested
    action is valid under `INCIDENT_RECOVERY.md`.

If any validation fails, dispatch is forbidden. If the failure is found during
checkpoint preflight, staging, commit, and push are forbidden.

For a governed `correction`, `update_state`, `wait_for_owner`, or `stop` action
whose explicit purpose is to create or repair missing workspace identity or
repository lock records, a failed identity gate still blocks normal dispatch,
checkpoint, commit, and push, but it does not block the governed recovery
action itself when transition rules permit that recovery route.

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

## Incident recovery freeze behavior

If incident recovery is active, the orchestrator must apply
`INCIDENT_RECOVERY.md` in addition to ordinary governance freeze rules.

Incident classes include:

```text
wrong_remote_push
wrong_branch_push
invalid_task_packet_commit
forbidden_files
secret_exposure
runtime_corruption
audit_false_pass
```

During incident recovery freeze, normal dispatch, checkpoint, commit, and push
are forbidden. The orchestrator may coordinate recovery only through
runtime/routing metadata, redacted event logging, owner wait, governed
update_state, governed stop, or a full bounded correction task packet when file
changes are required.

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
