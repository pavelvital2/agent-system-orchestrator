# DESIGN_RESEARCH_LOOP

## Purpose

This document defines the design-specific research dependency loop.

The designer must not guess when factual evidence is missing.

## When to use

The designer must create a bounded research dependency when architecture,
implementation plan, task decomposition, contracts, setup plan, launch plan, or
project documentation cannot be completed safely without additional factual
evidence that can be researched from allowed sources.

Examples of researchable dependencies:

- existing code behavior;
- API or library contract;
- runtime or setup behavior;
- documented data format;
- public technical documentation;
- logs or command output that the task packet explicitly permits.

Examples that are not research dependencies:

- owner business decision or product choice: return GAP;
- missing credentials, inaccessible file, broken command, unavailable runtime:
  return blocked;
- design preference that requires architecture judgment: keep within designer
  task and audit it.

## Required design route

```text
designer identifies missing factual evidence
-> designer creates or requests TASK_KIND: research_dependency
-> research executor returns RESULT and research output
-> independent auditor reviews research
-> audit pass and checkpoint if configured
-> orchestrator dispatches TASK_KIND: design_continuation
-> designer continues bounded design task
-> designer pass routes to design audit
```

Audit fail, blocked, or gap from the research audit must not route to design
continuation. It must route to correction, blocked, GAP, or owner handling as
allowed by runtime governance.

## Required research dependency fields

The research task packet must include:

```text
TASK_KIND: research_dependency
REQUESTED_BY_ROLE: designer
REQUESTED_BY_TASK:
RESEARCH_QUESTION_ID:
RESEARCH_PURPOSE:
RESEARCH_QUESTIONS:
ALLOWED_SOURCES:
FORBIDDEN_SOURCES:
EXPECTED_EVIDENCE:
EXPECTED_OUTPUT:
RETURN_TO_REQUESTER_AFTER_AUDIT_PASS: yes
RETURN_TO_ROLE_AFTER_AUDIT_PASS: designer
RETURN_TASK_AFTER_AUDIT_PASS:
AUDIT_REQUIREMENTS: mandatory
```

## Design continuation

The continuation task must use:

```text
TASK_KIND: design_continuation
TARGET_ROLE: designer
REASONING_LEVEL.VALUE: maximum
```

It must include accepted research and audit refs in `DEPENDENCIES`, `INPUTS`,
or `READ_INPUTS`.

The continuation task is invalid if it cites unaudited research as accepted
evidence.
