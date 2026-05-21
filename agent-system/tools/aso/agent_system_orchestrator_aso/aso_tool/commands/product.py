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
REDACTED_SECRET_PLACEHOLDER = "REDACTED_SECRET_VALUE"
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b([A-Z][A-Z0-9_]*(?:TOKEN|SECRET|KEY|PASSWORD|WEBHOOK)[A-Z0-9_]*|"
    r"api[_ .-]?key|access[_ .-]?token|refresh[_ .-]?token|webhook[_ .-]?secret|"
    r"password|passwd|pwd|secret|token)"
    r"\s*(?::|=|\bis\b|\bare\b)\s*([^\s,;`\"']+)"
)
GENERIC_SECRET_NAME_MAP = {
    "API_KEY": "EXTERNAL_API_KEY",
    "ACCESS_TOKEN": "EXTERNAL_ACCESS_TOKEN",
    "REFRESH_TOKEN": "EXTERNAL_REFRESH_TOKEN",
    "WEBHOOK_SECRET": "EXTERNAL_WEBHOOK_SECRET",
    "PASSWORD": "EXTERNAL_PASSWORD",
    "PASSWD": "EXTERNAL_PASSWORD",
    "PWD": "EXTERNAL_PASSWORD",
    "SECRET": "EXTERNAL_SECRET",
    "TOKEN": "EXTERNAL_API_TOKEN",
}
INLINE_SECRET_VALUE_RE = re.compile(
    r"(?i)\b(?:bearer\s+[A-Za-z0-9._~+/=-]{12,}|"
    r"\d{6,12}:[A-Za-z0-9_-]{20,}|"
    r"sk-[A-Za-z0-9_-]{10,}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"gh[pousr]_[A-Za-z0-9_]{10,}|glpat-[A-Za-z0-9_-]{10,}|AKIA[0-9A-Z]{12,})"
)

PRODUCT_PROFILE_HINTS = (
    ("telegram_bot", ("telegram", "bot", "chat command", "inline keyboard", "webhook")),
    ("marketplace_automation", ("marketplace", "ozon", "wildberries", "amazon", "shopify", "catalog", "stock", "price")),
    ("web_app", ("web app", "website", "dashboard", "admin panel", "frontend", "landing")),
    ("api_service", ("api", "backend", "service", "endpoint", "integration")),
    ("cli_tool", ("cli", "command line", "terminal", "console")),
    ("analytics_tool", ("analytics", "report", "metrics", "dashboard", "export")),
    ("crm_tool", ("crm", "lead", "pipeline", "sales manager")),
)

CAPABILITY_HINTS = (
    (
        "Telegram bot conversation",
        ("telegram", "bot", "chat", "message", "inline keyboard"),
        "Handle owner-approved Telegram bot conversations and commands.",
    ),
    (
        "Admin dashboard",
        ("admin", "dashboard", "panel", "moderator", "back office"),
        "Provide an operator-facing surface for review and configuration.",
    ),
    (
        "User accounts and roles",
        ("login", "auth", "account", "role", "user profile", "registration"),
        "Manage user access, roles, and account lifecycle requirements.",
    ),
    (
        "Catalog and marketplace sync",
        ("catalog", "marketplace", "stock", "inventory", "price", "promo", "ozon", "wildberries", "shopify"),
        "Plan catalog, inventory, price, or marketplace synchronization behavior.",
    ),
    (
        "Payments and billing",
        ("payment", "pay", "invoice", "subscription", "refund", "stripe", "yookassa", "paypal"),
        "Plan payment, billing, invoice, or refund flows with approval boundaries.",
    ),
    (
        "Notifications",
        ("notify", "notification", "email", "sms", "alert", "reminder", "broadcast"),
        "Send owner-approved notifications or reminders through configured channels.",
    ),
    (
        "Reports and analytics",
        ("report", "analytics", "metric", "statistics", "export", "csv", "dashboard"),
        "Produce reports, exports, or metrics for owner review.",
    ),
    (
        "Data capture and storage",
        ("database", "storage", "save", "record", "form", "survey", "file", "upload"),
        "Capture and store product data according to confirmed retention rules.",
    ),
    (
        "External system integration",
        ("api", "integration", "webhook", "sync", "crm", "google sheets", "openai"),
        "Integrate with external systems after credentials and approval policy are defined.",
    ),
    (
        "Search and filtering",
        ("search", "filter", "sort", "query"),
        "Let users find and filter product records or content.",
    ),
)

