# DESIGN_CONTINUATION_TASK_TEMPLATE

## Purpose

Use this template for a solution architect continuation task after accepted
research.

The continuation task resumes the original bounded design work using only
research that passed independent audit.

This file is an extension section template. It must be embedded into a full
`TASK_PACKET_TEMPLATE.md`-compatible task packet. It is schema-invalid if used
standalone.

---

# DESIGN CONTINUATION TASK

## TASK_ID

```text
<TASK_ID>
```

## TASK_STATUS

```text
active | completed | superseded | deprecated
```

## TASK_KIND

```text
design_continuation
```

## TASK_COMPLEXITY

```text
xhigh
```

## TASK_TYPE

```text
solution_architect
```

## TARGET_ROLE

```text
solution_architect
```

## AGENT_LIFECYCLE_POLICY

```text
one_agent_one_task_delete_after_result
```

## REASONING_LEVEL

```text
VALUE: xhigh
OVERRIDE_REASON: NONE
```

## REASONING_LEVEL_REQUIRED

```text
xhigh
```

## REQUESTED_BY_ROLE

```text
solution_architect
```

## REQUESTED_BY_TASK

```text
<original design task id>
```

## DEPENDENCIES

```text
- <research_dependency task id>
- <research RESULT ref>
- <audit RESULT ref with STATUS: pass>
```

## INPUTS

```text
- accepted research result reference
- accepted audit result reference
```

## READ_INPUTS

```text
- <research result path/ref>
- <audit result path/ref>
```

## RETURN_TO_REQUESTER_AFTER_AUDIT_PASS

```text
no
```

## RETURN_TO_ROLE_AFTER_AUDIT_PASS

```text
none
```

## RETURN_TASK_AFTER_AUDIT_PASS

```text
NONE
```

## Rules

- The solution architect must use only audited research as continuation input.
- Unaudited research, failed audit findings, or informal research notes are not
  valid continuation source-of-truth.
- Continuation scope must remain bounded to the original design task and the
  accepted research implications.
- The continuation task still routes to mandatory design audit on pass.
- A dispatchable design continuation artifact must be embedded in a full
  `# TASK PACKET` and pass task packet schema validation before dispatch.
- A candidate continuation that is not yet dispatchable must be emitted as a
  `TASK_PROPOSAL` with `DISPATCH_STATUS: non_dispatchable`.
- `RETURN_TO_REQUESTER_AFTER_AUDIT_PASS`,
  `RETURN_TO_ROLE_AFTER_AUDIT_PASS`, and `RETURN_TASK_AFTER_AUDIT_PASS` must
  remain deterministic and must not be inferred from research notes or
  conversation history.
