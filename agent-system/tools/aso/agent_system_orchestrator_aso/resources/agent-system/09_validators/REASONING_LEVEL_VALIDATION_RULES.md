# REASONING_LEVEL_VALIDATION_RULES

## Purpose

This document defines validation checks for explicit reasoning level governance.

## Allowed levels

```text
low
medium
high
xhigh
```

`default`, `maximum`, and `role_default` are deprecated values and must not be
used as `REASONING_LEVEL.VALUE` in new task packets. `role_default` may be used
only as source/policy metadata, not as a level value.

## Role defaults

```yaml
ROLE_REASONING_DEFAULTS:
  orchestrator: high
  solution_architect: xhigh
  designer: xhigh          # deprecated alias, mapped to solution_architect
  researcher: high
  developer: high
  auditor: xhigh
  qa: high
  documenter: medium
  summarizer: medium
  simple_file_operator: low
```

Current profile-role compatibility mappings:

```text
requirements_analyst: high
tester: high
technical_writer: medium
devops_setup_engineer: high
release_manager: high
```

Compatibility mappings are role-default policy metadata. They do not add
allowed `REASONING_LEVEL.VALUE` strings.

Tester and auditor assignments must stay above medium. The tester floor is
`high`; the auditor floor is `xhigh`.

## Complexity floors

Every dispatchable task packet must include `TASK_COMPLEXITY` and
`REASONING_LEVEL_REQUIRED`.

```yaml
TASK_COMPLEXITY_FLOORS:
  low: low
  medium: medium
  high: high
  xhigh: xhigh
```

Complexity floors are minimums. Lifecycle/state/transition work,
security/secrets policy, audit, correction after failed audit, final
acceptance, and cross-link validation are at least `high`. Requirements
analysis and architecture/design work are `xhigh` unless an explicit governed
task packet proves a narrower lower floor without violating role defaults or
gate floors.

## Gate-required floors

```yaml
GATE_REASONING_FLOORS:
  initial_tz_analysis: xhigh
  architecture_design: xhigh
  task_decomposition: high
  implementation: high
  audit: xhigh
  checkpoint: high
  runtime_lint: medium
  docs_update: medium
  simple_file_move: low
```

Current gate names must map to the canonical floor that preserves or raises
their minimum: requirements gates map to `initial_tz_analysis`; design gates map
to `architecture_design`; final audit and audit gates map to `audit`; setup,
testing, launch, correction implementation, security policy, and cross-link
validation map to at least `implementation`; lifecycle/state/transition and
final acceptance gates require `xhigh`.

## Validation rules

- `REASONING_LEVEL.VALUE` must be one of the allowed levels:
  `low`, `medium`, `high`, or `xhigh`.
- `role_default` must not be used as `REASONING_LEVEL.VALUE`; it is valid only
  as source/policy metadata that resolves to the target role default before
  gate-floor checks.
- A task packet may raise reasoning level without `OVERRIDE_REASON`.
- A task packet may lower reasoning level only for mechanical bounded tasks and
  must include `OVERRIDE_REASON`.
- A task packet must not lower below a gate-required floor.
- `low` is allowed only for mechanical bounded tasks such as formatting,
  renaming a heading, updating a single link, adding a missing file to a
  checklist, copying a template field into schema, or normalizing naming
  without changing rules.
- `low` is forbidden for design, requirements analysis, audit, correction
  after failed audit, lifecycle/state/transition changes, security/secrets
  policy, launch/release readiness, final acceptance, and cross-link
  validation.

Violations must block dispatch and route through governed correction.

## Dispatch execution compliance

Before spawning any profile agent, the orchestrator must resolve:

```text
role_default_reasoning_level
task_packet_reasoning_level
task_complexity_floor
gate_required_floor
final_required_dispatch_level
requested_or_configured_reasoning_level
dispatch_receipt_ref
runner_config_evidence
```

`final_required_dispatch_level` is the highest applicable level among role
default, task packet `REASONING_LEVEL`, task packet `TASK_COMPLEXITY`, and
gate-required floor, using:

```text
low < medium < high < xhigh
```

The handoff, spawn log, or orchestrator transcript must record:

```text
TARGET_ROLE
TASK_ID
TASK_PACKET
TASK_COMPLEXITY
REASONING_LEVEL_REQUIRED
REASONING_LEVEL_SOURCE
REASONING_LEVEL_RESOLVED
DISPATCH_RECEIPT_REF
RUNNER_CONFIG_EVIDENCE
REASONING_LEVEL_COMPLIANCE
HANDOFF_LOG_REF
```

Allowed `REASONING_LEVEL_SOURCE` values are:

```text
explicit
role_default
gate_floor
escalated
fallback
```

If the requested or configured runner reasoning level is below required, this
is invalid dispatch:

- worker RESULT is invalid;
- audit must fail or block and must not pass;
- post-audit checkpoint is forbidden;
- commit/push are forbidden;
- routing must enter governed correction.

The task packet field `REASONING_LEVEL_REQUIRED` must match the resolved
minimum before dispatch. A mismatch is invalid dispatch unless the packet is
first corrected through governed task-packet update and audit.

## Dispatch Receipt Evidence

P58 dispatches are external-runner dispatches. Before profile-agent execution,
the orchestrator or external launcher must write:

```text
project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json
```

The dispatch receipt must conform to:

```text
agent-system/09_validators/schemas/dispatch_receipt.schema.json
```

It must record runner, model when known, reasoning_effort, prompt_ref, task_id,
role, started_at, and handoff_ref. ASO does not infer runner reasoning from
stderr or terminal output.

## Auditor compliance check

The auditor must verify reasoning-level execution compliance from task packet,
role defaults, gate-required floor, and available runner configuration evidence
from the dispatch receipt. The system must not claim knowledge of the agent's
internal reasoning level from stderr, terminal scrollback, or unverifiable
runner text.

Auditor validation must check:

```text
task packet REASONING_LEVEL
role default
gate-required floor
requested or configured runner reasoning level
no downgrade below required level
evidence from dispatch receipt and handoff
```

If the requested or configured runner reasoning level is lower than the
resolved required level, auditor `STATUS: pass` is invalid. The auditor must
return `STATUS: fail` or `STATUS: blocked`.

Auditor evidence must record:

```text
REASONING_LEVEL_COMPLIANCE: passed | failed | blocked
DISPATCH_RECEIPT_REF: project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json
```

If checkpoint preflight or later deterministic routing detects a
reasoning-level blocker after auditor `STATUS: pass`, and the auditor had the
required spawn/handoff evidence available, the orchestrator must record
`AUDIT_FALSE_PASS_DETECTED` with `FAILURE_TYPE: audit_miss` and route correction
without staging, commit, or push.
