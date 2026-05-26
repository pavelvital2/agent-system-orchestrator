"""Dispatch receipt contract helpers for external profile-agent launches."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from . import role_registry


RECEIPT_TYPE = "DISPATCH_RECEIPT"
SCHEMA_VERSION = "1.0.0"
SCHEMA_RELATIVE_PATH = "agent-system/09_validators/schemas/dispatch_receipt.schema.json"
TEMPLATE_RELATIVE_PATH = "agent-system/03_templates/dispatch_receipt.template.json"
RECEIPT_REF_TEMPLATE = "project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json"
RUNNER_EXTERNAL_CODEX_CLI = "external_codex_cli"
RUNNERS = (RUNNER_EXTERNAL_CODEX_CLI,)
RUNNER_SEMANTICS = (
    "ASO records dispatch evidence for an externally invoked Codex CLI run; "
    "ASO does not execute the runner, daemonize work, or mutate task outputs."
)
EXTERNAL_RUNNER_COMMAND_TEMPLATE = (
    'codex exec -C <WORKSPACE_ROOT> -m <MODEL> '
    '-c model_reasoning_effort="<REASONING_EFFORT>" - < <PROMPT_REF>'
)
WRITER_COMMAND_TEMPLATE = (
    "python3 agent-system/tools/aso/aso.py dispatch receipt "
    "--root <WORKSPACE_ROOT> "
    "--agent-instance-id <AGENT_INSTANCE_ID> "
    "--task-id <TASK_ID> "
    "--role <ROLE> "
    "--reasoning-effort <REASONING_EFFORT> "
    "--prompt-ref <PROMPT_REF> "
    "--handoff-ref <HANDOFF_REF> "
    "--runner external_codex_cli "
    "--model <MODEL_OR_UNKNOWN> "
    "--confirm-write"
)
LEVELS = ("low", "medium", "high", "xhigh")
LEVEL_RANK = {level: index for index, level in enumerate(LEVELS)}
PROFILE_ROLES = role_registry.dispatchable_roles()
AGENT_INSTANCE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}


@dataclass(frozen=True)
class DispatchReceiptValidationResult:
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def receipt_ref(agent_instance_id: str) -> str:
    return f"project-runtime/agents/dispatches/{agent_instance_id}.json"


def receipt_path(root: Path, agent_instance_id: str) -> Path:
    return root / receipt_ref(agent_instance_id)


def dispatch_receipt_plan(
    *,
    task_id: str,
    role: str,
    reasoning_effort: str,
    required: bool,
) -> dict[str, object]:
    return {
        "required": required,
        "schema_ref": SCHEMA_RELATIVE_PATH,
        "template_ref": TEMPLATE_RELATIVE_PATH,
        "receipt_ref_template": RECEIPT_REF_TEMPLATE,
        "writer_command_template": WRITER_COMMAND_TEMPLATE,
        "external_runner_command_template": EXTERNAL_RUNNER_COMMAND_TEMPLATE,
        "runner": RUNNER_EXTERNAL_CODEX_CLI,
        "runner_semantics": RUNNER_SEMANTICS,
        "task_id": task_id or "NONE",
        "role": role or "NONE",
        "reasoning_effort": reasoning_effort or "NONE",
        "live_dispatch_performed_by_aso": False,
    }


def build_dispatch_receipt(
    *,
    agent_instance_id: str,
    task_id: str,
    role: str,
    runner: str,
    model: str,
    reasoning_effort: str,
    prompt_ref: str,
    handoff_ref: str,
    started_at: str,
) -> dict[str, object]:
    ref = receipt_ref(agent_instance_id)
    return {
        "receipt_type": RECEIPT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "agent_instance_id": agent_instance_id,
        "task_id": task_id,
        "role": role,
        "runner": runner,
        "runner_semantics": RUNNER_SEMANTICS,
        "model": model or "UNKNOWN",
        "reasoning_effort": reasoning_effort,
        "prompt_ref": prompt_ref,
        "handoff_ref": handoff_ref,
        "started_at": started_at,
        "receipt_ref": ref,
        "receipt_path": ref,
        "external_runner_command_template": EXTERNAL_RUNNER_COMMAND_TEMPLATE,
        "live_dispatch_performed_by_aso": False,
    }


def validate_dispatch_receipt(payload: Mapping[str, Any]) -> DispatchReceiptValidationResult:
    errors: list[str] = []
    required = (
        "receipt_type",
        "schema_version",
        "agent_instance_id",
        "runner",
        "model",
        "reasoning_effort",
        "prompt_ref",
        "task_id",
        "role",
        "started_at",
        "handoff_ref",
        "receipt_ref",
        "external_runner_command_template",
        "live_dispatch_performed_by_aso",
    )
    for field in required:
        if field not in payload:
            errors.append(f"{field} is required")

    if payload.get("receipt_type") != RECEIPT_TYPE:
        errors.append(f"receipt_type must be {RECEIPT_TYPE}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    agent_instance_id = _text(payload.get("agent_instance_id"))
    if not agent_instance_id or not AGENT_INSTANCE_ID_RE.match(agent_instance_id):
        errors.append("agent_instance_id must contain only letters, numbers, underscore, dash, colon, or dot")
    elif _text(payload.get("receipt_ref")) != receipt_ref(agent_instance_id):
        errors.append(f"receipt_ref must be {receipt_ref(agent_instance_id)}")

    runner = _text(payload.get("runner"))
    if runner not in RUNNERS:
        errors.append(f"runner must be one of {', '.join(RUNNERS)}")
    if _text(payload.get("external_runner_command_template")) != EXTERNAL_RUNNER_COMMAND_TEMPLATE:
        errors.append("external_runner_command_template must match the dispatch receipt contract")
    if payload.get("live_dispatch_performed_by_aso") is not False:
        errors.append("live_dispatch_performed_by_aso must be false")

    for field in ("task_id", "prompt_ref", "handoff_ref"):
        value = _text(payload.get(field))
        if value in NONE_VALUES:
            errors.append(f"{field} must be a concrete non-empty reference")
    if _text(payload.get("role")) not in PROFILE_ROLES:
        errors.append("role must be a runtime-contract dispatchable profile role")
    if _text(payload.get("reasoning_effort")) not in LEVEL_RANK:
        errors.append("reasoning_effort must be one of low, medium, high, xhigh")
    model = _text(payload.get("model"))
    if not model:
        errors.append("model must be a string; use UNKNOWN when the external runner uses configured defaults")

    started_at = _text(payload.get("started_at"))
    if not RFC3339_UTC_RE.match(started_at):
        errors.append("started_at must be RFC3339 UTC with Z suffix")
    else:
        try:
            datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("started_at must be a valid RFC3339 timestamp")

    return DispatchReceiptValidationResult(tuple(errors))


def load_dispatch_receipt(root: Path, agent_instance_id: str) -> tuple[dict[str, Any] | None, str]:
    path = receipt_path(root, agent_instance_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, f"dispatch receipt is missing or unreadable: {receipt_ref(agent_instance_id)}: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"dispatch receipt is invalid JSON: {receipt_ref(agent_instance_id)}: {exc}"
    if not isinstance(payload, dict):
        return None, f"dispatch receipt root must be an object: {receipt_ref(agent_instance_id)}"
    return payload, ""


def reasoning_compliance_from_receipt(root: Path, agent_instance_id: str, required_level: str) -> dict[str, object]:
    payload, error = load_dispatch_receipt(root, agent_instance_id)
    if payload is None:
        return {
            "status": "blocked",
            "receipt_ref": receipt_ref(agent_instance_id),
            "required_reasoning_level": required_level,
            "reasoning_effort": "NONE",
            "errors": [error],
        }
    validation = validate_dispatch_receipt(payload)
    effort = _text(payload.get("reasoning_effort"))
    required_rank = LEVEL_RANK.get(required_level, -1)
    effort_rank = LEVEL_RANK.get(effort, -1)
    errors = list(validation.errors)
    if required_rank < 0:
        errors.append(f"required_level is not valid: {required_level or 'NONE'}")
    if effort_rank >= 0 and required_rank >= 0 and effort_rank < required_rank:
        errors.append(f"reasoning_effort={effort} is below required_level={required_level}")
    status = "passed" if not errors else "failed"
    return {
        "status": status,
        "receipt_ref": receipt_ref(agent_instance_id),
        "required_reasoning_level": required_level,
        "reasoning_effort": effort or "NONE",
        "runner": _text(payload.get("runner")) or "NONE",
        "model": _text(payload.get("model")) or "UNKNOWN",
        "errors": errors,
    }


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
