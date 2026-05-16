# RESEARCH_REQUEST_TEMPLATE

## Purpose

Use this template for a bounded research dependency task packet.

Research dependency tasks collect factual evidence for a requester. They do not
make business decisions, replace owner GAP handling, or return to the requester
before audit pass.

---

# RESEARCH REQUEST

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
research_dependency
```

## TASK_TYPE

```text
requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager
```

## TARGET_ROLE

```text
<single profile execution role that will perform the research>
```

## REASONING_LEVEL

```text
VALUE: role_default | high | maximum
OVERRIDE_REASON: NONE
```

Research dependency tasks must not use `low`.

## REQUESTED_BY_ROLE

```text
<requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager>
```

## REQUESTED_BY_TASK

```text
<TASK_ID>
```

## RESEARCH_QUESTION_ID

```text
<stable question id>
```

## RESEARCH_PURPOSE

```text
<why the requester cannot safely continue without this evidence>
```

## RESEARCH_QUESTIONS

```text
- <exact factual question>
```

## ALLOWED_SOURCES

```text
- <allowed source path, API doc, code area, log class, web/source class, or NONE>
```

## FORBIDDEN_SOURCES

```text
- secrets, credentials, private tokens, deprecated docs, project-archive active use, or other forbidden source>
```

## EXPECTED_EVIDENCE

```text
- <required evidence type, source citation, command output class, matrix row, or NONE>
```

## EXPECTED_OUTPUT

```text
- research result using agent-system/03_templates/RESEARCH_RESULT_TEMPLATE.md
- RESULT using agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

## RETURN_TO_REQUESTER_AFTER_AUDIT_PASS

```text
yes | no
```

## RETURN_TO_ROLE_AFTER_AUDIT_PASS

```text
<requester role | none>
```

## RETURN_TASK_AFTER_AUDIT_PASS

```text
<continuation task id or task packet | NONE>
```

## AUDIT_REQUIREMENTS

```text
mandatory
```

## Rules

- A research dependency is distinct from GAP and BLOCKER.
- Missing owner decisions must be returned as GAP, not research dependency.
- Technical execution obstacles must be returned as blocked, not research
  dependency.
- Research output is advisory until independent audit pass.
- The orchestrator must not return research to requester continuation before
  audit pass.
- Research tasks must not grant commit or push authority to profile agents.
