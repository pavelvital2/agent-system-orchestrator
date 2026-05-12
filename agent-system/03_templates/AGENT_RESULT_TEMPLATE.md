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

CHANGED_FILES:
- <path> | NONE

READ_DOCS:
- <path>

EVIDENCE:
- <command/result/file/report> | NONE

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

NEXT_REQUIRED_ACTION:
- <next action>
```

Если GAP отсутствует, секция должна быть:

```text
GAPS:
- NONE
```

## Result authority rule

`NEXT_REQUIRED_ACTION` is advisory.

The orchestrator must validate it against:

- runtime state schema;
- state transition rules;
- governance authority;
- filesystem governance;
- active task packet lifecycle.

Agent RESULT cannot directly override governance or mark the project completed.
