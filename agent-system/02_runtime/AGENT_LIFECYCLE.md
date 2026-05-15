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
8. Handoff или task source reference, если задача создана из handoff.

## Завершение агента

Агент считается завершённым после возврата RESULT.

После этого:

- его контекст не используется повторно;
- новая задача не добавляется в тот же агентский контекст;
- для новой задачи создаётся новый агент.
- RESULT должен быть сохранён или получить deterministic `RESULT_REF`;
- handoff, если он использовался, должен быть помечен как consumed через `CONSUMED_BY_RESULT`.

## Запреты

Запрещено:

- давать агенту вторую задачу после завершения первой;
- просить агента “заодно” исправить соседние проблемы;
- сохранять контекст агента как источник истины;
- принимать неструктурированный RESULT;
- продолжать pipeline без RESULT.
- переиспользовать consumed, superseded или cancelled handoff как active source-of-truth.

## Correction and retry lifecycle

Correction is a new bounded task.

A failed, blocked, or violating agent result must not be retried in the same agent context.

For correction:

- create a new task or correction task packet;
- create a fresh agent;
- pass only REQUIRED_DOCS;
- preserve normal audit/testing/documentation requirements;
- do not expand correction scope unless designer creates a new bounded task.

Agent `NEXT_RECOMMENDED_ACTION` is advisory. The orchestrator must validate it against governance, runtime schema, transition rules, handoff protocol, and filesystem governance before updating runtime state or next action.

## Result evidence lifecycle

Every profile-agent RESULT must include:

- documents read;
- inputs read;
- changed, created, and deleted files;
- commands run;
- evidence;
- scope verification;
- forbidden changes check;
- blockers and gaps when present;
- recommended next action.

Missing mandatory RESULT fields are a formally invalid RESULT and must be handled through governed violation/correction flow.

## Handoff lifecycle

Handoff records follow:

```text
draft -> active -> consumed
draft -> active -> superseded
draft -> cancelled
```

Rules:

- `active` handoff may be used to create exactly one bounded agent task;
- `consumed` handoff must reference `CONSUMED_BY_RESULT`;
- `superseded` handoff must reference `SUPERSEDED_BY`;
- stale handoffs must not be used for dispatch;
- handoff lifecycle cannot bypass audit, testing, documentation, setup, launch, or checkpoint gates.
