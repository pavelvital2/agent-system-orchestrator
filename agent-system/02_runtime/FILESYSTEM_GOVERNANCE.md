# FILESYSTEM_GOVERNANCE

## Назначение

Этот документ определяет правила работы агентов с файловой системой проекта.

Цель — предотвратить:
- хаотичное создание файлов;
- смешение runtime state и проектной документации;
- использование deprecated-документов;
- расползание source-of-truth;
- случайное изменение файлов не той ролью;
- рост giant-doc architecture.

Документ не задаёт полную структуру конкретного проекта заранее. Структура проекта формируется по этапам.

---

## Базовый принцип

Файловая система проекта делится на два уровня:

1. Bootstrap filesystem — минимальная структура, существующая до работы проектировщика.
2. Project filesystem — структура, создаваемая проектировщиком и далее развиваемая агентами по bounded tasks.

Ни один агент не имеет права создавать или менять файлы вне своего scope.

Top-level runtime taxonomy is governed by
`agent-system/02_runtime/RUNTIME_FILE_TAXONOMY.md`:

```text
project-docs     = stable documentation
project-runtime  = execution state/artifacts
project-input    = owner input/TZ/upgrade packages
project-archive  = superseded/deprecated workspace artifacts
```

That taxonomy defines the preferred new `project-runtime/` task, result,
agent, checkpoint, and report layout while preserving compatibility with
existing runtime paths.

Root-level `project-runtime/`, `project-input/`, and `project-archive/` are
generated workspace artifacts. They are expected in target workspaces or local
orchestration sessions. They are not shipped as active state in the package
repository.

Package templates and workspace instance data must not be confused:

```text
agent-system/04_state/       = package state templates
project-runtime/             = generated runtime state
agent-system/03_templates/   = package task/result templates
project-input/               = local owner input
```

---

## Bootstrap filesystem

Bootstrap filesystem существует до проектировщика.

Минимально ожидаемая структура:

```text
agent-system/
project-input/
project-runtime/
project-archive/
```

This minimum root layout is expected for a target workspace or a local
orchestration session. In the package repository, root-level
`project-input/`, `project-runtime/`, and `project-archive/` may exist only as
local generated artifacts for owner input, runtime evidence, or archival
material; they are not active package state to ship.

### agent-system/

Назначение:
- универсальные инструкции для агентов;
- role instructions;
- runtime rules;
- templates;
- governance documents.

Кто может менять:
- владелец проекта;
- вручную назначенный агент только по отдельной bounded-задаче на изменение universal package.

Обычные проектные агенты не имеют права менять `agent-system/`.

---

### project-input/

Назначение:
- входное ТЗ проекта;
- дополнительные входные материалы владельца проекта;
- исходные файлы, которые должны быть переданы проектировщику.
- upgrade packages and owner-provided package task packets.

Пример:

```text
project-input/TZ.md
```

Кто может менять:
- владелец проекта;
- агент только по отдельной задаче подготовки/нормализации входных материалов.

Проектировщик читает `project-input/`, но не должен переписывать исходное ТЗ.

---

### project-runtime/

Назначение:
- operational state pipeline;
- runtime state оркестратора;
- текущие gates;
- next action;
- agent handoff files;
- agent result logs;
- GAP register;
- execution artifacts, task lifecycle records, result records, audit records,
  checkpoint receipts, agent lifecycle events, and generated runtime reports.

Примеры:

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

Checkpoint eligibility receipts are orchestrator-owned runtime evidence under:

```text
project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_<TASK_ID>_<ATTEMPT_NO>.md
```

Recommended new runtime artifact structure:

```text
project-runtime/tasks/pending/
project-runtime/tasks/active/
project-runtime/tasks/completed/
project-runtime/tasks/superseded/
project-runtime/results/worker/
project-runtime/results/audit/
project-runtime/agents/instances.jsonl
project-runtime/checkpoints/
project-runtime/reports/
```

