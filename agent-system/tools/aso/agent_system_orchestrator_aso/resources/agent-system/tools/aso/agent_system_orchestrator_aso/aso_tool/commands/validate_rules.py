"""Read-only governance rule registry validation."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .. import resources


REGISTRY_RELATIVE_PATH = Path("agent-system/09_validators/rules/governance_rules.json")
REQUIRED_RULE_FIELDS = {
    "id",
    "severity",
    "source_docs",
    "check_target",
    "trigger",
    "expected_action",
    "rationale",
}
ALLOWED_SEVERITIES = {"info", "warning", "error", "critical"}
ALLOWED_ACTIONS = {
    "block",
    "block_unbounded_mutation",
    "warn",
    "record_gap",
    "redact",
    "reject",
    "require_audit_pass",
    "require_checkpoint_preflight",
    "require_correction",
    "require_identity_pass",
    "require_local_runtime_artifact_roots",
    "require_owner_input",
    "require_repository_lock",
    "require_receipt",
    "require_state_verify",
    "route_to_auditor",
    "stop",
    "validate_schema",
    "validate_scope",
    "validate_traceability",
    "validate_transition",
}
RULE_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")


def _as_root_path(value: object) -> Path:
    if isinstance(value, Path):
        return value.expanduser()
    return Path(str(value)).expanduser()


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _json_type(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


class RuleRegistryValidator:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.registry_path = REGISTRY_RELATIVE_PATH
        self.registry_origin = ""
        self.attempted_paths: list[str] = []
        self._using_root_registry = False
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.rule_count = 0

    def validate(self) -> None:
        registry = self._load_registry()
        if registry is None:
            return

        if not isinstance(registry, dict):
            self.errors.append(f"registry root must be an object, got {_json_type(registry)}")
            return

        self._validate_registry_object(registry)

    def _load_registry(self) -> Any | None:
        root_registry = self.root / REGISTRY_RELATIVE_PATH
        if root_registry.is_file():
            self._using_root_registry = True
            self.registry_origin = str(root_registry)
            self.attempted_paths = [str(root_registry)]
            try:
                return json.loads(root_registry.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                self.errors.append(f"registry JSON is invalid at line {exc.lineno}, column {exc.colno}: {exc.msg}")
                return None
            except OSError as exc:
                self.errors.append(f"registry file is unreadable: {exc}")
                return None

        try:
            resource = resources.read_resource_text(REGISTRY_RELATIVE_PATH, anchor_file=__file__)
            self.registry_origin = resource.origin
            self.attempted_paths = list(resource.attempted_paths)
            return json.loads(resource.text)
        except json.JSONDecodeError as exc:
            self.errors.append(f"registry JSON is invalid at line {exc.lineno}, column {exc.colno}: {exc.msg}")
            return None
        except OSError as exc:
            self.errors.append(
                "registry file is unreadable: "
                f"{exc}. Attempted paths: {self.attempted_paths or [REGISTRY_RELATIVE_PATH.as_posix()]}. "
                "Reinstall agent-system-orchestrator from a complete source archive, or run the direct script from "
                "an ASO source checkout."
            )
            return None

    def _validate_registry_object(self, registry: dict[str, Any]) -> None:
        if not _non_empty_string(registry.get("schema_version")):
            self.errors.append("schema_version must be a non-empty string")
        if not _non_empty_string(registry.get("registry_id")):
            self.errors.append("registry_id must be a non-empty string")

        rules = registry.get("rules")
        if not isinstance(rules, list) or not rules:
            self.errors.append("rules must be a non-empty array")
            return

        self.rule_count = len(rules)
        seen_ids: dict[str, int] = {}
        for index, rule in enumerate(rules):
            location = f"rules[{index}]"
            if not isinstance(rule, dict):
                self.errors.append(f"{location} must be an object, got {_json_type(rule)}")
                continue
            self._validate_rule(rule, location, seen_ids)

    def _validate_rule(self, rule: dict[str, Any], location: str, seen_ids: dict[str, int]) -> None:
        missing = sorted(REQUIRED_RULE_FIELDS - rule.keys())
        for field in missing:
            self.errors.append(f"{location}.{field} is required")

        rule_id = rule.get("id")
        if _non_empty_string(rule_id):
            rule_id_text = str(rule_id)
            if not RULE_ID_RE.fullmatch(rule_id_text):
                self.errors.append(f"{location}.id has invalid format: {rule_id_text}")
            if rule_id_text in seen_ids:
                self.errors.append(f"{location}.id duplicates rules[{seen_ids[rule_id_text]}].id: {rule_id_text}")
            else:
                seen_ids[rule_id_text] = int(location.removeprefix("rules[").removesuffix("]"))
        elif "id" in rule:
            self.errors.append(f"{location}.id must be a non-empty string")

        severity = rule.get("severity")
        if severity not in ALLOWED_SEVERITIES:
            self.errors.append(
                f"{location}.severity must be one of {sorted(ALLOWED_SEVERITIES)}, got {severity!r}"
            )

        self._validate_source_docs(rule.get("source_docs"), location)

        for field in ("check_target", "trigger", "rationale"):
            if field in rule and not _non_empty_string(rule.get(field)):
                self.errors.append(f"{location}.{field} must be a non-empty string")

        self._validate_expected_action(rule.get("expected_action"), location)

    def _validate_source_docs(self, source_docs: Any, location: str) -> None:
        if not isinstance(source_docs, list) or not source_docs:
            self.errors.append(f"{location}.source_docs must be a non-empty array")
            return

        for doc_index, source_doc in enumerate(source_docs):
            doc_location = f"{location}.source_docs[{doc_index}]"
            if not _non_empty_string(source_doc):
                self.errors.append(f"{doc_location} must be a non-empty string")
                continue

            doc_path = Path(source_doc)
            if doc_path.is_absolute() or ".." in doc_path.parts:
                self.errors.append(f"{doc_location} must be a repository-relative path without parent traversal")
                continue

            if self._using_root_registry:
                exists = (self.root / doc_path).is_file()
            else:
                exists = resources.resource_exists(doc_path, anchor_file=__file__)
            if not exists:
                self.errors.append(f"{doc_location} does not exist: {doc_path.as_posix()}")

    def _validate_expected_action(self, expected_action: Any, location: str) -> None:
        if isinstance(expected_action, str):
            actions = [expected_action]
        elif isinstance(expected_action, list):
            actions = expected_action
        else:
            self.errors.append(f"{location}.expected_action must be a non-empty string or array")
            return

        if not actions:
            self.errors.append(f"{location}.expected_action must not be empty")
            return

        for action_index, action in enumerate(actions):
            action_location = f"{location}.expected_action[{action_index}]"
            if not _non_empty_string(action):
                self.errors.append(f"{action_location} must be a non-empty string")
                continue
            if action not in ALLOWED_ACTIONS:
                self.errors.append(
                    f"{action_location} must be one of {sorted(ALLOWED_ACTIONS)}, got {action!r}"
                )

    def report(self, *, strict: bool) -> dict[str, Any]:
        failed = bool(self.errors) or (strict and bool(self.warnings))
        return {
            "status": "failed" if failed else "passed",
            "strict": strict,
            "registry_path": REGISTRY_RELATIVE_PATH.as_posix(),
            "registry_origin": self.registry_origin,
            "attempted_paths": self.attempted_paths,
            "rule_count": self.rule_count,
            "allowed_severities": sorted(ALLOWED_SEVERITIES),
            "allowed_actions": sorted(ALLOWED_ACTIONS),
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _write_json_report(path_text: str, report: dict[str, Any]) -> None:
    path = Path(path_text).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run(args: Any) -> int:
    root = _as_root_path(args.root)
    validator = RuleRegistryValidator(root)
    validator.validate()
    report = validator.report(strict=bool(getattr(args, "strict", False)))

    json_out = getattr(args, "json_out", None)
    if json_out:
        _write_json_report(str(json_out), report)

    print(
        f"validate-rules: {report['status']} "
        f"({report['rule_count']} rules, {len(report['errors'])} errors, {len(report['warnings'])} warnings)",
        file=sys.stderr if report["status"] == "failed" else sys.stdout,
    )

    return 0 if report["status"] == "passed" else 1
