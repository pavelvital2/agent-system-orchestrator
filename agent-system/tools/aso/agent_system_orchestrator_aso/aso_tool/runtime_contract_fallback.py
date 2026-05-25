"""Embedded runtime contract fallback for installed ASO packages."""

from __future__ import annotations


ORIGIN = "agent_system_orchestrator_aso.aso_tool.runtime_contract_fallback"

ORCHESTRATOR_RUNTIME_CONTRACT_JSON = r"""{
  "contract_version": "1.0.0",
  "package_version": "3.7.9",
  "governance_ruleset_version": "3.7.9",
  "runtime_schema_version": "3.1.1",
  "artifact_package_schema_version": "1.1.0",
  "allowed_roles": [
    "requirements_analyst",
    "solution_architect",
    "developer",
    "tester",
    "auditor",
    "technical_writer"
  ],
  "forbidden_dispatch_roles": [
    "orchestrator",
    "owner",
    "control",
    "release_manager"
  ],
  "allowed_events": [
    "CREATE_AGENT_RECOMMENDED",
    "CREATE_AGENT_DISPATCHED",
    "RESULT_RECEIVED",
    "ARTIFACT_ACCEPTED",
    "AGENT_TERMINATED",
    "AUDIT_ROUTE_READY",
    "AUDIT_RESULT_RECEIVED_PASS",
    "AUDIT_RESULT_RECEIVED_FAIL",
    "CORRECTION_REQUIRED",
    "CHECKPOINT_ELIGIBLE"
  ],
  "event_aliases": {
    "agent_task_dispatched": "CREATE_AGENT_DISPATCHED",
    "agent_result_received": "RESULT_RECEIVED",
    "artifact_accepted": "ARTIFACT_ACCEPTED",
    "agent_instance_terminated": "AGENT_TERMINATED",
    "AGENT_TERMINATED": "AGENT_TERMINATED",
    "AUDITOR_AGENT_TERMINATED": "AGENT_TERMINATED",
    "auditor_agent_terminated": "AGENT_TERMINATED",
    "audit_route_ready": "AUDIT_ROUTE_READY",
    "AUDIT_RESULT_RECEIVED": {
      "pass": "AUDIT_RESULT_RECEIVED_PASS",
      "fail": "AUDIT_RESULT_RECEIVED_FAIL"
    }
  },
  "state_transitions": {
    "TASK_READY": {
      "CREATE_AGENT_DISPATCHED": "AGENT_RUNNING"
    },
    "AGENT_RUNNING": {
      "RESULT_RECEIVED": "RESULT_PENDING_ARTIFACT_ACCEPTANCE"
    },
    "RESULT_PENDING_ARTIFACT_ACCEPTANCE": {
      "ARTIFACT_ACCEPTED": "RESULT_ACCEPTED"
    },
    "RESULT_ACCEPTED": {
      "AGENT_TERMINATED": "AGENT_TERMINATED"
    },
    "AGENT_TERMINATED": {
      "AUDIT_ROUTE_READY": "AUDIT_PENDING"
    },
    "AUDIT_PENDING": {
      "AUDIT_RESULT_RECEIVED_PASS": "CHECKPOINT_ELIGIBLE",
      "AUDIT_RESULT_RECEIVED_FAIL": "CORRECTION_REQUIRED"
    },
    "CORRECTION_REQUIRED": {
      "CREATE_AGENT_DISPATCHED": "CORRECTION_AGENT_RUNNING"
    }
  },
  "terminal_states": [
    "CHECKPOINT_ELIGIBLE"
  ],
  "forbidden_transitions": [
    {
      "from_states": [
        "AGENT_RUNNING",
        "RESULT_PENDING_ARTIFACT_ACCEPTANCE",
        "RESULT_ACCEPTED",
        "AGENT_TERMINATED",
        "AUDIT_PENDING",
        "CORRECTION_REQUIRED",
        "CHECKPOINT_ELIGIBLE"
      ],
      "event": "CREATE_AGENT_DISPATCHED",
      "same_task": true,
      "reason": "duplicate dispatch forbidden after lifecycle progress"
    },
    {
      "from_states": [
        "CORRECTION_REQUIRED"
      ],
      "event": "CHECKPOINT_ELIGIBLE",
      "reason": "audit fail must route correction before checkpoint"
    }
  ],
  "next_actions_by_state": {
    "TASK_READY": {
      "recommended_next_action": "CREATE_AGENT",
      "action_type": "create_agent",
      "target_role_source": "task_or_gate",
      "dispatchable": true
    },
    "AGENT_RUNNING": {
      "recommended_next_action": "WAIT_FOR_RESULT",
      "action_type": "route_result",
      "target_role": "orchestrator",
      "dispatchable": false
    },
    "RESULT_PENDING_ARTIFACT_ACCEPTANCE": {
      "recommended_next_action": "ACCEPT_ARTIFACT",
      "action_type": "update_state",
      "target_role": "orchestrator",
      "dispatchable": false
    },
    "RESULT_ACCEPTED": {
      "recommended_next_action": "TERMINATE_AGENT",
      "action_type": "update_state",
      "target_role": "orchestrator",
      "dispatchable": false
    },
    "AGENT_TERMINATED": {
      "recommended_next_action": "CREATE_AUDITOR",
      "action_type": "create_agent",
      "target_role": "auditor",
      "dispatchable": true
    },
    "AUDIT_PENDING": {
      "recommended_next_action": "WAIT_FOR_AUDIT_RESULT",
      "action_type": "route_result",
      "target_role": "auditor",
      "dispatchable": false
    },
    "CORRECTION_REQUIRED": {
      "recommended_next_action": "CORRECTION_REQUIRED",
      "action_type": "correction",
      "target_role": "orchestrator",
      "dispatchable": false
    },
    "CORRECTION_AGENT_RUNNING": {
      "recommended_next_action": "WAIT_FOR_RESULT",
      "action_type": "route_result",
      "target_role": "orchestrator",
      "dispatchable": false
    },
    "CHECKPOINT_ELIGIBLE": {
      "recommended_next_action": "CHECKPOINT_PREFLIGHT",
      "action_type": "update_state",
      "target_role": "orchestrator",
      "checkpoint_policy": "local_only",
      "dispatchable": false
    },
    "OWNER_INPUT_REQUIRED": {
      "recommended_next_action": "ASK_OWNER",
      "action_type": "wait_for_owner",
      "target_role": "project_owner",
      "dispatchable": false
    },
    "TERMINAL_STOP": {
      "recommended_next_action": "STOP",
      "action_type": "stop",
      "target_role": "none",
      "dispatchable": false
    }
  },
  "next_action_aliases": {
    "CORRECTION_REQUIRED": [
      "ROUTE_CORRECTION"
    ],
    "WAIT_FOR_RESULT": [
      "ROUTE_RESULT"
    ],
    "WAIT_FOR_AUDIT_RESULT": [
      "ROUTE_RESULT"
    ]
  },
  "required_docs_by_role": {
    "requirements_analyst": [
      "current_task_packet",
      "project-input/TZ.md",
      "agent_result_template",
      "artifact_contract_summary"
    ],
    "solution_architect": [
      "current_task_packet",
      "accepted_requirements_artifact_manifest",
      "agent_result_template",
      "artifact_contract_summary"
    ],
    "developer": [
      "current_task_packet",
      "accepted_design_artifact_manifest",
      "agent_result_template",
      "artifact_contract_summary"
    ],
    "tester": [
      "current_test_packet",
      "implementation_result",
      "test_result_template"
    ],
    "auditor": [
      "current_audit_packet",
      "accepted_artifact_manifest",
      "audit_result_template",
      "audit_rules_summary"
    ],
    "technical_writer": [
      "current_task_packet",
      "accepted_artifact_manifest",
      "agent_result_template"
    ]
  },
  "reasoning_floor_by_role": {
    "requirements_analyst": "xhigh",
    "solution_architect": "xhigh",
    "developer": "high",
    "tester": "high",
    "auditor": "xhigh",
    "technical_writer": "medium"
  },
  "dispatch_receipt_contract": {
    "schema_ref": "agent-system/09_validators/schemas/dispatch_receipt.schema.json",
    "template_ref": "agent-system/03_templates/dispatch_receipt.template.json",
    "receipt_ref_template": "project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json",
    "required_fields": [
      "runner",
      "model",
      "reasoning_effort",
      "prompt_ref",
      "task_id",
      "role",
      "started_at",
      "handoff_ref"
    ],
    "runner": "external_codex_cli",
    "runner_semantics": "ASO records dispatch evidence for an externally invoked Codex CLI run; ASO does not execute the runner, daemonize work, or mutate task outputs.",
    "external_runner_command_template": "codex exec -C <WORKSPACE_ROOT> -m <MODEL> -c model_reasoning_effort=\"<REASONING_EFFORT>\" - < <PROMPT_REF>",
    "writer_command_template": "python3 agent-system/tools/aso/aso.py dispatch receipt --root <WORKSPACE_ROOT> --agent-instance-id <AGENT_INSTANCE_ID> --task-id <TASK_ID> --role <ROLE> --reasoning-effort <REASONING_EFFORT> --prompt-ref <PROMPT_REF> --handoff-ref <HANDOFF_REF> --runner external_codex_cli --model <MODEL_OR_UNKNOWN> --confirm-write",
    "live_dispatch_performed_by_aso": false
  },
  "artifact_contracts": {
    "candidate_manifest_canonical": "manifest.json",
    "candidate_manifest_legacy_aliases": [
      "artifact_package_manifest.json"
    ],
    "accepted_manifest_canonical": "manifest.json"
  },
  "audit_gate_rules": {
    "audit_pass_allows_checkpoint": true,
    "audit_fail_routes_correction": true,
    "audit_fail_blocks_checkpoint": true
  },
  "checkpoint_rules": {
    "requires_audit_pass": true,
    "requires_no_open_lifecycle_blockers": true,
    "requires_state_consistency": true
  },
  "routine_context_policy": {
    "orchestrator_must_read": [
      "ORCHESTRATOR_RUNTIME_CONTRACT.json",
      "project-runtime/state/*.json",
      "project-runtime/agents/instances.jsonl",
      "current_task_packet",
      "current_result_or_audit_result",
      "current_artifact_manifest_or_receipt"
    ],
    "orchestrator_must_not_read_routinely": [
      "all_role_docs",
      "all_templates",
      "full_changelog",
      "all_validator_docs",
      "release_notes",
      "historical_contracts"
    ],
    "reference_docs_allowed_only_for": [
      "bootstrap",
      "debug",
      "violation_recovery",
      "audit_dispute",
      "specific_validator_reference"
    ]
  },
  "handoff_context_builder_contract": {
    "normal_context_mode": "routine",
    "allowed_context_modes": [
      "routine",
      "debug",
      "explain",
      "violation_recovery"
    ],
    "runtime_contract_required_sections": [
      "allowed_roles",
      "forbidden_dispatch_roles",
      "allowed_events",
      "event_aliases",
      "state_transitions",
      "forbidden_transitions",
      "next_actions_by_state",
      "required_docs_by_role",
      "reasoning_floor_by_role",
      "dispatch_receipt_contract",
      "artifact_contracts",
      "audit_gate_rules",
      "checkpoint_rules",
      "routine_context_policy",
      "handoff_context_builder_contract"
    ],
    "routine_handoff_includes": [
      "runtime_contract_required_sections",
      "project-runtime/state/*.json",
      "project-runtime/agents/instances.jsonl",
      "current_task_packet",
      "current_event_reference",
      "current_result_or_audit_result_reference",
      "current_artifact_manifest_or_receipt_reference",
      "specific_target_role_doc",
      "target_role_required_doc_tokens"
    ],
    "routine_handoff_excludes": [
      "agent-system/01_roles/",
      "agent-system/03_templates/",
      "agent-system/GOVERNANCE_CHANGELOG.md",
      "agent-system/11_release/",
      "agent-system/09_validators/"
    ],
    "reference_doc_inclusion_rule": "Reference docs outside routine_handoff_includes require context_mode debug, explain, or violation_recovery plus either an explicit reference_reason or validator_required=true.",
    "target_role_doc_map": {
      "requirements_analyst": "agent-system/01_roles/REQUIREMENTS_ANALYST.md",
      "solution_architect": "agent-system/01_roles/SOLUTION_ARCHITECT.md",
      "developer": "agent-system/01_roles/DEVELOPER.md",
      "tester": "agent-system/01_roles/TESTER.md",
      "auditor": "agent-system/01_roles/AUDITOR.md",
      "technical_writer": "agent-system/01_roles/TECHNICAL_WRITER.md"
    }
  }
}
"""
