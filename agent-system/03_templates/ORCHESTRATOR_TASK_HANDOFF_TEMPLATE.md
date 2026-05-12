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
- Use only REQUIRED_DOCS.
- Do not use deprecated, superseded, or archived documents as source-of-truth.
- Do not modify `project-runtime/`.
- Do not modify `agent-system/` unless this is an explicit universal-package update task.
- Do not treat missing information as permission to infer.
- If task packet conflicts with governance or scope, return STATUS: blocked or gap.
- NEXT_REQUIRED_ACTION is advisory; orchestrator validates it.
- Return result strictly using AGENT_RESULT_TEMPLATE.

EXPECTED_RESULT_FORMAT:
Use:
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```
