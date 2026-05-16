# Bootstrap Design Intake

## Task

```text
TASK_ID: TASK_BOOTSTRAP_DESIGNER_001
ROLE: designer
TASK_KIND: normal
PURPOSE: first bounded bootstrap intake for project design
```

## Source Material Read

```text
project-input/TZ.md
agent-system/01_roles/DESIGNER.md
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/bootstrap/TASK_BOOTSTRAP_DESIGNER_001.md
project-runtime/agent-handoffs/HANDOFF_TASK_BOOTSTRAP_DESIGNER_001.md
```

## Intake Conclusion

The owner source input is structured enough for direct design routing. It
contains purpose, product boundaries, target deliverables, major constraints,
runtime expectations, MVP acceptance criteria, future contours, and known
source dependencies.

No owner decision GAP blocks this bootstrap intake.

Detailed architecture, implementation sequencing, data contracts, and task
decomposition must not be finalized yet, because they depend on factual
evidence from existing external local projects that this task is not allowed
to read:

```text
/home/pavel/projects/wb-parser-v1
/home/pavel/projects/parser_ozon
/home/pavel/projects/parser_ozon/docs/ozon_parser/
```

Those facts are research dependencies, not owner GAPs.

## Confirmed Product Boundaries From Source Input

```text
- Build two new independent projects:
  - market-parser-v2
  - market-analytics
- Existing WB and Ozon parsers are read-only fact sources.
- market-parser-v2 collects and prepares external WB/Ozon market data only.
- market-analytics imports parser export bundles and provides analytics/UI/export.
- Analytics must not read parser internal folders as the production data path.
- WB/Ozon identifiers must always be scoped by marketplace/source_system.
- Cookies, API keys, auth tokens, raw sensitive fixtures, logs, and secrets must not be committed or exported.
- Financial metrics such as profit, margin, revenue, sales, ad efficiency, conversion, and cost economics are out of MVP factual scope until confirmed sources exist.
- Partial, failed, stale, or low-confidence data must be visible in data quality surfaces and exports.
- Own-store, product matching, and Decision Layer are future architecture contours, not MVP implemented facts.
```

## Required Research Dependencies

```text
project-docs/03_tasks/TASK_RESEARCH_WB_SOURCE_001.md
project-docs/03_tasks/TASK_RESEARCH_OZON_SOURCE_001.md
```

The research outputs must be audited independently. Design continuation must
not consume those findings until auditor STATUS is pass.

## Deferred Design Continuation

```text
project-docs/03_tasks/TASK_DESIGN_CONTINUATION_AFTER_SOURCE_RESEARCH_001.md
```

This continuation task is advisory for orchestration. It should be dispatched
only after both source research tasks have accepted audit-pass results.

## Audit Expectations For This Intake

The auditor should verify:

```text
- only allowed input documents were read;
- no external source project files were read by this intake task;
- created files are only under project-docs/01_architecture or project-docs/03_tasks;
- research dependencies are bounded and include allowed/forbidden sources;
- no source-derived contract detail is asserted as confirmed without research;
- NEXT_RECOMMENDED_ACTION routes to mandatory auditor, not developer.
```

## Risks Carried Forward

```text
- WB actual CSV/JSON fields, run reports, checkpoints, and commands are unverified.
- Ozon actual code/docs/output behavior, widget extraction rules, seller enrichment, and tests are unverified.
- Export bundle and analytics import contracts cannot be finalized safely before source research is accepted.
- Production hardening details such as auth, backup, retention, and deployment topology need later bounded design after source contracts are established.
```
