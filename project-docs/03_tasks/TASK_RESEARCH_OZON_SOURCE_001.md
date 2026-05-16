# Task Packet: Ozon Source Research

## TASK_ID

```text
TASK_RESEARCH_OZON_SOURCE_001
```

## TASK_TITLE

```text
Research Ozon parser source facts for market-parser-v2 design
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
RQ_OZON_SOURCE_001
```

## RESEARCH_PURPOSE

```text
Collect auditable factual evidence from the existing Ozon parser and its
documentation so later design can define provider architecture, data contracts,
export contracts, migration tasks, and acceptance criteria without guessing.
```

## RESEARCH_QUESTIONS

```text
1. What are the actual Ozon scripts, Python extractors, Playwright/Chromium flow, commands, configuration inputs, and runtime assumptions?
2. What suggest, products/SERP, seller enrichment, network capture, bridge, output, and test artifacts exist?
3. What actual fields are extracted for suggestions, product rows, pagination state, sellers, and seller-query-product bridge rows?
4. Which documented Ozon facts still match code and tests, and where do docs/code/outputs diverge?
5. What anti-bot, cookie, throttling, partial-run, failure-state, and security behaviors are confirmed?
6. Which behaviors are confirmed facts, which are assumptions, and which need owner or design decisions later?
```

## ALLOWED_SOURCES

```text
/home/pavel/projects/parser_ozon/package.json
/home/pavel/projects/parser_ozon/scripts/collect_ozon_suggest.js
/home/pavel/projects/parser_ozon/scripts/collect_ozon_products.js
/home/pavel/projects/parser_ozon/scripts/enrich_ozon_sellers.js
/home/pavel/projects/parser_ozon/scripts/collect_ozon_network.js
/home/pavel/projects/parser_ozon/ozon_parser/extractor.py
/home/pavel/projects/parser_ozon/ozon_parser/suggest_extractor.py
/home/pavel/projects/parser_ozon/tests/test_ozon_extractor.py
/home/pavel/projects/parser_ozon/tests/test_ozon_suggest_extractor.py
/home/pavel/projects/parser_ozon/docs/ozon_parser/
Non-secret sanitized fixtures or sample outputs explicitly referenced by the listed docs, tests, or scripts, only when needed to confirm schemas.
```

## FORBIDDEN_SOURCES

```text
Secrets, credentials, cookies, auth tokens, .env files, browser profiles, unsanitized HAR files, unrelated projects, unrelated directories, and any source not listed in ALLOWED_SOURCES.
```

## EXPECTED_EVIDENCE

```text
- file paths and concise line references for each confirmed finding;
- command outputs used to identify schemas, scripts, or tests;
- schema samples limited to headers or short sanitized excerpts;
- explicit docs-vs-code-vs-output comparison where evidence exists;
- explicit distinction between confirmed fact, assumption, gap, and risk;
- no secret values copied into the result or artifacts.
```

## EXPECTED_OUTPUT

```text
- RESULT using agent-system/03_templates/AGENT_RESULT_TEMPLATE.md;
- research fields required for TASK_KIND research_dependency;
- optional artifact: project-docs/01_architecture/RESEARCH_OZON_SOURCE_001.md.
```

## REQUIRED_DOCS

```text
project-input/TZ.md
project-docs/01_architecture/BOOTSTRAP_DESIGN_INTAKE.md
project-docs/03_tasks/TASK_RESEARCH_OZON_SOURCE_001.md
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

## SCOPE_IN

```text
- inspect only ALLOWED_SOURCES;
- inventory confirmed Ozon parser behavior needed for design;
- identify source-backed schemas, commands, state, outputs, tests, docs mismatches, and risks;
- report missing or ambiguous facts as unresolved findings;
- create only the optional research artifact if useful.
```

## SCOPE_OUT

```text
- do not change Ozon parser files;
- do not change implementation code in any project;
- do not design market-parser-v2;
- do not create implementation tasks;
- do not audit your own result;
- do not read forbidden sources.
```

## ALLOWED_FILE_CHANGES

```text
project-docs/01_architecture/RESEARCH_OZON_SOURCE_001.md
```

## ACCEPTANCE_CRITERIA

```text
- all findings are backed by allowed source evidence;
- no secret or credential content is copied;
- actual schemas and behavior are separated from assumptions;
- docs/code/output divergences are identified where evidence exists;
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