Existing paths such as `project-runtime/agent-results/`,
`project-runtime/audits/`, `project-runtime/bootstrap/`, and root-level
runtime state files remain compatible. Moving or deleting historical runtime
artifacts requires a separate archive or supersede workflow.

Кто может менять:
- оркестратор;
- владелец проекта вручную при emergency correction.

Обычные агенты не имеют права менять `project-runtime/`.

Агенты могут читать runtime-файлы только если они явно переданы в REQUIRED_DOCS.

---

### project-archive/

Назначение:
- deprecated documents;
- superseded docs;
- old execution plans;
- старые task packets, которые больше не являются source-of-truth;
- исторические материалы, исключённые из pipeline.

Пример:

```text
project-archive/deprecated-docs/
```

Кто может менять:
- оркестратор при cleanup;
- техрайтер или проектировщик только по отдельной bounded-задаче;
- владелец проекта вручную.

Документы в `project-archive/` не являются active source-of-truth.

---

## Project filesystem

Project filesystem появляется после работы проектировщика.

Проектировщик обязан определить bounded project structure в рамках `ACTIVE_DOC_ROOT`.

По умолчанию рекомендуемый active documentation root:

```text
project-docs/
```

`project-docs/` is for stable documentation. It must not be used as a runtime
dump for every worker result, audit result, checkpoint receipt, or stale state
artifact.

Если проектировщик предлагает другой root, он должен явно зафиксировать это в runtime state и пройти audit.

---

## ACTIVE_DOC_ROOT

`ACTIVE_DOC_ROOT` — единственный активный корень проектной документации.

Пример:

```text
ACTIVE_DOC_ROOT:
project-docs/
```

Правила:

- все active task packets должны находиться внутри ACTIVE_DOC_ROOT;
- все active project docs должны находиться внутри ACTIVE_DOC_ROOT;
- deprecated docs не могут быть ACTIVE_DOC_ROOT;
- агенты не должны использовать документы вне ACTIVE_DOC_ROOT, если они не указаны явно в REQUIRED_DOCS;
- при смене ACTIVE_DOC_ROOT обязателен audit.

Единственное исключение для active task packet вне `ACTIVE_DOC_ROOT`:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

The `<TARGET_ROLE>` segment is required and must resolve to the selected first
profile route.

Это исключение допустимо только для первого bootstrap dispatch одного
profile-agent и только если файл является полным bootstrap task packet по
`agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md`. Обычные task
packets вне `ACTIVE_DOC_ROOT` остаются invalid.

---

## Workspace identity governance

Every active workspace must have an explicit workspace identity record based on:

```text
agent-system/03_templates/WORKSPACE_IDENTITY_TEMPLATE.md
```

The orchestrator must validate workspace identity before runtime
initialization, profile-agent dispatch, checkpoint, commit, or push. It must
not trust folder name, inherited `.git` metadata, README wording, runtime state
alone, or raw Git remote strings as sufficient identity proof.

The workspace identity model must include:

```text
PROJECT_NAME
PROJECT_SLUG
WORKSPACE_TYPE
PROJECT_ROOT_EXPECTED
GIT_TOPLEVEL_ACTUAL
EXPECTED_REMOTE
ACTUAL_REMOTE
EXPECTED_GIT_REMOTE
ACTUAL_GIT_REMOTE
EXPECTED_BRANCH
ACTUAL_BRANCH
PUSH_ALLOWED
```

Canonical repository identity comparison is required. `EXPECTED_GIT_REMOTE` and
`ACTUAL_GIT_REMOTE` must match after normalization under
`agent-system/09_validators/WORKSPACE_IDENTITY_VALIDATION_RULES.md`.

Equivalent GitHub remote forms are limited to:

```text
https://github.com/OWNER/REPO
https://github.com/OWNER/REPO.git
git@github.com:OWNER/REPO.git
git@<approved_ssh_host_alias>:OWNER/REPO.git
```

The SSH host alias form is valid only when the alias is explicitly accepted in
the repository lock or bounded evidence proves the alias resolves to
`github.com`.

## Safe project workspace initialization

