# agent-system orchestrator package

Это стартовый универсальный пакет документов для Codex CLI оркестратора.

Пакет предназначен для схемы:

- один проект;
- один long-running orchestrator в tmux;
- одна задача = один агент;
- каждый агент получает свежий контекст;
- оркестратор не вникает в проект, а работает как конвейер;
- source-of-truth хранится в файлах.

## Первый файл для запуска

Передавай оркестратору:

`agent-system/00_start/ORCHESTRATOR_START.md`

## Минимальный состав

- старт оркестратора;
- роль оркестратора;
- universal project lifecycle from TZ intake to final acceptance;
- requirements analyst, devops/setup engineer, and release manager roles;
- runtime loop;
- whitelist действий;
- lifecycle агента;
- шаблон handoff;
- шаблон RESULT;
- шаблоны runtime state;
- GAP flow;
- журнал результатов;
- governance authority;
- state transition rules;
- violation recovery rules;
- accepted-state locking;
- package versioning policy;
- governance changelog.

## Governance hardening layer

The package includes a minimal governance/state-machine hardening layer:

```text
agent-system/PACKAGE_VERSIONING.md
agent-system/GOVERNANCE_CHANGELOG.md
agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/VIOLATION_RECOVERY.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
```

These documents do not introduce a new orchestration model.
They formalize authority, transitions, recovery, accepted-state locking, and package governance for the existing deterministic filesystem-based runtime.

## Universal lifecycle layer

The package defines a project-agnostic lifecycle for taking a project from TZ intake through requirements, design, implementation, audit, testing, setup, run, launch, documentation, handover, and final acceptance:

```text
agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
agent-system/07_lifecycle/REQUIREMENTS_STAGE.md
agent-system/07_lifecycle/DESIGN_STAGE.md
agent-system/07_lifecycle/IMPLEMENTATION_STAGE.md
agent-system/07_lifecycle/TESTING_STAGE.md
agent-system/07_lifecycle/SETUP_STAGE.md
agent-system/07_lifecycle/RUN_STAGE.md
agent-system/07_lifecycle/LAUNCH_STAGE.md
agent-system/07_lifecycle/HANDOVER_STAGE.md
```

The lifecycle adds universal stage boundaries and gates without changing the deterministic orchestrator model.

## Additional universal roles

The lifecycle uses these additional role documents:

```text
agent-system/01_roles/REQUIREMENTS_ANALYST.md
agent-system/01_roles/DEVOPS_SETUP_ENGINEER.md
agent-system/01_roles/RELEASE_MANAGER.md
```
