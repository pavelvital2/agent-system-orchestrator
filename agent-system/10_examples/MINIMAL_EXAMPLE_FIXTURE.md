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
project-runtime/example/NEXT_ACTION.md
```

The paths above are illustrative. A real orchestrator may choose different
runtime paths when the owner authorizes a project.

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
PACKAGE_VERSION: 1.2.0
GOVERNANCE_RULESET_VERSION: 1.2.0
RUNTIME_SCHEMA_VERSION: 1.1.0
CURRENT_STAGE: bootstrap
CURRENT_GATE: tz_intake
ACTIVE_TASK: NONE
ACTIVE_GAP: NONE
ACCEPTED_ARTIFACTS_REF: project-runtime/example/ACCEPTED_ARTIFACTS.md
TASK_REGISTRY_REF: project-runtime/example/TASK_REGISTRY.md

NEXT_ACTION:
ACTION: create_agent
TARGET_ROLE: requirements_analyst
TASK_PACKET_REF: project-runtime/example/tasks/TASK_EXAMPLE_001_REQUIREMENTS.md
REASON:
Convert owner-provided TZ into a bounded requirements baseline.
```

## Minimal first task packet

```text
TASK_ID: TASK_EXAMPLE_001_REQUIREMENTS
TASK_TYPE: requirements
TARGET_ROLE: requirements_analyst
LIFECYCLE_STAGE: requirements
DEPENDENCIES: none
AUDIT_REQUIRED: yes
POST_AUDIT_GIT_CHECKPOINT_REQUIRED: yes

PURPOSE:
Create a requirements baseline from the example TZ.

REQUIRED_DOCS:
- agent-system/01_roles/REQUIREMENTS_ANALYST.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- project-input/example/TZ.md

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
- project-runtime/example/requirements/*

FORBIDDEN_FILE_CHANGES:
- credential files
- secret files
- files outside allowed changes

EXPECTED_OUTPUT_FILES:
- project-runtime/example/requirements/REQUIREMENTS_BASELINE.md

ACCEPTANCE_CRITERIA:
- baseline maps each requirement to the TZ;
- blockers and GAPs are explicit or marked NONE;
- no project-specific business behavior is invented.

NEXT_RECOMMENDED_ACTION:
- create matching auditor agent.
```

## Non-requirements

This fixture intentionally omits concrete application code, installation
commands, deployment commands, and secret values. Setup, run, launch, and
handover are represented as governed documentation gates in the expected flow
example.
