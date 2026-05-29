"""Read-only checkpoint eligibility preflight command."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .. import correction_routing, transition_engine
from . import package_checks, plan_next, state_verify


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_IO_ERROR = 3

BLOCKING_CHECKPOINT_ELIGIBILITY = {"blocked"}
BLOCKING_CHECKPOINT_ELIGIBILITY_STATUS = {"blocked", "ineligible"}


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in plan_next.NONE_VALUES)


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _content(sidecars: dict[str, dict[str, object]], sidecar_type: str) -> dict[str, object]:
    payload = sidecars.get(sidecar_type, {})
    content = payload.get("content")
    return content if isinstance(content, dict) else {}


def _blocking_rule(
    rule_id: str,
    message: str,
    evidence: str,
    *,
    severity: str = "error",
    path: str = "",
    recommendation: str = "",
) -> dict[str, object]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "evidence": evidence,
        "path": path,
        "recommendation": recommendation,
    }


def _warning(rule_id: str, message: str, evidence: str, *, path: str = "") -> dict[str, object]:
    return {
        "rule_id": rule_id,
        "severity": "warning",
        "message": message,
        "evidence": evidence,
        "path": path,
    }


def _summary(blocking_rules: list[dict[str, object]], warnings: list[dict[str, object]]) -> dict[str, int]:
    return {
        "blocking_rules": len(blocking_rules),
        "warnings": len(warnings),
    }


def _dedupe(items: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[object, object, object]] = set()
    deduped: list[dict[str, object]] = []
    for item in items:
        key = (item.get("rule_id"), item.get("path"), item.get("evidence"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _git_worktree_status(root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    evidence: dict[str, object] = {
        "git_available": False,
        "inside_worktree": False,
        "toplevel": "",
        "commands_invoked": [
            "git -C <root> rev-parse --is-inside-work-tree",
            "git -C <root> rev-parse --show-toplevel",
        ],
    }
    blockers: list[dict[str, object]] = []
    try:
        inside = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        blockers.append(
            _blocking_rule(
                "CHECKPOINT-PKG-GIT-001",
                "Git is unavailable, so checkpoint preflight cannot verify the package repository.",
                "git executable was not found",
                recommendation="Run checkpoint-preflight in an environment with git available.",
            )
        )
        return evidence, blockers

    evidence["git_available"] = True
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        blockers.append(
            _blocking_rule(
                "CHECKPOINT-PKG-GIT-002",
                "Package checkpoint preflight requires a Git worktree.",
                (inside.stderr or inside.stdout or "not inside a Git worktree").strip(),
                recommendation="Run package mode from the ASO package repository root.",
            )
        )
        return evidence, blockers

    evidence["inside_worktree"] = True
    top = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        check=False,
        text=True,
        capture_output=True,
    )
    if top.returncode == 0:
        evidence["toplevel"] = top.stdout.strip()
    return evidence, blockers


def _package_report(root: Path, strict: bool) -> tuple[dict[str, object], int]:
    inspection = package_checks.inspect_package(root)
    git_evidence, git_blockers = _git_worktree_status(root)

    blocking_rules = list(git_blockers)
    warnings: list[dict[str, object]] = []
    for finding in inspection.findings:
        target = blocking_rules if finding.severity == "error" else warnings
        target.append(
            _blocking_rule(
                finding.rule_id,
                finding.details,
                finding.title,
                severity=finding.severity,
                path=finding.files[0] if finding.files else "",
                recommendation=finding.recommendation,
            )
        )

    if strict:
        blocking_rules.extend(
            _blocking_rule(
                str(item["rule_id"]),
                str(item["message"]),
                str(item["evidence"]),
                path=str(item.get("path", "")),
                recommendation="Strict mode treats checkpoint preflight warnings as blockers.",
            )
            for item in warnings
        )

    blocking_rules = _dedupe(blocking_rules)
    warnings = _dedupe(warnings)
    io_error = any(item.get("rule_id") == "PACKAGE_IO_001" for item in blocking_rules)
    eligible = not blocking_rules and not io_error
    status = "eligible" if eligible else ("io_error" if io_error else "blocked")

    return {
        "tool": "aso",
        "command": "checkpoint-preflight",
        "mode": "package",
        "status": status,
        "eligible": eligible,
        "root": str(root),
        "strict": strict,
        "read_only": True,
        "dry_run": True,
        "mutations_performed": False,
        "blocking_rules": blocking_rules,
        "warnings": warnings,
        "summary": _summary(blocking_rules, warnings),
        "evidence": {
            "package_consistency": package_checks.consistency(inspection.findings),
            "generated_roots": inspection.generated_roots,
            "git_tracked_generated_files": inspection.git_tracked_generated_files,
            "git": git_evidence,
            "script_integration": {
                "checkpoint_preflight_sh_invoked": False,
                "reason": "Python package-mode checks are read-only and do not invoke the shell preflight.",
            },
        },
    }, EXIT_OK if eligible else (EXIT_IO_ERROR if io_error else EXIT_BLOCKED)


def _tasks_by_id(sidecars: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    tasks = _content(sidecars, "TASK_REGISTRY").get("tasks")
    result: dict[str, dict[str, object]] = {}
    if isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict) and isinstance(task.get("task_id"), str):
                result[task["task_id"]] = task
    return result


def _active_blockers(project_state: dict[str, object], next_action: dict[str, object]) -> list[str]:
    blockers: list[str] = []
    for key in ("active_blockers", "checkpoint_blocked_by"):
        value = project_state.get(key)
        if isinstance(value, list):
            blockers.extend(str(item).strip() for item in value if not _is_none(item))
    value = next_action.get("blocked_by")
    if isinstance(value, list):
        blockers.extend(str(item).strip() for item in value if not _is_none(item))
    return sorted(set(item for item in blockers if item))


def _audit_pass_evidence(
    root: Path,
    sidecars: dict[str, dict[str, object]],
    task: dict[str, object],
    task_id: str,
) -> dict[str, object]:
    return transition_engine.audit_pass_evidence_from_sidecars(root, sidecars, task_id=task_id)


def _transition_engine_evidence(root: Path, sidecars: dict[str, dict[str, object]]) -> dict[str, object]:
    try:
        contract = transition_engine.load_runtime_contract()
        return transition_engine.routing_authority_report(contract, sidecars, root=root)
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return {
            "allowed": False,
            "contract_authoritative": True,
            "canonical_recommended_next_action": "NONE",
            "findings": [
                {
                    "rule_id": "RUNTIME_CONTRACT_LOAD_FAILED",
                    "severity": "error",
                    "message": "Runtime contract could not be loaded.",
                    "evidence": str(exc),
                    "recommendation": "Restore ORCHESTRATOR_RUNTIME_CONTRACT.json before checkpoint routing.",
                }
            ],
            "reference_docs_used": [transition_engine.CONTRACT_RELATIVE_PATH.as_posix()],
        }


def _state_verify_blockers(verify_report: dict[str, object]) -> list[dict[str, object]]:
    findings = verify_report.get("findings")
    if not isinstance(findings, list):
        return []
    blockers: list[dict[str, object]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        if finding.get("severity") != "error":
            continue
        rule_id = str(finding.get("rule_id", "UNKNOWN"))
        mapped_rule = "GOV-CHECKPOINT-AUDIT-GATE" if rule_id == "SIDECAR_CHECKPOINT_POLICY_INVALID" else "GOV-ACTION-SEMANTICS"
        blockers.append(
            _blocking_rule(
                mapped_rule,
                "Workspace state verification has a blocking checkpoint preflight finding.",
                f"{rule_id}: {finding.get('details', finding.get('message', ''))}",
                path=str(finding.get("path", "")),
                recommendation=str(finding.get("recommendation", "Resolve the state verification finding.")),
            )
        )
    return blockers


def _workspace_report(root: Path, strict: bool) -> tuple[dict[str, object], int]:
    verify_report, verify_exit_code = state_verify._report(root, strict)
    sidecars = plan_next._load_sidecars(root)
    project_state = _content(sidecars, "PROJECT_STATE")
    next_action = _content(sidecars, "NEXT_ACTION")
    transition_evidence = _transition_engine_evidence(root, sidecars)
    derived_next_action_cache = transition_evidence.get("derived_next_action_cache")
    routing_next_action = dict(next_action)
    if isinstance(derived_next_action_cache, dict):
        routing_next_action = dict(derived_next_action_cache)
    elif isinstance(transition_evidence.get("next_action"), dict):
        routing_next_action = dict(transition_evidence["next_action"])
    tasks = _tasks_by_id(sidecars)
    task_id = _as_text(routing_next_action.get("task_id"))
    task = tasks.get(task_id, {})
    blockers = _active_blockers(project_state, routing_next_action)
    audit_evidence = _audit_pass_evidence(root, sidecars, task, task_id)
    correction_route = correction_routing.from_audit_inspection(root, audit_evidence.get("invalid_audit_results"))
    is_checkpoint_attempt = transition_evidence.get("canonical_recommended_next_action") == "CHECKPOINT_PREFLIGHT"
    checkpoint_eligibility = _as_text(project_state.get("checkpoint_eligibility"))
    checkpoint_eligibility_status = _as_text(project_state.get("checkpoint_eligibility_status"))

    blocking_rules = _state_verify_blockers(verify_report)
    warnings: list[dict[str, object]] = []

    if verify_exit_code == EXIT_IO_ERROR:
        blocking_rules.append(
            _blocking_rule(
                "GOV-ACTION-SEMANTICS",
                "Workspace state sidecars are unavailable or unreadable.",
                str(verify_report.get("summary", {})),
                recommendation="Restore required project-runtime/state sidecars before checkpoint preflight.",
            )
        )

    if not is_checkpoint_attempt:
        warnings.append(
            _warning(
                "GOV-CHECKPOINT-AUDIT-GATE",
                "Canonical transition route is not currently a checkpoint attempt.",
                (
                    f"canonical_recommended_next_action="
                    f"{transition_evidence.get('canonical_recommended_next_action', 'NONE')}"
                ),
            )
        )

    if not audit_evidence["present"]:
        blocking_rules.append(
            _blocking_rule(
                "GOV-CHECKPOINT-AUDIT-GATE",
                "Checkpoint preflight is blocked because audit-pass evidence is absent.",
                f"task_id={task_id or 'NONE'}; task_status={audit_evidence['task_status'] or 'NONE'}",
                recommendation="Run and accept the required audit before checkpoint preflight can be eligible.",
            )
        )

    if audit_evidence["invalid_audit_results"]:
        blocking_rules.append(
            _blocking_rule(
                "GOV-CHECKPOINT-AUDIT-GATE",
                "Checkpoint preflight is blocked because parsed AUDIT_RESULT evidence is not a pass for this task.",
                json.dumps(audit_evidence["invalid_audit_results"], sort_keys=True),
                recommendation="Record an auditor AUDIT_RESULT with STATUS: pass for the task before checkpointing.",
            )
        )
        if correction_route:
            blocking_rules.append(
                _blocking_rule(
                    "GOV-AUDIT-FAIL-NO-CHECKPOINT",
                    "Checkpoint preflight is blocked because AUDIT_RESULT STATUS fail routes correction.",
                    str(correction_route.get("source_audit_result_ref", "NONE")),
                    recommendation="Route correction from the failed audit before checkpointing.",
                )
            )

    if audit_evidence["unparsed_audit_refs"]:
        blocking_rules.append(
            _blocking_rule(
                "GOV-CHECKPOINT-AUDIT-GATE",
                "Checkpoint preflight is blocked because AUDIT_RESULT evidence references are missing or unreadable.",
                json.dumps(audit_evidence["unparsed_audit_refs"], sort_keys=True),
                recommendation="Restore the referenced AUDIT_RESULT file or record a new passing auditor AUDIT_RESULT.",
            )
        )

    if blockers:
        blocking_rules.append(
            _blocking_rule(
                "GOV-ACTION-SEMANTICS",
                "Active blockers or GAP routes block checkpoint eligibility.",
                ", ".join(blockers),
                recommendation="Resolve or route active blockers before checkpointing.",
            )
        )

    if checkpoint_eligibility in BLOCKING_CHECKPOINT_ELIGIBILITY:
        blocking_rules.append(
            _blocking_rule(
                "GOV-CHECKPOINT-AUDIT-GATE",
                "Runtime state marks checkpoint eligibility as blocked or ineligible.",
                f"checkpoint_eligibility={checkpoint_eligibility}",
                recommendation="Resolve checkpoint_blocked_by state before checkpointing.",
            )
        )
    elif checkpoint_eligibility_status in BLOCKING_CHECKPOINT_ELIGIBILITY_STATUS:
        blocking_rules.append(
            _blocking_rule(
                "GOV-CHECKPOINT-AUDIT-GATE",
                "Runtime state marks checkpoint eligibility status as blocked or ineligible.",
                f"checkpoint_eligibility_status={checkpoint_eligibility_status}",
                recommendation="Resolve checkpoint_blocked_by state before checkpointing.",
            )
        )
    elif checkpoint_eligibility and checkpoint_eligibility not in {"local_only", "push_allowed", "not_applicable"}:
        warnings.append(
            _warning(
                "GOV-CHECKPOINT-AUDIT-GATE",
                "Runtime checkpoint eligibility is not a canonical eligible or not-applicable value.",
                f"checkpoint_eligibility={checkpoint_eligibility}",
            )
        )

    if strict:
        blocking_rules.extend(
            _blocking_rule(
                str(item["rule_id"]),
                str(item["message"]),
                str(item["evidence"]),
                path=str(item.get("path", "")),
                recommendation="Strict mode treats checkpoint preflight warnings as blockers.",
            )
            for item in warnings
        )

    blocking_rules = _dedupe(blocking_rules)
    warnings = _dedupe(warnings)
    eligible = not blocking_rules
    status = "eligible" if eligible else ("io_error" if verify_exit_code == EXIT_IO_ERROR else "blocked")
    report = {
        "tool": "aso",
        "command": "checkpoint-preflight",
        "mode": "workspace",
        "status": status,
        "eligible": eligible,
        "root": str(root),
        "strict": strict,
        "read_only": True,
        "dry_run": True,
        "mutations_performed": False,
        "blocking_rules": blocking_rules,
        "warnings": warnings,
        "correction_routing": correction_route,
        "summary": _summary(blocking_rules, warnings),
        "evidence": {
            "state_verify": {
                "status": verify_report.get("status"),
                "summary": verify_report.get("summary"),
                "findings": verify_report.get("findings", []),
            },
            "next_action": {
                "action_type": next_action.get("action_type", ""),
                "action_semantic": next_action.get("action_semantic", ""),
                "checkpoint_policy": next_action.get("checkpoint_policy", ""),
                "task_id": task_id,
                "task_packet": next_action.get("task_packet", ""),
                "routing_action_type": routing_next_action.get("action_type", ""),
                "routing_checkpoint_policy": routing_next_action.get("checkpoint_policy", ""),
            },
            "project_state": {
                "project_status": project_state.get("project_status", ""),
                "checkpoint_eligibility": checkpoint_eligibility,
                "checkpoint_eligibility_status": checkpoint_eligibility_status,
                "checkpoint_preflight_status": project_state.get("checkpoint_preflight_status", ""),
                "checkpoint_blocked_by": project_state.get("checkpoint_blocked_by", []),
                "active_blockers": project_state.get("active_blockers", []),
            },
            "audit_pass_evidence": audit_evidence,
            "correction_routing": correction_route,
            "transition_engine": transition_evidence,
            "script_integration": {
                "checkpoint_preflight_sh_invoked": False,
                "reason": "Workspace mode reads state sidecars directly and does not invoke the shell preflight.",
            },
        },
    }
    if verify_exit_code == EXIT_IO_ERROR:
        return report, EXIT_IO_ERROR
    return report, EXIT_OK if eligible else EXIT_BLOCKED


def _print_text(report: dict[str, object]) -> None:
    print(f"ASO checkpoint-preflight: {str(report['status']).upper()} (dry-run/read-only)")
    print(f"Root: {report['root']}")
    print(f"Mode: {report['mode']}")
    print(f"Strict: {report['strict']}")
    print(f"Eligible: {str(report['eligible']).lower()}")
    print(f"Blocking rules: {len(report['blocking_rules'])}")
    print(f"Warnings: {len(report['warnings'])}")
    for blocker in report["blocking_rules"]:
        if isinstance(blocker, dict):
            print(f"- {blocker.get('rule_id')}: {blocker.get('message')}")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso checkpoint-preflight: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso checkpoint-preflight: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    """Run the read-only checkpoint preflight."""

    root = Path(args.root).expanduser()
    if args.mode == "package":
        report, exit_code = _package_report(root, bool(args.strict))
    else:
        report, exit_code = _workspace_report(root, bool(args.strict))
    _print_text(report)
    if args.json_out and not _write_json(str(args.json_out), report):
        return EXIT_IO_ERROR
    return exit_code
