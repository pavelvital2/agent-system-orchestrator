"""P4 product intake planning command scaffolds."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import output_policy


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_IO_ERROR = 3

READINESS_MODES = ("mvp", "business_ready", "production_ready", "enterprise_like")
ALLOWED_WORKSPACE_OUTPUTS = (
    "project-runtime/product",
    "project-runtime/reports",
    "project-runtime/rendered",
)
ARTIFACT_FILENAMES = {
    "PRODUCT_INTAKE": "product-intake",
    "OPEN_QUESTIONS": "open-questions",
    "PRODUCT_SPEC": "product-spec",
    "CAPABILITY_MATRIX": "capability-matrix",
    "PRODUCT_PLAN": "product-plan",
}
SECRET_NAME_RE = re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b")
SECRET_HINTS = ("TOKEN", "SECRET", "KEY", "PASSWORD", "WEBHOOK")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _artifact_id(artifact_type: str, now: datetime) -> str:
    return f"{artifact_type}-{now.strftime('%Y%m%dT%H%M%SZ')}"


def _read_text(path_text: str) -> tuple[str | None, str | None]:
    path = Path(path_text).expanduser()
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, f"failed to read {path}: {exc}"


def _read_json_object(path_text: str) -> tuple[dict[str, Any] | None, str | None]:
    path = Path(path_text).expanduser()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, f"failed to read {path}: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"failed to parse JSON {path}: {exc}"
    if not isinstance(loaded, dict):
        return None, f"expected JSON object in {path}"
    return loaded, None


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        clean = line.strip()
        if clean:
            return clean[:240]
    return "Owner product goal is not yet specified."


def _detected_secret_names(text: str) -> list[str]:
    names = sorted(
        {
            match.group(0)
            for match in SECRET_NAME_RE.finditer(text)
            if any(hint in match.group(0) for hint in SECRET_HINTS)
        }
    )
    return names


def _source_ref(source_ref_id: str, source_type: str, title: str, **extra: object) -> dict[str, object]:
    ref: dict[str, object] = {
        "source_ref_id": source_ref_id,
        "source_type": source_type,
        "title": title,
    }
    ref.update(extra)
    return ref


def _common(
    args: argparse.Namespace,
    *,
    artifact_type: str,
    status: str,
    source_refs: list[dict[str, object]],
    human_summary: str,
    now: datetime,
) -> dict[str, object]:
    return {
        "artifact_id": _artifact_id(artifact_type, now),
        "artifact_type": artifact_type,
        "schema_version": "1.0.0",
        "package_version": "3.6.0",
        "runtime_schema_version": "3.1.0",
        "created_at": _timestamp(now),
        "created_by": "aso",
        "target_root": "project-runtime/product/",
        "profile": str(args.profile),
        "readiness_mode": str(args.readiness),
        "status": status,
        "source_refs": source_refs,
        "human_summary": human_summary,
    }


def _build_intake(args: argparse.Namespace, now: datetime) -> tuple[dict[str, object] | None, str | None]:
    text, error = _read_text(str(args.tz))
    if error is not None or text is None:
        return None, error
    goal = _first_non_empty_line(text)
    secret_names = _detected_secret_names(text)
    source_ref = _source_ref(
        "SRC-owner-tz",
        "owner_input",
        "Owner TZ product request",
        description=f"Local input file: {Path(str(args.tz)).expanduser()}",
    )
    artifact = _common(
        args,
        artifact_type="PRODUCT_INTAKE",
        status="needs_clarification",
        source_refs=[source_ref],
        human_summary=(
            "Planning-only intake scaffold generated locally; later tasks own full "
            "capability detection and product generation."
        ),
        now=now,
    )
    artifact.update(
        {
            "goal": goal,
            "source_summary": goal,
            "candidate_capabilities": [
                {
                    "capability_id": "CAP-001",
                    "name": "Owner requested capability",
                    "description": "Placeholder capability derived from owner input for planning review.",
                    "source_ref_ids": ["SRC-owner-tz"],
                }
            ],
            "assumptions": [
                {
                    "id": "ASSUMPTION-001",
                    "text": "Full product decomposition is intentionally deferred to later P4 tasks.",
                    "source_ref_ids": ["SRC-owner-tz"],
                }
            ],
            "missing_information": [
                {
                    "id": "MISSING-001",
                    "text": "Owner must confirm users, workflows, data, integrations, security, operations, and acceptance.",
                    "source_ref_ids": ["SRC-owner-tz"],
                }
            ],
            "risk_flags": [
                {
                    "id": "RISK-001",
                    "text": "This scaffold is not implementation evidence and does not authorize execution.",
                    "source_ref_ids": ["SRC-owner-tz"],
                }
            ],
            "external_integrations": [],
            "required_secrets": [
                {
                    "secret_id": f"SECRET-{index:03d}",
                    "name": name,
                    "value_status": "not_collected",
                    "purpose": "Secret name detected from owner input; value was not collected or stored.",
                }
                for index, name in enumerate(secret_names, start=1)
            ],
        }
    )
    return artifact, None


def _artifact_profile(args: argparse.Namespace, source: dict[str, Any]) -> None:
    if getattr(args, "profile", None) == "generic" and isinstance(source.get("profile"), str):
        args.profile = source["profile"]
    if getattr(args, "readiness", None) == "mvp" and source.get("readiness_mode") in READINESS_MODES:
        args.readiness = source["readiness_mode"]


def _build_clarify(args: argparse.Namespace, now: datetime) -> tuple[dict[str, object] | None, str | None]:
    intake, error = _read_json_object(str(args.from_intake))
    if error is not None or intake is None:
        return None, error
    _artifact_profile(args, intake)
    artifact = _common(
        args,
        artifact_type="OPEN_QUESTIONS",
        status="needs_clarification",
        source_refs=[
            _source_ref(
                "SRC-product-intake",
                "artifact",
                "Product intake artifact",
                artifact_id=str(intake.get("artifact_id", "PRODUCT_INTAKE-unknown")),
            )
        ],
        human_summary="Planning-only owner clarification questions; no owner answers are inferred.",
        now=now,
    )
    categories = (
        "users and roles",
        "workflows",
        "data and storage",
        "integrations",
        "security/secrets",
        "deployment/operations",
        "business risks",
        "acceptance",
    )
    artifact["questions"] = [
        {
            "question_id": f"Q-{index:03d}",
            "question": f"What owner decision is required for {category}?",
            "category": category,
            "why_it_matters": "The product planning layer must keep unknowns explicit before implementation planning.",
            "options": [
                {
                    "option_id": "OPT-001",
                    "label": "Owner will answer",
                    "description": "Capture an explicit owner decision before downstream planning.",
                },
                {
                    "option_id": "OPT-002",
                    "label": "Defer",
                    "description": "Mark this area as a documented gap instead of silently filling it.",
                },
            ],
            "default_recommendation": "Owner should answer or explicitly defer.",
            "blocks_implementation": True,
            "source_ref_ids": ["SRC-product-intake"],
        }
        for index, category in enumerate(categories, start=1)
    ]
    return artifact, None


def _build_spec(args: argparse.Namespace, now: datetime) -> tuple[dict[str, object] | None, str | None]:
    intake, error = _read_json_object(str(args.from_intake))
    if error is not None or intake is None:
        return None, error
    answers, error = _read_json_object(str(args.answers))
    if error is not None or answers is None:
        return None, error
    _artifact_profile(args, intake)
    artifact = _common(
        args,
        artifact_type="PRODUCT_SPEC",
        status="needs_clarification",
        source_refs=[
            _source_ref(
                "SRC-product-intake",
                "artifact",
                "Product intake artifact",
                artifact_id=str(intake.get("artifact_id", "PRODUCT_INTAKE-unknown")),
            ),
            _source_ref("SRC-owner-answers", "artifact", "Owner answers artifact"),
        ],
        human_summary="Planning-only product specification scaffold; critical unknowns remain explicit gaps.",
        now=now,
    )
    goal = str(intake.get("goal") or "Product goal remains an explicit gap.")
    artifact.update(
        {
            "product_name": str(answers.get("product_name") or "Product name pending owner confirmation"),
            "problem_statement": goal,
            "target_users": ["Primary users pending owner confirmation"],
            "outcomes": ["Owner-visible outcome pending owner confirmation"],
            "requirements": [
                {
                    "requirement_id": "REQ-001",
                    "description": "Plan the first owner-approved workflow after clarification.",
                    "priority": "must",
                    "source_ref_ids": ["SRC-product-intake", "SRC-owner-answers"],
                    "capability_ids": ["CAP-001"],
                }
            ],
            "scope_in": ["Planning-only product specification review"],
            "scope_out": ["Application source generation", "Deployment execution", "Live external API calls"],
        }
    )
    return artifact, None


def _build_capabilities(args: argparse.Namespace, now: datetime) -> tuple[dict[str, object] | None, str | None]:
    spec, error = _read_json_object(str(args.from_spec))
    if error is not None or spec is None:
        return None, error
    _artifact_profile(args, spec)
    artifact = _common(
        args,
        artifact_type="CAPABILITY_MATRIX",
        status="proposed",
        source_refs=[
            _source_ref(
                "SRC-product-spec",
                "artifact",
                "Product spec artifact",
                artifact_id=str(spec.get("artifact_id", "PRODUCT_SPEC-unknown")),
            )
        ],
        human_summary="Planning-only capability matrix scaffold; verification expectations are future-facing.",
        now=now,
    )
    artifact.update(
        {
            "user_wants": str(spec.get("problem_statement") or "Owner-desired behavior remains under review."),
            "planned_delivery": "Future governed implementation work may be planned after owner review.",
            "verification_later": "Future evidence must map each accepted capability to acceptance criteria.",
            "not_included": ["Application source generation", "Deployment execution", "Live external integration execution"],
            "capabilities": [
                {
                    "capability_id": "CAP-001",
                    "user_wants": "Owner-requested behavior from the product specification.",
                    "planned_delivery": "Plan future governed implementation work for the accepted capability.",
                    "verification_later": "Verify with acceptance evidence after implementation exists.",
                    "not_included": ["Secret collection", "Live dispatch", "Deployment"],
                    "requirement_ids": ["REQ-001"],
                    "user_story_ids": ["US-001"],
                    "acceptance_criterion_ids": ["AC-001"],
                    "status": "proposed",
                }
            ],
        }
    )
    return artifact, None


def _build_plan(args: argparse.Namespace, now: datetime) -> tuple[dict[str, object] | None, str | None]:
    spec, error = _read_json_object(str(args.from_spec))
    if error is not None or spec is None:
        return None, error
    capabilities, error = _read_json_object(str(args.from_capabilities))
    if error is not None or capabilities is None:
        return None, error
    _artifact_profile(args, spec)
    artifact = _common(
        args,
        artifact_type="PRODUCT_PLAN",
        status="proposed",
        source_refs=[
            _source_ref(
                "SRC-product-spec",
                "artifact",
                "Product spec artifact",
                artifact_id=str(spec.get("artifact_id", "PRODUCT_SPEC-unknown")),
            ),
            _source_ref(
                "SRC-capability-matrix",
                "artifact",
                "Capability matrix artifact",
                artifact_id=str(capabilities.get("artifact_id", "CAPABILITY_MATRIX-unknown")),
            ),
        ],
        human_summary=(
            "Non-executable product plan scaffold; it does not create task packets, "
            "queue dispatches, execute checkpoints, commit, push, deploy, call APIs, or collect secrets."
        ),
        now=now,
    )
    artifact.update(
        {
            "plan_summary": "Future governed implementation workstreams can be proposed after owner review.",
            "planned_workstreams": [
                {
                    "planned_workstream_id": "WS-001",
                    "description": "Plan future work for the first accepted capability.",
                    "capability_ids": ["CAP-001"],
                    "acceptance_criterion_ids": ["AC-001"],
                    "sequencing_notes": "Owner review must happen before downstream task packets or dispatches are created.",
                    "status": "proposed",
                }
            ],
            "non_executable_constraints": [
                "no_task_packets",
                "no_queue_entries",
                "no_live_dispatch",
                "no_checkpoint_execution",
                "no_commits_or_pushes",
                "no_deployment_execution",
                "no_external_api_calls",
                "no_secret_collection",
            ],
            "creates_task_packets": False,
            "queues_dispatches": False,
            "executes_checkpoints": False,
            "performs_commits": False,
            "performs_deployments": False,
        }
    )
    return artifact, None


def _is_workspace_output(root: Path, path: Path) -> bool:
    workspace = root.expanduser().resolve(strict=False)
    target = path.resolve(strict=False)
    try:
        target.relative_to((workspace / "project-runtime").resolve(strict=False))
    except ValueError:
        return False
    return True


def _validate_json_out(root: Path, path_text: str, *, confirm_write: bool) -> tuple[Path | None, str | None]:
    path = output_policy.resolve_output_path(path_text)
    error = output_policy.validate_generated_output_path(
        root,
        path,
        allowed_workspace_subdirs=ALLOWED_WORKSPACE_OUTPUTS,
    )
    if error is not None:
        return None, f"{error.rule_id}: {error.message}: {error.evidence}"
    if _is_workspace_output(root, path) and not confirm_write:
        return None, "--confirm-write is required for workspace product artifact writes"
    if not path.parent.exists():
        return None, f"json-out parent does not exist: {path.parent}"
    return path, None


def _confirm_write_path(root: Path, artifact: dict[str, object]) -> tuple[Path | None, str | None]:
    product_dir = (root / "project-runtime" / "product").resolve(strict=False)
    artifact_type = str(artifact.get("artifact_type") or "product-artifact")
    filename_part = ARTIFACT_FILENAMES.get(artifact_type, artifact_type.lower())
    artifact_id = str(artifact.get("artifact_id") or filename_part)
    path = product_dir / f"{artifact_id}-{filename_part}.json"
    error = output_policy.validate_generated_output_path(
        root,
        path,
        allowed_workspace_subdirs=("project-runtime/product",),
    )
    if error is not None:
        return None, f"{error.rule_id}: {error.message}: {error.evidence}"
    try:
        product_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return None, f"failed to create product artifact directory: {exc}"
    return path, None


def _write_json(path: Path, payload: dict[str, object]) -> tuple[bool, str]:
    try:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, ""


def _run_product(args: argparse.Namespace, builder: Any, command_name: str) -> int:
    root = Path(args.root).expanduser()
    artifact, error = builder(args, _utc_now())
    if error is not None or artifact is None:
        print(f"aso product {command_name}: {error}", file=sys.stderr)
        return EXIT_BLOCKED

    files_written: list[Path] = []
    if args.confirm_write:
        path, error = _confirm_write_path(root, artifact)
        if error is not None or path is None:
            print(f"aso product {command_name}: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        ok, write_error = _write_json(path, artifact)
        if not ok:
            print(f"aso product {command_name}: failed to write confirmed artifact: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(path)

    if args.json_out:
        path, error = _validate_json_out(root, str(args.json_out), confirm_write=bool(args.confirm_write))
        if error is not None or path is None:
            print(f"aso product {command_name}: {error}", file=sys.stderr)
            return EXIT_BLOCKED
        if path not in files_written:
            ok, write_error = _write_json(path, artifact)
            if not ok:
                print(f"aso product {command_name}: failed to write json-out: {write_error}", file=sys.stderr)
                return EXIT_IO_ERROR
            files_written.append(path)

    if not files_written:
        print(json.dumps(artifact, indent=2, sort_keys=True))
    elif args.confirm_write and not args.json_out:
        print(f"aso product {command_name}: wrote {files_written[0]}")
    return EXIT_OK


def run_intake(args: argparse.Namespace) -> int:
    return _run_product(args, _build_intake, "intake")


def run_clarify(args: argparse.Namespace) -> int:
    return _run_product(args, _build_clarify, "clarify")


def run_spec(args: argparse.Namespace) -> int:
    return _run_product(args, _build_spec, "spec")


def run_capabilities(args: argparse.Namespace) -> int:
    return _run_product(args, _build_capabilities, "capabilities")


def run_plan(args: argparse.Namespace) -> int:
    return _run_product(args, _build_plan, "plan")
