# DESIGN_CONTINUATION_TASK_TEMPLATE

## Purpose

Use this template for a designer continuation task after accepted research.

The continuation task resumes the original bounded design work using only
research that passed independent audit.

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

## TASK_TYPE

```text
designer
```

## TARGET_ROLE

```text
designer
```

## REASONING_LEVEL

```text
VALUE: maximum
OVERRIDE_REASON: NONE
```

## REQUESTED_BY_ROLE

```text
designer
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

- The designer must use only audited research as continuation input.
- Unaudited research, failed audit findings, or informal research notes are not
  valid continuation source-of-truth.
- Continuation scope must remain bounded to the original design task and the
  accepted research implications.
- The continuation task still routes to mandatory design audit on pass.