New project workspaces must be initialized from the universal package through:

```text
agent-system/scripts/init_project_workspace.sh
```

or an equivalent governed procedure that satisfies the same invariants.

The initialization procedure must:

- copy only universal package content needed by the workspace, normally
  `agent-system/`;
- create project-owned bootstrap directories such as `project-input/`,
  `project-runtime/`, and `project-archive/` locally in the target workspace;
- never copy, rename, inherit, or reuse the package repository `.git`
  directory;
- reject a target directory inside the package repository worktree;
- reject a target directory that inherits an ancestor Git worktree instead of
  owning its own `.git`;
- require explicit expected remote and expected branch inputs before repository
  lock acceptance;
- compare any existing target `.git` origin and branch against those expected
  inputs before copying package files;
- classify an existing target `.git` origin mismatch as
  `repository_identity_mismatch`;
- classify an existing target branch mismatch as
  `repository_branch_mismatch`;
- create or require creation of `WORKSPACE_IDENTITY` and `REPOSITORY_LOCK`
  records before normal runtime initialization.

Clone-renaming the package repository into a project workspace is forbidden.
That pattern carries package repository identity into project runtime state and
must be treated as `workspace_identity_leakage` until corrected.

Repository lock acceptance is forbidden unless all of these are true:

```text
EXPECTED_GIT_REMOTE equals ACTUAL_GIT_REMOTE after canonical normalization
EXPECTED_BRANCH equals ACTUAL_BRANCH
WORKSPACE_TYPE is valid for the target workspace
PUSH_ALLOWED remains false unless the accepted lock explicitly authorizes push
```

## Workspace types

```text
package_repo:
  Universal agent-system package repository. Only owner-authorized
  package-governance tasks may change agent-system files. Push requires an
  accepted repository lock.

project_workspace:
  Project orchestration workspace containing project-input, project-runtime,
  project docs, and package instructions. It must not inherit identity from a
  copied package checkout. Push requires an accepted repository lock.

implementation_repo:
  Product/source repository for implementation work. Code checkpoint requires
  matching canonical repository identity and branch. Push requires an accepted
  repository lock.

test_fixture:
  Disposable validation fixture. PUSH_ALLOWED must remain false, and fixture
  identity cannot authorize package, project workspace, or implementation repo
  checkpoint.
```

If workspace type conflicts with README, runtime state, manifest, Git remote,
Git branch, or repository lock, classify the condition as
`workspace_identity_leakage`. Dispatch, checkpoint, commit, and push are
forbidden until governed correction resolves the conflict.

---

## Рекомендуемая bounded-doc структура

Проектировщик может использовать базовую структуру:

```text
project-docs/
  00_project/
  01_architecture/
  02_stages/
  03_tasks/
  04_audits/
  05_testing/
  06_runtime/
  07_reports/
  08_user_docs/
```

Эта структура не обязана существовать до проектировщика.

Проектировщик создаёт только те папки, которые нужны проекту.

---

## Права ролей на изменение файлов

### Orchestrator

Может изменять:
- `project-runtime/`
- `project-archive/` при cleanup
- handoff/result tracking files

Не может изменять:
- код проекта;
- проектную документацию внутри ACTIVE_DOC_ROOT;
- task packets по содержанию;
- universal instructions без отдельной задачи владельца проекта.

---

### Requirements Analyst

Может читать:
- `project-input/`, если указан в REQUIRED_DOCS;
- accepted project docs внутри ACTIVE_DOC_ROOT, если они указаны в REQUIRED_DOCS;
- назначенный requirements task packet.

Может изменять:
- bounded requirements artifacts внутри ACTIVE_DOC_ROOT, если это явно разрешено task packet;
- requirements traceability notes, GAP notes, and acceptance signal summaries, если они входят в scope задачи.

Не может изменять:
- `agent-system/`;
- `project-runtime/`;
- `project-input/`, включая исходное ТЗ, кроме отдельной source-normalization задачи;
- `project-archive/`;
- implementation code;
- architecture docs, task packets, audit/testing docs, setup docs, release docs, or user docs outside assigned scope.

