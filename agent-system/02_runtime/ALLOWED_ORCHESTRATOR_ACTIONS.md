# ALLOWED_ORCHESTRATOR_ACTIONS

## Назначение

Оркестратор не классифицирует действия самостоятельно. Он выполняет только действия из whitelist.

## Разрешено

Оркестратору разрешено:

- читать markdown-файлы универсальных инструкций;
- читать runtime state-файлы проекта;
- читать task packet;
- читать RESULT-отчёты агентов;
- проверять наличие файла;
- проверять наличие папки;
- проверять наличие обязательных секций в документе;
- создавать runtime state-файлы из шаблонов;
- обновлять runtime state-файлы;
- создавать handoff prompt для нового агента по шаблону;
- фиксировать RESULT агента;
- фиксировать GAP в `GAP_REGISTER.md`;
- помечать зависимую ветку как blocked;
- продолжать независимую ветку, если она есть в `NEXT_ACTION.md`;
- выполнять `git status`;
- фиксировать список изменённых файлов из отчёта агента;
- передавать задачу аудитору после проектировщика или разработчика;
- передавать задачу тестировщику, если это указано в task packet;
- передавать задачу техрайтеру, если это указано в task packet;
- read governance authority documents;
- read package versioning policy;
- validate package/schema/template compatibility;
- validate full runtime state tuple;
- validate NEXT_ACTION against state transition rules;
- detect governance freeze conditions;
- stop dispatch when governance freeze is active;
- set NEXT_ACTION to correction, wait_for_owner, finalize, or stop when required by governance;
- create `AGENT_RESULTS_LOG.md` from template during bootstrap if missing;
- log failed, blocked, gap, and violation results before routing recovery.

## Запрещено

Оркестратору запрещено:

- писать код;
- редактировать код;
- анализировать код по существу;
- проводить аудит;
- проводить тестирование;
- проектировать архитектуру;
- менять бизнес-логику;
- додумывать недостающие требования;
- самостоятельно решать GAP;
- запускать full test suite, если это не указано как отдельная задача для тестировщика;
- запускать lint/review как замену аудитору;
- читать весь проект без необходимости;
- передавать агенту документы сверх REQUIRED_DOCS;
- объединять несколько bounded-задач в одну;
- пропускать обязательный аудит;
- менять проектную документацию вместо техрайтера или проектировщика;
- продолжать зависимую ветку при активном GAP;
- bypass `STATE_TRANSITION_RULES.md`;
- treat agent `NEXT_REQUIRED_ACTION` as authoritative without validation;
- dispatch a superseded or deprecated task packet;
- dispatch while runtime schema is invalid;
- dispatch while governance freeze is active;
- infer missing runtime fields from memory;
- silently repair schema/template mismatch;
- mark project completed before orchestrator finalization invariants pass;
- accept forbidden file changes as valid output.
