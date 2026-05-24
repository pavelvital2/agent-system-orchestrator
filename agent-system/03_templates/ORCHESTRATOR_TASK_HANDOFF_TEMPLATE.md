# ORCHESTRATOR_TASK_HANDOFF_TEMPLATE

Используй этот шаблон при передаче задачи новому агенту.

```text
ROLE:
<requirements_analyst | solution_architect | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager>

REASONING_LEVEL:
VALUE: low | medium | high | xhigh
OVERRIDE_REASON: <reason | NONE>

TASK_COMPLEXITY:
low | medium | high | xhigh

AGENT_LIFECYCLE_POLICY:
one_agent_one_task_delete_after_result

DISPATCH_REASONING_RECORD:
TARGET_ROLE: <same as ROLE>
DISPATCH_TASK_ID: <TASK_ID>
TASK_PACKET: <path | NONE>
REASONING_LEVEL_REQUIRED: low | medium | high | xhigh
REASONING_LEVEL_SOURCE: explicit | role_default | gate_floor | escalated | fallback
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

CONTEXT_MODE:
routine | debug | explain | violation_recovery

RUNTIME_CONTRACT:
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json
  SECTIONS: <handoff_context_builder_contract.runtime_contract_required_sections>

CURRENT_STATE_REFS:
- project-runtime/state/*.json
- project-runtime/agents/instances.jsonl

CURRENT_EVENT_RESULT_ARTIFACT_REFS:
EVENT: <event ref | NONE>
RESULT_OR_AUDIT_RESULT: <result ref | NONE>
ARTIFACT_MANIFEST_OR_RECEIPT: <artifact or receipt ref | NONE>

TASK_PACKET_TEMPLATE:
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md

UNIVERSAL_ROLE_INSTRUCTIONS:
- <specific target-role doc path only>

REQUIRED_DOCS:
- <path>
- <path>

REFERENCE_DOCS:
- <debug/explain/recovery reference path | NONE>
REFERENCE_REASON:
<explicit reason, validator-required reason, or NONE>

SCOPE:
IN:
- <allowed work item>

OUT:
- <forbidden work item>

MANDATORY_RULES:
- Work on exactly one task.
- One agent = one task = one RESULT; after RESULT the agent context is
  terminated and deleted or rendered inaccessible for future work.
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
- REASONING_LEVEL_REQUIRED must be the highest applicable level among role default, task packet REASONING_LEVEL, task packet TASK_COMPLEXITY, and gate-required floor.
- Tester handoffs require REASONING_LEVEL_REQUIRED at least high.
- Auditor handoffs require REASONING_LEVEL_REQUIRED xhigh.
- If the requested or configured runner reasoning level is below
  REASONING_LEVEL_REQUIRED, dispatch is non_compliant and the worker RESULT is
  invalid.
- Do not use unaudited research as accepted input; requester return requires independent audit pass.
- Routine context must not include the full governance corpus, all role docs,
  all templates, full changelog, release notes, or all validator docs.
- Reference docs are allowed only when CONTEXT_MODE is `debug`, `explain`, or
  `violation_recovery` and REFERENCE_REASON records an explicit request or
  validator-required reason.

EXPECTED_RESULT_FORMAT:
Use:
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

`ROLE` must be a canonical profile execution role. `solution_architect` is the
canonical design role; `designer` is accepted only as a deprecated compatibility
alias for old task packets. Control/routing pseudo-roles `orchestrator`,
`project_owner`, and `none` are not valid task handoff execution roles in this
template.