---

### Designer

Может изменять:
- проектную документацию внутри ACTIVE_DOC_ROOT;
- task packets;
- stage docs;
- architecture docs;
- audit/testing/writer flow docs.

Не может изменять:
- код проекта;
- `project-runtime/`;
- `agent-system/`;
- deprecated docs без отдельной cleanup-задачи;
- исходное ТЗ в `project-input/`.

---

### Developer

Может изменять:
- только implementation files, разрешённые task packet;
- новые implementation files, если они входят в scope задачи.

Git authority:
- profile agents never commit or push;
- task packets cannot grant commit or push authority to the developer.

Не может изменять:
- `agent-system/`;
- `project-runtime/`;
- `project-input/`;
- `project-archive/`;
- task packets;
- architecture docs;
- audit/testing docs;
- user docs, если это не указано отдельной задачей.

---

### Auditor

По умолчанию не изменяет файлы.

Может читать:
- task packet;
- RESULT проверяемого агента;
- REQUIRED_DOCS для аудита;
- файлы, которые нужно проверить по audit scope.

Не может изменять:
- код;
- проектную документацию;
- task packets;
- runtime state;
- universal instructions.

---

### Tester

По умолчанию не изменяет файлы.

Может создавать временные тестовые данные, если это нужно для testing task и не меняет исходный код.

Не может изменять:
- код;
- project docs;
- task packets;
- runtime state;
- universal instructions;
- archive docs.

---

### Technical Writer

Может изменять:
- user-facing docs;
- run docs;
- usage docs;
- accepted documentation files, явно указанные в documentation task.

Рекомендуемая папка:

```text
project-docs/08_user_docs/
```

Не может изменять:
- код;
- task packets;
- runtime state;
- source architecture docs, если task packet не разрешает это явно;
- project scope docs для размещения user manual;
- deprecated docs без отдельной задачи.

---

### DevOps Setup Engineer

Может изменять:
- bounded setup, configuration, run-readiness, or operational handoff artifacts внутри ACTIVE_DOC_ROOT, если это явно разрешено task packet;
- allowed project setup files, configuration templates, sample files, scripts, or run instructions, если они явно указаны task packet.

Может читать:
- setup/run task packet;
- accepted setup, architecture, implementation, testing, or runtime-readiness evidence, если они указаны в REQUIRED_DOCS;
- configuration examples without secret values.

Не может изменять:
- `agent-system/`;
- `project-runtime/`;
- `project-input/`;
- `project-archive/`;
- product requirements, architecture, implementation behavior, acceptance criteria, release approvals, or user docs outside assigned scope;
- credentials, local secrets, tokens, cookies, private keys, or `.env` files.

Не может:
- expose, print, commit, or invent secret values;
- run production deployment unless explicitly assigned and approved by task packet.
- commit or push changes.

---

### Release Manager

Может изменять:
- launch readiness, release readiness, rollback/recovery, handover, and final acceptance artifacts внутри ACTIVE_DOC_ROOT, если это явно разрешено task packet;
- bounded release blocker, known limitation, and accepted-artifact readiness summaries, если они входят в scope задачи.

Может читать:
- launch, release, or handover task packet;
- accepted task results, audit results, testing results, setup/run evidence, documentation results, and owner decisions, если они указаны в REQUIRED_DOCS.

Не может изменять:
- `agent-system/`;
- `project-runtime/`;
- `project-input/`;
- `project-archive/`;
- implementation code;
- requirements, architecture, acceptance criteria, audit findings, testing evidence, setup evidence, or user docs outside assigned scope.

Не может:
- mark the project completed;
- ignore failed or missing gates;
- commit or push changes;
- tag, deploy, or approve production launch unless explicitly assigned by an orchestrator-controlled task.

Terminal completion remains orchestrator-controlled.

---

## Deprecated documents

Документ считается deprecated, если:
- он заменён bounded-doc structure;
- его больше нельзя использовать как source-of-truth;
- он перемещён в `project-archive/`;
- или явно помечен заголовком `# DEPRECATED`.

