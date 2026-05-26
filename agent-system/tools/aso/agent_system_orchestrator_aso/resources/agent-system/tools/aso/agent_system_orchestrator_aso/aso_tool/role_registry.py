"""Role registry helpers derived from the runtime contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from . import resources
from . import runtime_contract_fallback


CONTRACT_RELATIVE_PATH = Path("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json")

# Historical RESULT/state artifacts may mention these roles, but they are not
# profile-dispatch roles unless the runtime contract explicitly allows them.
LEGACY_LIFECYCLE_SYSTEM_ROLES = (
    "designer",
    "devops_setup_engineer",
    "release_manager",
)
CONTROL_OR_PSEUDO_ROLES = (
    "orchestrator",
    "project_owner",
    "owner",
    "control",
    "none",
)


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def load_contract_roles() -> dict[str, Any]:
    """Load the runtime contract role fields without importing the transition engine."""

    try:
        resource = resources.read_resource_text(CONTRACT_RELATIVE_PATH, anchor_file=__file__)
        raw_text = resource.text
    except FileNotFoundError:
        raw_text = runtime_contract_fallback.ORCHESTRATOR_RUNTIME_CONTRACT_JSON
    payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        return {}
    return payload


def dispatchable_roles(contract: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    """Return profile-dispatch roles from allowed_roles minus forbidden_dispatch_roles."""

    source = contract if contract is not None else load_contract_roles()
    allowed = _string_list(source.get("allowed_roles"))
    forbidden = set(_string_list(source.get("forbidden_dispatch_roles")))
    return tuple(role for role in allowed if role not in forbidden)


def forbidden_dispatch_roles(contract: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    source = contract if contract is not None else load_contract_roles()
    return _string_list(source.get("forbidden_dispatch_roles"))


def legacy_lifecycle_system_roles() -> tuple[str, ...]:
    return LEGACY_LIFECYCLE_SYSTEM_ROLES


def control_or_pseudo_roles(contract: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    return CONTROL_OR_PSEUDO_ROLES


def is_dispatchable_role(role: str, contract: Mapping[str, Any] | None = None) -> bool:
    return role.strip() in set(dispatchable_roles(contract))