INTEGRATION_HINTS = (
    ("Telegram", ("telegram", "botfather", "telegram bot")),
    ("Stripe", ("stripe",)),
    ("YooKassa", ("yookassa", "yoo kassa", "ukassa")),
    ("PayPal", ("paypal",)),
    ("Marketplace API", ("marketplace", "ozon", "wildberries", "amazon seller", "shopify")),
    ("Google Sheets", ("google sheets", "spreadsheet")),
    ("Google APIs", ("google api", "gmail", "google calendar", "google drive")),
    ("CRM", ("crm", "amoCRM", "bitrix", "salesforce", "hubspot")),
    ("Email or SMTP", ("email", "smtp", "mailgun", "sendgrid")),
    ("SMS provider", ("sms", "twilio")),
    ("OpenAI API", ("openai", "gpt", "llm")),
)

INTEGRATION_SECRET_NAMES = {
    "Telegram": ("TELEGRAM_BOT_TOKEN",),
    "Stripe": ("STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET"),
    "YooKassa": ("YOOKASSA_SHOP_ID", "YOOKASSA_SECRET_KEY"),
    "PayPal": ("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"),
    "Marketplace API": ("MARKETPLACE_API_KEY",),
    "Google Sheets": ("GOOGLE_SERVICE_ACCOUNT_JSON",),
    "Google APIs": ("GOOGLE_API_KEY",),
    "CRM": ("CRM_API_TOKEN",),
    "Email or SMTP": ("SMTP_PASSWORD",),
    "SMS provider": ("SMS_PROVIDER_API_KEY",),
    "OpenAI API": ("OPENAI_API_KEY",),
}

HIGH_RISK_HINTS = (
    (
        "Marketplace price, stock, or promotion changes",
        ("price", "stock", "inventory", "promo", "discount", "publish listing", "marketplace"),
    ),
    (
        "Payment, refund, payout, or subscription changes",
        ("payment", "charge", "refund", "payout", "invoice", "subscription", "billing"),
    ),
    (
        "Bulk messaging or user-impacting notifications",
        ("broadcast", "mass message", "bulk", "notify all", "sms", "email campaign"),
    ),
    (
        "User blocking, deletion, or irreversible data changes",
        ("delete", "erase", "block user", "ban", "remove account", "irreversible"),
    ),
    (
        "Sensitive personal, financial, medical, or legal data handling",
        ("personal data", "passport", "medical", "diagnosis", "legal", "finance", "bank card", "pii"),
    ),
)


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


def _source_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "markdown_tz"
    if suffix in {".txt", ".text"}:
        return "text_tz"
    if suffix in {".json"}:
        return "json_tz"
    return "local_tz"


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _redact_secret_values(text: str) -> tuple[str, bool]:
    redacted = False

    def replace_assignment(match: re.Match[str]) -> str:
        nonlocal redacted
        redacted = True
        return f"{match.group(1).strip()}=[{REDACTED_SECRET_PLACEHOLDER}]"

    sanitized = SECRET_ASSIGNMENT_RE.sub(replace_assignment, text)
    sanitized, inline_count = INLINE_SECRET_VALUE_RE.subn(f"[{REDACTED_SECRET_PLACEHOLDER}]", sanitized)
    redacted = redacted or inline_count > 0
    return sanitized, redacted


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        clean = line.strip().lstrip("#").strip()
        if clean:
            return _normalize_ws(clean)[:240]
    return "Owner product goal is not yet specified."