Каждый deprecated документ должен начинаться с блока:

```md
# DEPRECATED

Этот документ больше не является source-of-truth.
Не использовать для новых task packets и audit flow.
```

Запрещено:
- включать deprecated docs в REQUIRED_DOCS;
- использовать deprecated docs для audit;
- использовать deprecated docs для developer handoff;
- ссылаться на deprecated docs из active task packets.

---

## Task packet lifecycle

Каждая bounded-задача должна иметь отдельный task packet.

Task packets должны находиться внутри ACTIVE_DOC_ROOT, кроме единственного
первого bootstrap task packet:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

Любой ordinary task packet вне ACTIVE_DOC_ROOT invalid.

Dispatchable task packets must declare:

```text
# TASK PACKET
```

and must pass:

```text
agent-system/09_validators/TASK_PACKET_SCHEMA_VALIDATION_RULES.md
agent-system/scripts/validate_task_packet.py
```

Files that declare:

```text
# TASK PROPOSAL
TASK_PROPOSAL
```

are non-dispatchable proposals. They may not be selected by
`NEXT_ACTION.TASK_PACKET`, may not create a profile agent, and must be converted
into a full task packet before dispatch.

Selecting a proposal, malformed task file, superseded task packet, deprecated
task packet, or ordinary task packet outside `ACTIVE_DOC_ROOT` for dispatch is
an `invalid_task_packet_schema` blocker.

Рекомендуемая папка:

```text
project-docs/03_tasks/
```

Task packet может быть:
- active;
- completed;
- superseded;
- deprecated.

Each task packet must explicitly declare:

```text
TASK_STATUS: active | completed | superseded | deprecated
SUPERSEDES: <TASK_ID | NONE>
SUPERSEDED_BY: <TASK_ID | NONE>
```

Only `TASK_STATUS: active` task packets may be selected by `NEXT_ACTION`.

Task packets must also declare:

```text
TASK_KIND: normal | research_dependency | design_continuation | task_continuation | correction | audit | testing | setup | launch | handover
```

`TASK_KIND: research_dependency` must remain a bounded sequential dependency.
It does not authorize generalized DAG/parallel orchestration, does not replace
GAP handling for owner decisions, and does not replace BLOCKER handling for
technical execution obstacles.

Research dependency task packets must keep requester return metadata in the
task packet and task registry:

```text
REQUESTED_BY_ROLE
REQUESTED_BY_TASK
RETURN_TO_REQUESTER_AFTER_AUDIT_PASS
RETURN_TO_ROLE_AFTER_AUDIT_PASS
RETURN_TASK_AFTER_AUDIT_PASS
```

Research results must not be routed to requester continuation until an
independent auditor returns `STATUS: pass`.

Если task packet заменён новым:
- старый task packet должен быть помечен superseded/deprecated;
- новый task packet должен иметь новый TASK_ID;
- pipeline не должен использовать оба task packets как active одновременно.
- the superseded task packet must not be used in `NEXT_ACTION`;
- the superseded task packet must not be used as source-of-truth for new agent dispatch.

---

## Result files and logs

RESULT агента является operational evidence.

RESULT должен быть:
- зафиксирован оркестратором;
- добавлен в agent result log;
- доступен следующему агенту только если он входит в REQUIRED_DOCS или явно передан в handoff.

Рекомендуемая папка для журналов:

```text
project-runtime/
```

Обычные агенты не должны самостоятельно редактировать result logs.

---

## Runtime state

Runtime state — это operational source-of-truth для оркестратора.

Минимальные runtime files:

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

Правила:
- runtime state обновляет оркестратор;
- агенты не меняют runtime state;
- runtime state не заменяет project docs;
- project docs не заменяют runtime state.

---

## Git authority

Profile agents never commit or push. Task packets cannot grant commit or push
authority to profile agents.

The post-audit Git checkpoint is orchestrator-owned only and may run only after
the required auditor returns `STATUS: pass`.

