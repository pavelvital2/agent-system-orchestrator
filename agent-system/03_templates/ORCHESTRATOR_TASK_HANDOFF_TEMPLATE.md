# ORCHESTRATOR_TASK_HANDOFF_TEMPLATE

Используй этот шаблон при передаче задачи новому агенту.

```text
ROLE:
<designer | developer | auditor | tester | technical_writer>

REASONING_LEVEL:
<default | high | maximum>

TASK_ID:
<TASK_ID>

TASK_TITLE:
<short title>

TASK_SOURCE:
<path to task packet or direct instruction>

TASK_PACKET_TEMPLATE:
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md

UNIVERSAL_ROLE_INSTRUCTIONS:
- <path>

REQUIRED_DOCS:
- <path>
- <path>

SCOPE:
IN:
- <allowed work item>

OUT:
- <forbidden work item>

MANDATORY_RULES:
- Work on exactly one task.
- Do not change files outside scope.
- Do not infer missing business requirements.
- If there is a gap, return STATUS: gap.
- Return result strictly using AGENT_RESULT_TEMPLATE.

EXPECTED_RESULT_FORMAT:
Use:
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```