def _detected_secret_names(text: str) -> list[str]:
    names = {
        match.group(0)
        for match in SECRET_NAME_RE.finditer(text)
        if any(hint in match.group(0) for hint in SECRET_HINTS)
        and match.group(0) != REDACTED_SECRET_PLACEHOLDER
    }
    for match in SECRET_ASSIGNMENT_RE.finditer(text):
        key = re.sub(r"[^A-Za-z0-9]+", "_", match.group(1)).strip("_").upper()
        if key and any(hint in key for hint in SECRET_HINTS):
            names.add(GENERIC_SECRET_NAME_MAP.get(key, key))
    return sorted(names)


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(hint.casefold() in folded for hint in hints)


def _detected_profile(requested_profile: str, text: str) -> str:
    if requested_profile != "generic":
        return requested_profile
    for profile, hints in PRODUCT_PROFILE_HINTS:
        if _contains_any(text, hints):
            return profile
    return "generic"


def _source_summary(path: Path, source_kind: str, goal: str, sanitized_text: str, redacted: bool) -> str:
    lines = [_normalize_ws(line.lstrip("#-* ").strip()) for line in sanitized_text.splitlines()]
    useful_lines = [line for line in lines if line][:3]
    summary = " ".join(useful_lines)[:500] or goal
    redaction_note = " Secret-like values were redacted." if redacted else ""
    return f"Source path: {path}; source type: {source_kind}; summary: {summary}{redaction_note}"


def _candidate_capabilities(text: str) -> list[dict[str, object]]:
    capabilities: list[dict[str, object]] = []
    seen: set[str] = set()
    for name, hints, description in CAPABILITY_HINTS:
        if _contains_any(text, hints) and name not in seen:
            seen.add(name)
            capabilities.append(
                {
                    "capability_id": f"CAP-{len(capabilities) + 1:03d}",
                    "name": name,
                    "description": description,
                    "source_ref_ids": ["SRC-owner-tz"],
                }
            )
    if not capabilities:
        capabilities.append(
            {
                "capability_id": "CAP-001",
                "name": "Clarified owner workflow",
                "description": "Clarify and plan the primary owner-visible workflow before implementation.",
                "source_ref_ids": ["SRC-owner-tz"],
            }
        )
    return capabilities


def _trace_notes(prefix: str, texts: list[str]) -> list[dict[str, object]]:
    return [
        {
            "id": f"{prefix}-{index:03d}",
            "text": text,
            "source_ref_ids": ["SRC-owner-tz"],
        }
        for index, text in enumerate(texts, start=1)
    ]


def _external_integrations(text: str) -> list[str]:
    names: list[str] = []
    for name, hints in INTEGRATION_HINTS:
        if _contains_any(text, hints) and name not in names:
            names.append(name)
    return names


def _required_secret_names(text: str, integrations: list[str]) -> list[str]:
    names = set(_detected_secret_names(text))
    for integration in integrations:
        names.update(INTEGRATION_SECRET_NAMES.get(integration, ()))
    return sorted(names)


def _high_risk_actions(text: str) -> list[str]:
    actions = []
    for action, hints in HIGH_RISK_HINTS:
        if _contains_any(text, hints):
            actions.append(action)
    return actions


