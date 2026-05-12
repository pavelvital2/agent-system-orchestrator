# AGENT_LIFECYCLE

## Базовое правило

Одна задача = один агент = один свежий контекст.

## Создание агента

При создании агента оркестратор обязан передать:

1. Роль агента.
2. Одну bounded-задачу.
3. Универсальные инструкции для роли.
4. REQUIRED_DOCS из task packet.
5. Ограничения scope.
6. Ожидаемый RESULT format.
7. Запрет на выход за рамки задачи.

## Завершение агента

Агент считается завершённым после возврата RESULT.

После этого:

- его контекст не используется повторно;
- новая задача не добавляется в тот же агентский контекст;
- для новой задачи создаётся новый агент.

## Запреты

Запрещено:

- давать агенту вторую задачу после завершения первой;
- просить агента “заодно” исправить соседние проблемы;
- сохранять контекст агента как источник истины;
- принимать неструктурированный RESULT;
- продолжать pipeline без RESULT.

## Correction and retry lifecycle

Correction is a new bounded task.

A failed, blocked, or violating agent result must not be retried in the same agent context.

For correction:

- create a new task or correction task packet;
- create a fresh agent;
- pass only REQUIRED_DOCS;
- preserve normal audit/testing/documentation requirements;
- do not expand correction scope unless designer creates a new bounded task.

Agent `NEXT_REQUIRED_ACTION` is advisory. The orchestrator must validate it against governance, runtime schema, transition rules, and filesystem governance before updating `NEXT_ACTION.md`.
