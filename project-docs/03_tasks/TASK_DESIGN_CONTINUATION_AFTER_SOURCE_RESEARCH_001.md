# Task Packet: Design Continuation After Source Research

## TASK_ID

```text
TASK_DESIGN_CONTINUATION_AFTER_SOURCE_RESEARCH_001
```

## TASK_TITLE

```text
Continue design after accepted WB and Ozon source research
```

## TASK_KIND

```text
design_continuation
```

## TASK_TYPE

```text
designer
```

## TARGET_ROLE

```text
designer
```

## DEPENDENCIES

```text
- TASK_RESEARCH_WB_SOURCE_001 has auditor STATUS: pass
- TASK_RESEARCH_OZON_SOURCE_001 has auditor STATUS: pass
```

## DEPENDENCY_STATUS

```text
blocked_until_research_audit_pass
```

## REQUESTED_BY_ROLE

```text
designer
```

## REQUESTED_BY_TASK

```text
TASK_BOOTSTRAP_DESIGNER_001
```

## PURPOSE

```text
Use accepted source research to create the next bounded design artifacts for
Market Intelligence Platform without relying on unverified source assumptions.
```

## REQUIRED_DOCS

```text
project-input/TZ.md
project-docs/01_architecture/BOOTSTRAP_DESIGN_INTAKE.md
project-docs/01_architecture/RESEARCH_WB_SOURCE_001.md
project-docs/01_architecture/RESEARCH_OZON_SOURCE_001.md
project-docs/03_tasks/TASK_DESIGN_CONTINUATION_AFTER_SOURCE_RESEARCH_001.md
agent-system/01_roles/DESIGNER.md
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

## SCOPE_IN

```text
- synthesize accepted WB and Ozon research into bounded project design;
- create or update architecture documents under project-docs/01_architecture;
- create bounded follow-up task packets under project-docs/03_tasks;
- separate confirmed facts, assumptions, owner gaps, research dependencies, and risks;
- define audit requirements for every created design or implementation task;
- identify where tester and technical_writer roles are required later.
```

## SCOPE_OUT

```text
- do not read source projects directly unless a new task explicitly allows it;
- do not write implementation code;
- do not edit project-runtime, agent-system, project-input, project-archive, .git, secrets, credentials, or environment files;
- do not route directly to developer after designer output;
- do not skip mandatory auditor review;
- do not treat unaudited research as accepted input.
```

## ALLOWED_FILE_CHANGES

```text
project-docs/01_architecture/*
project-docs/03_tasks/*
```

## EXPECTED_OUTPUTS

```text
- bounded architecture index and initial architecture documents;
- bounded task packets for next design/research/implementation preparation as supported by evidence;
- RESULT using agent-system/03_templates/AGENT_RESULT_TEMPLATE.md.
```

## ACCEPTANCE_CRITERIA

```text
- every source-derived fact traces to accepted research evidence;
- missing owner decisions are returned as GAP instead of assumed;
- missing factual evidence is turned into new research_dependency tasks;
- task packets have minimal REQUIRED_DOCS and bounded scope;
- mandatory audit follows designer pass.
```

## AUDIT_REQUIREMENTS

```text
mandatory
```

## TESTING_REQUIREMENTS

```text
none_for_this_design_task
```

## DOCUMENTATION_REQUIREMENTS

```text
optional
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
