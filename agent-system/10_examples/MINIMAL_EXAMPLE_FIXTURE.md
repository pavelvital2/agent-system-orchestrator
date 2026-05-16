# MINIMAL_EXAMPLE_FIXTURE

## Purpose

This fixture shows the smallest generic project input set needed to start the
universal agent-system flow. It is documentation-only and does not require a
real deployment target, credentials, external repositories, or business-domain
implementation.

## Fixture files

```text
project-input/example/TZ.md
project-runtime/example/PROJECT_STATE.md
project-runtime/example/CURRENT_GATE.md
project-runtime/example/NEXT_ACTION.md
project-runtime/example/GAP_REGISTER.md
project-runtime/example/AGENT_RESULTS_LOG.md
project-runtime/example/TASK_REGISTRY.md
project-runtime/example/ACCEPTED_ARTIFACTS.md
project-runtime/example/ORCHESTRATOR_EVENTS_LOG.md
project-runtime/example/STATUS_SUMMARY.md
project-docs/example/03_tasks/TASK_EXAMPLE_001_REQUIREMENTS.md
project-docs/example/00_requirements/REQUIREMENTS_BASELINE.md
project-docs/example/07_reports/TASK_EXAMPLE_001_REQUIREMENTS_RESULT.md
```

The `project-runtime/example/*` paths above are orchestrator-owned runtime
seed, state, and log examples. The `project-docs/example/*` paths illustrate
the active documentation root used for profile-agent task packets, artifacts,
and result handoff files.

## Example TZ

```text
# TZ

PROJECT_TITLE:
Minimal documentation-only example

PROJECT_GOAL:
Create a small accepted document that records one generic workflow and its
handover notes.

SCOPE_IN:
- produce one requirements summary;
- produce one design note;
- produce one task packet for a documentation-only implementation;
- audit accepted work before checkpoint;
- verify setup, run, launch, and handover readiness as documentation gates.

SCOPE_OUT:
- no production deployment;
- no external service integration;
- no credentials, tokens, cookies, or secret values;
- no project-specific business workflow.

ACCEPTANCE_CRITERIA:
- requirements summary exists and maps back to this TZ;
- design note exists and maps to the requirements summary;
- implementation task is bounded and lists allowed file changes;
- audit result passes before any Git checkpoint;
- setup, run, launch, and handover checklists are completed using only
  documentation evidence.
```

## Minimal runtime seed

```text
PROJECT_STATE:
PACKAGE_VERSION: 1.3.0
GOVERNANCE_RULESET_VERSION: 1.3.0
RUNTIME_SCHEMA_VERSION: 1.2.0
CURRENT_PHASE: bootstrap
PROJECT_STATUS: active
ACTION_SEMANTIC: normal
SEMANTIC_REASON:
Initial bootstrap runtime seed has no blocker, owner wait, pause, or terminal
condition.
ACCEPTED_ARTIFACTS_REF: project-runtime/example/ACCEPTED_ARTIFACTS.md
TASK_REGISTRY_REF: project-runtime/example/TASK_REGISTRY.md

NEXT_ACTION:
ACTION_TYPE: create_agent
TARGET_ROLE: requirements_analyst
TASK_ID: TASK_EXAMPLE_001_REQUIREMENTS
TASK_PACKET: project-docs/example/03_tasks/TASK_EXAMPLE_001_REQUIREMENTS.md
DEPENDENCY_STATUS: ready
BLOCKED_BY: NONE
ACTION_SEMANTIC: normal
REQUESTER_RETURN_CONTEXT: NONE
BLOCKING_OR_RESUME_CONTEXT: NONE
INSTRUCTION_FOR_ORCHESTRATOR:
Convert owner-provided TZ into a bounded requirements baseline.
```

## Minimal first task packet

```text
TASK_ID: TASK_EXAMPLE_001_REQUIREMENTS
TASK_STATUS: active
TASK_KIND: normal
SUPERSEDES: NONE
SUPERSEDED_BY: NONE
CORRECTION_OF: NONE
SOURCE_RESULT_REF: NONE
ATTEMPT_NO: NONE
FAILURE_TYPE: none
TASK_TITLE: Create requirements baseline
TASK_TYPE: requirements_analyst
TARGET_ROLE: requirements_analyst
REASONING_LEVEL:
  VALUE: maximum
  OVERRIDE_REASON: NONE
DEPENDENCIES:
- NONE
DEPENDENCY_STATUS: none
REQUESTED_BY_ROLE: NONE
REQUESTED_BY_TASK: NONE
RESEARCH_QUESTION_ID: NONE
RESEARCH_PURPOSE: NONE
RESEARCH_QUESTIONS: NONE
ALLOWED_SOURCES: NONE
FORBIDDEN_SOURCES: NONE
EXPECTED_EVIDENCE: NONE
EXPECTED_OUTPUT: NONE
RETURN_TO_REQUESTER_AFTER_AUDIT_PASS: no
RETURN_TO_ROLE_AFTER_AUDIT_PASS: none
RETURN_TASK_AFTER_AUDIT_PASS: NONE

PURPOSE:
Create a requirements baseline from the example TZ.

SOURCE_OF_TRUTH:
- project-input/example/TZ.md

REQUIRED_DOCS:
- agent-system/01_roles/REQUIREMENTS_ANALYST.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- project-input/example/TZ.md

INPUTS:
NONE

READ_INPUTS:
NONE

SCOPE_IN:
- summarize goals, constraints, scope, and acceptance criteria;
- identify GAPs if the TZ is insufficient;
- remain project-agnostic.

SCOPE_OUT:
- no design;
- no implementation;
- no deployment;
- no credentials.

ALLOWED_FILE_CHANGES:
- project-docs/example/00_requirements/*
- project-docs/example/07_reports/*

FORBIDDEN_FILE_CHANGES:
- credential files
- secret files
- files outside allowed changes

EXPECTED_OUTPUTS:
- project-docs/example/00_requirements/REQUIREMENTS_BASELINE.md

ACCEPTANCE_CRITERIA:
- baseline maps each requirement to the TZ;
- blockers and GAPs are explicit or marked NONE;
- no project-specific business behavior is invented.

EVIDENCE_REQUIREMENTS:
- list changed files;
- summarize source TZ mapping;
- confirm no secret values were read or written.

SETUP_HOOKS:
NONE

LAUNCH_HOOKS:
NONE

RESULT_PATH:
project-docs/example/07_reports/TASK_EXAMPLE_001_REQUIREMENTS_RESULT.md

RISK_REQUIREMENTS:
- unresolved or ambiguous owner input.

MANDATORY_WORKFLOW:
requirements_analyst -> auditor

NEXT_ROLE_ON_PASS:
auditor

NEXT_ROLE_ON_FAIL:
orchestrator

NEXT_ROLE_ON_BLOCKED:
orchestrator

NEXT_ROLE_ON_GAP:
orchestrator

AUDIT_REQUIREMENTS:
mandatory

TESTING_REQUIREMENTS:
none

DOCUMENTATION_REQUIREMENTS:
none

FILESYSTEM_GOVERNANCE:
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md

RUNTIME_GOVERNANCE:
agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md

RESULT_FORMAT:
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md

TERMINAL_CONDITIONS:
NONE

NOTES:
NONE
```

## Non-requirements

This fixture intentionally omits concrete application code, installation
commands, deployment commands, and secret values. Setup, run, launch, and
handover are represented as governed documentation gates in the expected flow
example.
