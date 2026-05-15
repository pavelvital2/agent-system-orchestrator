# GAP_FLOW

## Назначение

GAP — это пробел, противоречие или недостаток информации, который профильный агент не имеет права додумывать.

GAP is blocking by default for every dependent branch, task, gate, artifact, or decision listed in `BLOCKS`.

Non-blocking observations, risks, weak assumptions, or improvement notes are findings, not GAPs.
They must be recorded in a findings register or RESULT evidence without stopping dependent dispatch unless governance later classifies them as blockers.

## Кто выявляет GAP

GAP выявляет только профильный агент:

- проектировщик — в ТЗ, бизнес-логике, функциональности, пользовательских сценариях;
- разработчик — в проектной документации или task packet;
- аудитор — в несоответствии между задачей, документацией и результатом;
- тестировщик — в expected behavior или acceptance criteria;
- техрайтер — в недостающих данных для фиксации документации.

Оркестратор GAP не выявляет и не анализирует.

## Как оркестратор узнаёт о GAP

Только через RESULT агента:

```text
STATUS: gap
```

и заполненную секцию:

```text
GAPS:
```

## Действия оркестратора при GAP

1. Зафиксировать GAP в `project-runtime/GAP_REGISTER.md`.
2. Пометить зависимую ветку как blocked.
3. Обновить `CURRENT_GATE.md`.
4. Обновить `NEXT_ACTION.md`.
5. Если есть независимая ветка, продолжить её.
6. Если независимой ветки нет, ожидать ответа владельца проекта.

## Owner decision protocol

When a GAP requires owner input, the orchestrator must create or update an owner decision record using:

```text
agent-system/03_templates/OWNER_DECISION_TEMPLATE.md
```

The owner decision record must include:

- question;
- context;
- options;
- recommended option;
- owner decision;
- affected tasks;
- affected artifacts;
- date.

Owner input may answer the question, but it does not by itself authorize dependent dispatch.
If the decision changes accepted source-of-truth, the required design, correction, audit, runtime-state, or accepted-artifact update must complete before the GAP can close.

## Findings

A finding is a non-blocking observation that should remain traceable but does not prevent the next governed action.

Examples:
- unclear but non-blocking assumption;
- improvement recommendation outside current scope;
- risk that does not invalidate acceptance;
- discovery note that should be reviewed later.

Findings must not be stored as active GAPs unless they block a dependent branch or require owner/source-of-truth resolution before work can continue.
Use:

```text
agent-system/03_templates/FINDINGS_REGISTER_TEMPLATE.md
```

## Запрет

Оркестратор не имеет права:

- отвечать на GAP сам;
- выбирать вариант ответа за владельца проекта;
- просить разработчика обойти GAP;
- продолжать зависимую ветку до закрытия GAP.

## GAP closure rule

A GAP is not closed merely because an owner/designer answer exists.

A GAP may be closed only when its resolution is reflected in accepted source-of-truth and the GAP register links to that update:

- updated accepted project documentation;
- updated active task packet;
- corrected runtime state;
- or explicit owner decision recorded through governed flow.

If the GAP changes architecture, scope, acceptance criteria, or task packet content, the resolution must go through designer/audit or bounded correction flow before dependent dispatch continues.

Minimum closure evidence:

```text
OWNER_DECISION_REF: <path or NONE>
ACCEPTED_SOURCE_OF_TRUTH_UPDATE: <path/ref>
ACCEPTED_ARTIFACT_REF: <path/ref or NONE>
CLOSURE_EVIDENCE: <RESULT/audit/runtime-state ref>
```