def _missing_information(text: str, integrations: list[str], secret_names: list[str], high_risk_actions: list[str]) -> list[str]:
    missing = []
    if not _contains_any(text, ("user", "customer", "client", "admin", "operator", "manager", "role")):
        missing.append("Target users, roles, and permissions are not fully specified.")
    if not _contains_any(text, ("workflow", "scenario", "when", "after", "step", "flow", "use case")):
        missing.append("Primary workflows and user scenarios need owner confirmation.")
    if not _contains_any(text, ("data", "database", "storage", "record", "retention", "export", "report")):
        missing.append("Data model, storage, retention, and export expectations are not fully specified.")
    if integrations:
        missing.append("External integration scopes, sandbox modes, credentials, and approval policy need owner confirmation.")
    if secret_names:
        missing.append("Secret collection procedure and secret owner are not specified; only secret names were recorded.")
    if high_risk_actions:
        missing.append("High-risk business actions require explicit owner approval, rollback policy, and dry-run rules.")
    if not _contains_any(text, ("acceptance", "done", "test", "verify", "success criteria", "definition of done")):
        missing.append("Acceptance criteria and verification evidence are not specified.")
    if not missing:
        missing.append("Owner should confirm that no additional constraints or acceptance gaps remain.")
    return missing


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
    if not text.strip():
        return None, "empty TZ input: provide a non-empty owner TZ or product idea file"

    source_path = Path(str(args.tz)).expanduser().resolve(strict=False)
    source_kind = _source_kind(source_path)
    sanitized_text, redacted_secret_values = _redact_secret_values(text)
    goal = _first_non_empty_line(sanitized_text)
    detected_profile = _detected_profile(str(args.profile), sanitized_text)
    integrations = _external_integrations(sanitized_text)
    secret_names = _required_secret_names(sanitized_text, integrations)
    high_risk_actions = _high_risk_actions(sanitized_text)
    candidate_capabilities = _candidate_capabilities(sanitized_text)
    missing_information = _missing_information(sanitized_text, integrations, secret_names, high_risk_actions)
    constraints = [
        "P4 intake is planning-only and does not authorize implementation, dispatch, deployment, commits, pushes, tags, or checkpoint execution.",
        "No network, LLM, or external API calls are made by this intake command.",
        "Required secrets are recorded by name only; secret values are not collected or stored.",
    ]
    assumptions = [
        f"Detected product profile is '{detected_profile}' based on local deterministic heuristics and/or the requested profile.",
        f"Readiness mode '{args.readiness}' is a planning target, not a claim that the product is ready.",
    ]
    risk_flags = [
        "This intake artifact is not implementation evidence and does not authorize live execution.",
    ]
    if redacted_secret_values:
        risk_flags.append("Secret-like values appeared in owner input and were redacted from generated output.")
        assumptions.append("Any real secret pasted into owner input should be rotated outside ASO.")
    if high_risk_actions:
        risk_flags.append("High-risk business actions require owner decision cards, dry-run behavior, and approval policy before execution planning.")
    recommended_next_action = "Run `aso product clarify` to collect owner decisions before product specification."
    if high_risk_actions:
        recommended_next_action = (
            "Run `aso product clarify` and capture owner approval policy for high-risk actions before specification."
        )
    source_ref = _source_ref(
        "SRC-owner-tz",
        "owner_input",
        "Owner TZ product request",
        path=str(source_path),
        description=f"Local input file; detected source type: {source_kind}",
    )
    artifact = _common(
        args,
        artifact_type="PRODUCT_INTAKE",
        status="needs_clarification",
        source_refs=[source_ref],
        human_summary=(
            "Planning-only intake generated locally with deterministic heuristics; "
            "unknowns, constraints, risks, integrations, and required secret names remain explicit."
        ),
        now=now,
    )
    artifact["profile"] = detected_profile
    artifact.update(
        {
            "product_goal": goal,
            "goal": goal,
            "source_summary": _source_summary(source_path, source_kind, goal, sanitized_text, redacted_secret_values),
            "candidate_capabilities": candidate_capabilities,
            "assumptions": _trace_notes("ASSUMPTION", assumptions),
            "missing_information": _trace_notes("MISSING", missing_information),
            "constraints": _trace_notes("CONSTRAINT", constraints),
            "risk_flags": _trace_notes("RISK", risk_flags),
            "external_integrations": _trace_notes(
                "INTEGRATION",
                [
                    f"{name} integration is a planning concern only; no external call was made."
                    for name in integrations
                ],
            ),
            "required_secrets": [
                {
                    "secret_id": f"SECRET-{index:03d}",
                    "name": name,
                    "value_status": "not_collected",
                    "purpose": "Secret name detected from owner input; value was not collected or stored.",
                }
                for index, name in enumerate(secret_names, start=1)
            ],
            "high_risk_business_actions": _trace_notes("HIGH_RISK", high_risk_actions),
            "recommended_next_action": recommended_next_action,
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
