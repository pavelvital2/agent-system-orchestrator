# ORCHESTRATOR_TASK_HANDOFF_TEMPLATE

Используй этот шаблон при передаче задачи новому агенту.

```text
ROLE:
<requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager>

REASONING_LEVEL:
VALUE: low | medium | high | xhigh
OVERRIDE_REASON: <reason | NONE>

DISPATCH_REASONING_RECORD:
TARGET_ROLE: <same as ROLE>
DISPATCH_TASK_ID: <TASK_ID>
TASK_PACKET: <path | NONE>
REASONING_LEVEL_REQUIRED: low | medium | high | xhigh
REASONING_LEVEL_SOURCE: role_default | task_packet | gate_required_floor | highest_applicable
REASONING_LEVEL_RESOLVED: low | medium | high | xhigh
RUNNER_CONFIG_EVIDENCE: <spawn log, runner config ref, orchestrator transcript ref, or NONE>
REASONING_LEVEL_COMPLIANCE: compliant | non_compliant | unknown
SPAWN_LOG_REF: <spawn log, orchestrator transcript ref, or NONE>
HANDOFF_LOG_REF: <handoff log ref or NONE>

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
- The handoff must record the resolved required reasoning level and runner
  configuration evidence as soon as the spawn configuration is known.
- REASONING_LEVEL_REQUIRED must be the highest applicable level among role default, task packet REASONING_LEVEL, and gate-required floor.
- If the requested or configured runner reasoning level is below
  REASONING_LEVEL_REQUIRED, dispatch is non_compliant and the worker RESULT is
  invalid.
- Do not use unaudited research as accepted input; requester return requires independent audit pass.

EXPECTED_RESULT_FORMAT:
Use:
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

`ROLE` must be a canonical profile execution role. Control/routing pseudo-roles
`orchestrator`, `project_owner`, and `none` are not valid task handoff execution
roles in this template.
