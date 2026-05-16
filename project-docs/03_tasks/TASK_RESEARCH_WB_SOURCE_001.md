# Task Packet: WB Source Research

## TASK_ID

```text
TASK_RESEARCH_WB_SOURCE_001
```

## TASK_TITLE

```text
Research WB parser source facts for market-parser-v2 design
```

## TASK_KIND

```text
research_dependency
```

## TASK_TYPE

```text
requirements_analyst
```

## TARGET_ROLE

```text
requirements_analyst
```

## REQUESTED_BY_ROLE

```text
designer
```

## REQUESTED_BY_TASK

```text
TASK_BOOTSTRAP_DESIGNER_001
```

## RESEARCH_QUESTION_ID

```text
RQ_WB_SOURCE_001
```

## RESEARCH_PURPOSE

```text
Collect auditable factual evidence from the existing WB parser so later design
can define provider architecture, data contracts, export contracts, migration
tasks, and acceptance criteria without guessing.
```

## RESEARCH_QUESTIONS

```text
1. What are the actual WB components, pipeline order, commands, configuration inputs, state files, checkpoints, and resume behavior?
2. What raw, staging, marts, latest, export, and run report files are produced, and what are their actual schemas and encodings?
3. What fields are required for suggest, filter, SERP/products, sellers, bridges, run reports, and export files?
4. What status, error, retry, backoff, partial-run, and data quality signals already exist?
5. What tests, fixtures, smoke checks, validation rules, and known limitations exist?
6. Which behaviors are confirmed facts, which are assumptions, and which need owner or design decisions later?
```

## ALLOWED_SOURCES

```text
/home/pavel/projects/wb-parser-v1/README.md
/home/pavel/projects/wb-parser-v1/ARCHITECTURE.md
/home/pavel/projects/wb-parser-v1/PROJECT_STATE.md
/home/pavel/projects/wb-parser-v1/DEVELOPMENT_STAGES.md
/home/pavel/projects/wb-parser-v1/app/suggest/alpha.py
/home/pavel/projects/wb-parser-v1/app/filter/engine.py
/home/pavel/projects/wb-parser-v1/app/serp/engine.py
/home/pavel/projects/wb-parser-v1/app/sellers/engine.py
/home/pavel/projects/wb-parser-v1/app/common/paths.py
/home/pavel/projects/wb-parser-v1/app/common/csv_io.py
/home/pavel/projects/wb-parser-v1/app/common/runner.py
/home/pavel/projects/wb-parser-v1/state/run_reports/latest.json
Non-secret output CSV/JSON files explicitly referenced by state/run_reports/latest.json, only when needed to confirm schemas.
```

## FORBIDDEN_SOURCES

```text
Secrets, credentials, cookies, auth tokens, .env files, browser profiles, unsanitized HAR files, unrelated projects, unrelated directories, and any source not listed in ALLOWED_SOURCES.
```

## EXPECTED_EVIDENCE

```text
- file paths and concise line references for each confirmed finding;
- command outputs used to identify schemas or tests;
- schema samples limited to headers or short sanitized excerpts;
- explicit distinction between confirmed fact, assumption, gap, and risk;
- no secret values copied into the result or artifacts.
```

## EXPECTED_OUTPUT

```text
- RESULT using agent-system/03_templates/AGENT_RESULT_TEMPLATE.md;
- research fields required for TASK_KIND research_dependency;
- optional artifact: project-docs/01_architecture/RESEARCH_WB_SOURCE_001.md.
```

## REQUIRED_DOCS

```text
project-input/TZ.md
project-docs/01_architecture/BOOTSTRAP_DESIGN_INTAKE.md
project-docs/03_tasks/TASK_RESEARCH_WB_SOURCE_001.md
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

## SCOPE_IN

```text
- inspect only ALLOWED_SOURCES;
- inventory confirmed WB parser behavior needed for design;
- identify source-backed schemas, commands, state, reports, outputs, and tests;
- report missing or ambiguous facts as unresolved findings;
- create only the optional research artifact if useful.
```

## SCOPE_OUT

```text
- do not change WB parser files;
- do not change implementation code in any project;
- do not design market-parser-v2;
- do not create implementation tasks;
- do not audit your own result;
- do not read forbidden sources.
```

## ALLOWED_FILE_CHANGES

```text
project-docs/01_architecture/RESEARCH_WB_SOURCE_001.md
```

## ACCEPTANCE_CRITERIA

```text
- all findings are backed by allowed source evidence;
- no secret or credential content is copied;
- actual schemas and behavior are separated from assumptions;
- unresolved facts are listed explicitly;
- output can be audited independently.
```

## RETURN_TO_REQUESTER_AFTER_AUDIT_PASS

```text
yes
```

## RETURN_TO_ROLE_AFTER_AUDIT_PASS

```text
designer
```

## RETURN_TASK_AFTER_AUDIT_PASS

```text
TASK_DESIGN_CONTINUATION_AFTER_SOURCE_RESEARCH_001
```

## AUDIT_REQUIREMENTS

```text
mandatory
```

## TESTING_REQUIREMENTS

```text
none
```

## DOCUMENTATION_REQUIREMENTS

```text
none
```

## NEXT_ROLE_ON_PASS

```text
auditor
```

## NEXT_ROLE_ON_BLOCKED

```text
orchestrator
```

## NEXT_ROLE_ON_GAP

```text
orchestrator
```

## EXPECTED_RESULT

```text
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```
