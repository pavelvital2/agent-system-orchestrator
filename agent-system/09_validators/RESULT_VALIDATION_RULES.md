# RESULT_VALIDATION_RULES

## Purpose

This document defines documentation-first validation rules for profile-agent
RESULT payloads.

## Source documents

```text
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
agent-system/03_templates/RESEARCH_RESULT_TEMPLATE.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
agent-system/02_runtime/REQUESTER_RETURN_PROTOCOL.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
```

## Required structure

A RESULT is invalid if it omits required sections from the current
`AGENT_RESULT_TEMPLATE.md`.

At minimum, validators must check:

```text
RESULT:
STATUS:
ROLE:
TASK:
SUMMARY:
CHANGED_FILES:
READ_DOCS:
EVIDENCE:
RISKS:
BLOCKERS:
GAPS:
NEXT_RECOMMENDED_ACTION:
```

If a newer template adds sections, the validator must follow the template.

`NEXT_REQUIRED_ACTION` is a legacy alias for older RESULT records. v1.2.0
validators must not require profile agents to emit it.

## STATUS validation

Profile-agent `STATUS` must be one of:

```text
pass
fail
blocked
gap
```

Invalid statuses include:

```text
violation
completed
accepted
checkpoint_done
```

`violation` is reserved for orchestrator recovery classification.

## Role and task validation

A RESULT is invalid when:

- `ROLE` does not match the dispatched `TARGET_ROLE`;
- `TASK` does not match the dispatched `TASK_ID` or task title;
- RESULT claims work from a different task packet;
- RESULT claims authority to update runtime state directly;
- RESULT claims project completion directly.

## Evidence validation

For `STATUS: pass`, RESULT must provide enough evidence to verify the task
packet acceptance criteria.

For `STATUS: fail`, `blocked`, or `gap`, RESULT must provide the reason and
the blocked or failed surface without expanding scope.

Evidence is invalid when it:

- references files the agent was not allowed to read;
- references project-specific external state not included as input;
- includes unredacted secrets;
- claims tests or commands were run without listing them when the task packet
  requires command evidence.

## File change validation

`CHANGED_FILES` must be compared to the task packet:

```text
ALLOWED_FILE_CHANGES
FORBIDDEN_FILE_CHANGES
```

The RESULT is invalid when:

- a changed path is outside allowed scope;
- a changed path matches forbidden scope;
- an ordinary project task changes `agent-system/`;
- a profile agent changes `project-runtime/`;
- a developer changes task packets or architecture docs without explicit scope;
- an auditor modifies files outside an explicitly assigned correction task.

`CHANGED_FILES: NONE` is required when no files changed.

## Secret-safety validation

RESULT is invalid if it prints or embeds:

- credentials;
- tokens;
- cookies;
- private keys;
- `.env` values;
- secret-bearing command output.

If a command or file path suggests a secret was involved, the RESULT must cite
only the command class, path, or redacted marker. It must not reproduce the
secret value.

## GAP validation

When `STATUS: gap`, the `GAPS` section must include:

- `GAP_ID`;
- `TYPE`;
- `BLOCKS`;
- `QUESTION_TO_OWNER`;
- `RECOMMENDED_OPTIONS`;
- `RECOMMENDED_OPTION`;
- `REASON`.

When no GAP exists, the section must be:

```text
GAPS:
- NONE
```

## BLOCKERS validation

When `STATUS: blocked`, the RESULT must identify a blocker or explain why an
owner decision is required.

`STATUS: blocked` with:

```text
BLOCKERS:
- NONE
```

is invalid unless the task packet explicitly defines a no-progress condition
that does not require a blocker.

## NEXT_RECOMMENDED_ACTION validation

`NEXT_RECOMMENDED_ACTION` is advisory and must not contradict governance. It is
not authoritative for routing until the orchestrator validates it against
runtime state, task registry, current gate, transition rules, blockers, and
accepted artifacts.

Legacy RESULT readers may accept `NEXT_REQUIRED_ACTION` as an alias when
reading older records, but current RESULT validation must require
`NEXT_RECOMMENDED_ACTION`.

Invalid RESULT recommendations include:

- designer pass directly to developer;
- developer pass directly to tester or technical writer;
- audit fail routed to normal next task;
- audit fail routed to Git checkpoint;
- tester fail routed to technical writer or finalization;
- profile agent directly setting project completed;
- direct progress after a required audit fail.
- direct requester continuation from unaudited research output.

The orchestrator must validate advisory action against transition rules before
updating `NEXT_ACTION.md`.

## Research result validation

For `TASK_KIND: research_dependency`, RESULT is invalid unless it includes the
additional research output fields from
`agent-system/03_templates/RESEARCH_RESULT_TEMPLATE.md`:

```text
RESEARCH_QUESTION_ID
RESEARCH_SUMMARY
SOURCES_USED
EVIDENCE_MATRIX
UNRESOLVED_FINDINGS
DESIGN_OR_TASK_IMPLICATIONS
RECOMMENDED_NEXT_ACTION
```

Research result validation must reject:

- missing source references for factual findings;
- use of forbidden sources;
- unredacted secrets;
- owner decisions treated as research findings instead of GAP;
- technical execution obstacles treated as research findings instead of
  BLOCKER;
- any recommendation that bypasses independent audit before requester return.
