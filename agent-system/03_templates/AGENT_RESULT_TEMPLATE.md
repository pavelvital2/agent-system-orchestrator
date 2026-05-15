# AGENT_RESULT_TEMPLATE

Каждый агент обязан вернуть RESULT строго в этом формате.

```text
RESULT:
STATUS: pass | fail | blocked | gap

ROLE:
<designer | developer | auditor | tester | technical_writer>

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

Legacy RESULT consumers may still display `NEXT_REQUIRED_ACTION`, but profile agents must emit `NEXT_RECOMMENDED_ACTION`.