Auditor `STATUS: pass` is not sufficient for commit or push. Before any
orchestrator-owned checkpoint, commit, or push, the orchestrator must validate:

```text
- workspace identity gate passed;
- canonical EXPECTED_GIT_REMOTE equals ACTUAL_GIT_REMOTE;
- EXPECTED_BRANCH equals ACTUAL_BRANCH;
- WORKSPACE_TYPE permits the requested checkpoint behavior;
- REPOSITORY_LOCK_STATUS is accepted when push is requested;
- PUSH_ALLOWED is true only under the accepted repository lock.
- CHECKPOINT_ELIGIBILITY_STATUS is eligible in a bounded receipt;
- changed files pass CHANGED_FILES_SCOPE_MATRIX;
- secret scan passes SECRET_SCAN_RULES without potential_secret_exposure.
```

Wrong remote, wrong branch, identity leakage, missing repository lock, or
`PUSH_ALLOWED: false` is a hard blocker for push. Commit is also forbidden
unless a governed local-only checkpoint is explicitly allowed by the repository
lock and active task packet.

Changed-file scope validation is governed by:

```text
agent-system/09_validators/CHANGED_FILES_SCOPE_MATRIX.md
```

Secret and sensitive artifact validation is governed by:

```text
agent-system/09_validators/SECRET_SCAN_RULES.md
```

Checkpoint eligibility receipts must use:

```text
agent-system/03_templates/CHECKPOINT_ELIGIBILITY_TEMPLATE.md
```

## Secret handling

No role may read, print, edit, stage, commit, or push secrets. A safe
secret-handling task may only identify non-secret configuration names,
purposes, and placeholder examples when task scope requires it.

Secret values must never be written into:
- logs;
- RESULTs;
- project docs;
- runtime state;
- commits;
- task packets;
- handoff artifacts.

Secrets include:
- credentials;
- tokens;
- cookies;
- HAR/devtools dumps;
- private keys;
- passwords;
- session material;
- local secret stores;
- `.env` files with real values.

Safe references may identify environment variable names, expected purpose, and placeholder examples only when task scope requires configuration documentation.

---

## Accepted state locking

Accepted state is governed by:

```text
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
```

Rules:

- solution_architect output is accepted only after design audit pass;
- developer output is accepted only after implementation audit pass;
- tested behavior is accepted only after tester pass when testing is required;
- technical writer output cannot redefine unverified implementation behavior;
- accepted source-of-truth artifacts cannot be changed in place by unrelated tasks;
- changing accepted artifacts requires a new bounded task and required audit path.

Any modification of an accepted artifact outside governed task scope is a workflow violation.

---

## Terminal project state

Проект считается завершённым только после orchestrator finalization.

Ни один профильный агент не имеет права самостоятельно объявить проект завершённым.

Terminal state допустим только если:
- implementation tasks завершены;
- обязательные audit gates пройдены;
- обязательное testing завершено;
- required documentation tasks завершены;
- active GAP отсутствуют;
- active blockers отсутствуют;
- `NEXT_ACTION` переведён в `stop`;
- `CURRENT_PHASE` переведён в `completed`.

---

## Запрещённые действия

Запрещено:

- создавать giant execution documents для средних и крупных проектов;
- хранить все задачи в одном общем документе;
- смешивать runtime state и project docs;
- использовать старые документы как source-of-truth;
- передавать агенту весь проект вместо REQUIRED_DOCS;
- изменять файлы вне scope;
- использовать project-archive как active source;
- менять universal instructions внутри обычного project pipeline;
- создавать новые папки без связи с task packet или role responsibility.

---

## Correction flow

Если агент изменил файл вне разрешённой зоны:
- оркестратор фиксирует workflow violation;
- pipeline не продолжается;
- результат возвращается на correction flow;
- при необходимости вызывается аудитор или проектировщик.

Если task packet требует изменить файл вне обычных прав роли:
- это должно быть явно указано в scope IN;
- должно пройти audit;
- должно быть отражено в RESULT.
