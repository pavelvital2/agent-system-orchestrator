# AGENT_RESULT_TEMPLATE

Каждый агент обязан вернуть RESULT строго в этом формате.

```text
RESULT:
STATUS: pass | fail | blocked | gap

TASK_ID:
<TASK_ID>

AGENT_INSTANCE_ID:
<agent instance id assigned by orchestrator>

ROLE:
<requirements_analyst | solution_architect | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager>

TASK:
<TASK_ID or task title>

RESULT_ACCEPTANCE_MODE: result_only | artifact_package
ARTIFACT_PACKAGE_REQUIRED: false | true

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

TESTS_RUN:
- <test/check and concise result> | NONE

EVIDENCE:
- <command/result/file/report> | NONE

SCOPE_VERIFICATION:
- <verification item> | NONE

FORBIDDEN_CHANGES_CHECK:
- <check/result> | NONE

RISKS:
- <risk> | NONE

LIMITATIONS:
- <limitation> | NONE

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

REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
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
solution_architect
designer
developer
auditor
tester
technical_writer
devops_setup_engineer
release_manager
```

`designer` is a deprecated compatibility alias for `solution_architect`.
New RESULT records must use `solution_architect`; legacy `designer` records
remain accepted with validator warnings.

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
TASK_ID
AGENT_INSTANCE_ID
ROLE
TASK
SUMMARY
READ_DOCS
READ_INPUTS
CHANGED_FILES
CREATED_FILES
DELETED_FILES
COMMANDS_RUN
TESTS_RUN
EVIDENCE
SCOPE_VERIFICATION
FORBIDDEN_CHANGES_CHECK
RISKS
LIMITATIONS
BLOCKERS
GAPS
NEXT_RECOMMENDED_ACTION
REUSE_ALLOWED
AGENT_TERMINATION_REQUIRED
```

If a field has no entries, use `NONE`.

Candidate artifact packages are agent-produced proposals. When created, list
their paths in `CREATED_FILES` and cite them in `EVIDENCE` with the label
`CANDIDATE_ARTIFACT_PACKAGE`. Candidate packages are not accepted project truth
and must not be consumed by downstream context packs until a governed
acceptance step copies them to `project-runtime/artifacts/accepted/`. Rendered
views intended for downstream context must live under `project-runtime/rendered/`.

Set `RESULT_ACCEPTANCE_MODE: result_only` and `ARTIFACT_PACKAGE_REQUIRED:
false` when the RESULT markdown is the governed output and no candidate
artifact package is produced. Set `RESULT_ACCEPTANCE_MODE: artifact_package`
and `ARTIFACT_PACKAGE_REQUIRED: true` when the task produces a candidate
artifact package that must be accepted before audit routing.

`REUSE_ALLOWED` must always be `false`.

`AGENT_TERMINATION_REQUIRED` must always be `true`.

The orchestrator must record lifecycle termination according to
`agent-system/02_runtime/PROFILE_AGENT_LIFECYCLE.md`.

Legacy RESULT consumers may still display or read `NEXT_REQUIRED_ACTION` as an
alias for older records, but profile agents must emit
`NEXT_RECOMMENDED_ACTION`.

Research `RECOMMENDED_NEXT_ACTION` is also advisory. It does not replace
`NEXT_RECOMMENDED_ACTION` and does not authorize requester return before audit
pass.

## Design output extension

For `ROLE: solution_architect`, the RESULT evidence or referenced design
artifact must also follow:

```text
agent-system/03_templates/DESIGN_OUTPUT_CONTRACT.md
```

The design contract sections do not replace the required RESULT fields.

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
DISPATCH_RECEIPT_REF
ALLOWED_SOURCES_REF
SOURCE_BOUNDARY_STATUS
SOURCE_BOUNDARY_SEVERITY
SOURCE_BOUNDARY_RECOMMENDED_ACTION
VALIDATED_TASK_PACKETS
```

Source-boundary severity values are:

```text
SB0_ALLOWED
SB1_REPORTING_ONLY
SB2_GOVERNANCE_WARNING
SB3_BLOCKING
SB4_INVALIDATING
```

Only `SB3_BLOCKING` and `SB4_INVALIDATING` create correction tasks. Own
handoff, own prompt, own dispatch receipt, assigned task packet, validator
error refs, accepted artifacts, and explicitly listed project sources are
allowed delivery context.

Auditor RESULT records should also include the audited worker result reference
inside `EVIDENCE` or `SCOPE_VERIFICATION` with one of these labels:

```text
SOURCE_RESULT_REF
AUDITED_RESULT_REF
RESULT_REF
ACCEPTED_RESULT_REF
```

Auditors must validate `REASONING_LEVEL_COMPLIANCE` from the dispatch receipt
at `project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json`. They must not
use stderr, terminal scrollback, or unverifiable runner claims as reasoning
evidence.

New audit result files should use:

```text
project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_<N>.md
```

New worker result files should use:

```text
project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_<N>.md
```

`project-runtime/agent-results/` is compatibility/read-only legacy storage for
historical worker RESULT evidence and must not be used for new worker RESULT
files.

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
