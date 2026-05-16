# ORCHESTRATOR_TASK_HANDOFF_TEMPLATE

Используй этот шаблон при передаче задачи новому агенту.

```text
ROLE:
<requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager>

REASONING_LEVEL:
VALUE: low | default | high | maximum | role_default
OVERRIDE_REASON: <reason | NONE>

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
- NEXT_RECOMMENDED_ACTION is advisory, not authoritative; orchestrator validates it before routing.
- Return result strictly using AGENT_RESULT_TEMPLATE.
- Follow the assigned REASONING_LEVEL only when it satisfies role default and gate-required floor governance.
- Do not use unaudited research as accepted input; requester return requires independent audit pass.

EXPECTED_RESULT_FORMAT:
Use:
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

`ROLE` must be a canonical profile execution role. Control/routing pseudo-roles
`orchestrator`, `project_owner`, and `none` are not valid task handoff execution
roles in this template.
