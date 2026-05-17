# AGENT_RESULT_TEMPLATE

Каждый агент обязан вернуть RESULT строго в этом формате.

```text
RESULT:
STATUS: pass | fail | blocked | gap

ROLE:
<requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager>

TASK:
<TASK_ID or task title>

SUMMARY:
<1-5 lines>

READ_DOCS:
- <path>

READ_INPUTS:
- <path or input ref> | NONE

CHANGED_FILES:
- <path> | NONE

CREATED_FILES:
- <path> | NONE

DELETED_FILES:
- <path> | NONE

COMMANDS_RUN:
- <command and concise result> | NONE

EVIDENCE:
- <command/result/file/report> | NONE

SCOPE_VERIFICATION:
- <verification item> | NONE

FORBIDDEN_CHANGES_CHECK:
- <check/result> | NONE

RISKS:
- <risk> | NONE

BLOCKERS:
- <blocker> | NONE

GAPS:
- GAP_ID: <id> | NONE
  TYPE: <business | functional | technical | documentation | acceptance | runtime>
  BLOCKS: <what is blocked>
  QUESTION_TO_OWNER: <question>
  RECOMMENDED_OPTIONS:
    A. <option>
    B. <option>
    C. <option>
  RECOMMENDED_OPTION: <A|B|C>
  REASON: <short reason>

NEXT_RECOMMENDED_ACTION:
- <next action>
```

For `TASK_KIND: research_dependency`, the RESULT must also include the research
output fields from:

```text
agent-system/03_templates/RESEARCH_RESULT_TEMPLATE.md
```

These fields are:

```text
RESEARCH_QUESTION_ID
RESEARCH_SUMMARY
SOURCES_USED
EVIDENCE_MATRIX
UNRESOLVED_FINDINGS
DESIGN_OR_TASK_IMPLICATIONS
RECOMMENDED_NEXT_ACTION
```

## Status rule

Profile agents may return only these `STATUS` values:

```text
pass
fail
blocked
gap
```

`violation` is not a valid profile-agent RESULT `STATUS`.

`violation` is an orchestrator-derived recovery/logging category for governance, workflow, filesystem, runtime-state, or formally invalid RESULT handling.

## Role rule

`ROLE` must be one of the canonical profile execution roles:

```text
requirements_analyst
designer
developer
auditor
tester
technical_writer
devops_setup_engineer
release_manager
```

Control/routing pseudo-roles `orchestrator`, `project_owner`, and `none` are not valid profile-agent RESULT roles.

Если GAP отсутствует, секция должна быть:

```text
GAPS:
- NONE
```

## Result authority rule

`NEXT_RECOMMENDED_ACTION` is advisory.

The orchestrator must validate it against:

- runtime state schema;
- state transition rules;
- governance authority;
- filesystem governance;
- active task packet lifecycle.

Agent RESULT cannot directly override governance or mark the project completed.

## Required field rule

Every RESULT must include these fields exactly:

```text
STATUS
ROLE
TASK
SUMMARY
READ_DOCS
READ_INPUTS
CHANGED_FILES
CREATED_FILES
DELETED_FILES
COMMANDS_RUN
EVIDENCE
SCOPE_VERIFICATION
FORBIDDEN_CHANGES_CHECK
RISKS
BLOCKERS
GAPS
NEXT_RECOMMENDED_ACTION
```

If a field has no entries, use `NONE`.

Legacy RESULT consumers may still display or read `NEXT_REQUIRED_ACTION` as an
alias for older records, but profile agents must emit
`NEXT_RECOMMENDED_ACTION`.

Research `RECOMMENDED_NEXT_ACTION` is also advisory. It does not replace
`NEXT_RECOMMENDED_ACTION` and does not authorize requester return before audit
pass.

## Audit evidence labels

Auditor RESULTs must keep the required top-level fields unchanged. Mandatory
audit checks are recorded inside `EVIDENCE` or `SCOPE_VERIFICATION` using these
labels:

```text
CHANGED_FILES_SCOPE_STATUS
TASK_PACKET_SCHEMA_STATUS
REPOSITORY_IDENTITY_STATUS
FORBIDDEN_PATH_STATUS
RUNTIME_MUTATION_STATUS
EVIDENCE_STATUS
SECRET_EXPOSURE_STATUS
REASONING_LEVEL_COMPLIANCE
VALIDATED_TASK_PACKETS
```

When changed files include `TASK_*.md`, `TASK_PROPOSAL*.md`, or
`*_TASK_PACKET*.md`, `VALIDATED_TASK_PACKETS` must list each changed
task-like file with its classification and schema status.

When checkpoint preflight detects a blocker after auditor `STATUS: pass` for a
check the auditor was required to perform, the orchestrator records:

```text
AUDIT_FALSE_PASS_DETECTED
FAILURE_TYPE: audit_miss
```

The resulting correction uses normal RESULT fields and must not authorize
commit or push until the correction passes its own audit and checkpoint
eligibility preflight.
