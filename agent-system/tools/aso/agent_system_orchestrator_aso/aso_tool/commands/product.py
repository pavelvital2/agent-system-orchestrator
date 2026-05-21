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
    "USER_STORIES": "user-stories",
    "ACCEPTANCE_CRITERIA": "acceptance-criteria",
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

SPEC_ANSWER_FIELDS = {
    "product_name",
    "product_summary",
    "target_users",
    "scope_in",
    "scope_out",
    "assumptions",
    "dependencies",
    "external_integrations",
    "required_secrets",
    "data_model_notes",
    "acceptance_summary",
    "acceptance_criteria",
    "open_gaps",
}

SPEC_REQUIRED_LIST_FIELDS = {
    "target_users",
    "scope_in",
    "scope_out",
    "assumptions",
    "dependencies",
    "external_integrations",
    "data_model_notes",
    "acceptance_criteria",
    "open_gaps",
}

CRITICAL_SPEC_FIELDS = (
    "product_name",
    "product_summary",
    "target_users",
    "scope_in",
    "data_model_notes",
    "acceptance_summary",
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


def _trace_texts(source: dict[str, Any], field: str) -> list[str]:
    values = source.get(field)
    if not isinstance(values, list):
        return []
    texts: list[str] = []
    for item in values:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            texts.append(item["text"])
        elif isinstance(item, str):
            texts.append(item)
    return texts


def _trace_notes_from_texts(prefix: str, texts: list[str], source_ref_ids: list[str]) -> list[dict[str, object]]:
    return [
        {
            "id": f"{prefix}-{index:03d}",
            "text": text,
            "source_ref_ids": source_ref_ids,
        }
        for index, text in enumerate(texts, start=1)
    ]


def _secret_names(source: dict[str, Any]) -> list[str]:
    values = source.get("required_secrets")
    if not isinstance(values, list):
        return []
    names = {
        str(item.get("name"))
        for item in values
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and re.fullmatch(r"[A-Z][A-Z0-9_]*", str(item.get("name")))
    }
    return sorted(names)


def _answer_body(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if "answers" not in payload:
        return payload, None
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        return None, "answers field must contain a JSON object"
    return answers, None


def _validate_spec_answers(raw_answers: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    answers, error = _answer_body(raw_answers)
    if error is not None or answers is None:
        return None, error

    unknown = sorted(set(answers) - SPEC_ANSWER_FIELDS)
    if unknown:
        return None, f"answers file contains unsupported fields: {', '.join(unknown)}"

    for field in ("product_name", "product_summary", "acceptance_summary"):
        if field in answers and (not isinstance(answers[field], str) or not answers[field].strip()):
            return None, f"answers field {field} must be a non-empty string when provided"

    for field in SPEC_REQUIRED_LIST_FIELDS:
        if field in answers:
            value = answers[field]
            if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                return None, f"answers field {field} must be a list of non-empty strings when provided"

    if "required_secrets" in answers:
        value = answers["required_secrets"]
        if not isinstance(value, list):
            return None, "answers field required_secrets must be a list when provided"
        for index, item in enumerate(value, start=1):
            if isinstance(item, str):
                name = item
            elif isinstance(item, dict):
                extra_secret_fields = sorted(set(item) - {"name", "purpose"})
                if extra_secret_fields:
                    return None, (
                        "answers field required_secrets must contain secret names only; "
                        f"entry {index} has unsupported fields: {', '.join(extra_secret_fields)}"
                    )
                name = item.get("name")
                purpose = item.get("purpose")
                if purpose is not None and (not isinstance(purpose, str) or not purpose.strip()):
                    return None, f"answers field required_secrets entry {index} purpose must be a non-empty string"
            else:
                return None, f"answers field required_secrets entry {index} must be a string or object"
            if not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
                return None, f"answers field required_secrets entry {index} must provide an uppercase secret name only"

    if _contains_secret_values(answers):
        return None, "answers file appears to contain secret values; provide secret names only"
    return answers, None


def _contains_secret_values(value: Any) -> bool:
    if isinstance(value, str):
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
            return False
        _, redacted = _redact_secret_values(value)
        return redacted
    if isinstance(value, list):
        return any(_contains_secret_values(item) for item in value)
    if isinstance(value, dict):
        return any(key != "name" and _contains_secret_values(item) for key, item in value.items())
    return False


def _answer_string(answers: dict[str, Any], field: str) -> str | None:
    value = answers.get(field)
    if isinstance(value, str) and value.strip():
        return _normalize_ws(value)
    return None


def _answer_list(answers: dict[str, Any], field: str) -> list[str]:
    value = answers.get(field)
    if not isinstance(value, list):
        return []
    return [_normalize_ws(item) for item in value if isinstance(item, str) and item.strip()]


def _answer_secret_names(answers: dict[str, Any]) -> list[dict[str, str]]:
    values = answers.get("required_secrets")
    if not isinstance(values, list):
        return []
    secrets: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in values:
        if isinstance(item, str):
            name = item
            purpose = "Secret name supplied by owner answers; value was not collected or stored."
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            name = item["name"]
            purpose = str(item.get("purpose") or "Secret name supplied by owner answers; value was not collected or stored.")
        else:
            continue
        if name not in seen:
            seen.add(name)
            secrets.append({"name": name, "purpose": purpose})
    return secrets


def _spec_required_secrets(intake: dict[str, Any], answers: dict[str, Any]) -> list[dict[str, object]]:
    secret_by_name: dict[str, str] = {
        name: "Secret name detected from intake; value was not collected or stored."
        for name in _secret_names(intake)
    }
    for secret in _answer_secret_names(answers):
        secret_by_name[secret["name"]] = secret["purpose"]
    return [
        {
            "secret_id": f"SECRET-{index:03d}",
            "name": name,
            "value_status": "not_collected",
            "purpose": secret_by_name[name],
        }
        for index, name in enumerate(sorted(secret_by_name), start=1)
    ]


def _spec_external_integrations(intake: dict[str, Any], answers: dict[str, Any]) -> list[str]:
    answer_integrations = _answer_list(answers, "external_integrations")
    if answer_integrations:
        return answer_integrations
    integrations: list[str] = []
    for text in _trace_texts(intake, "external_integrations"):
        name = text.split(" integration", 1)[0].strip()
        integrations.append(name or text)
    return integrations


def _spec_scope_out(answers: dict[str, Any]) -> list[str]:
    scope_out = _answer_list(answers, "scope_out")
    mandatory_boundaries = [
        "Application source generation",
        "Deployment execution",
        "Live external API calls",
        "Secret collection or storage of secret values",
    ]
    for item in mandatory_boundaries:
        if item not in scope_out:
            scope_out.append(item)
    return scope_out


def _spec_open_gaps(intake: dict[str, Any], answers: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for field in CRITICAL_SPEC_FIELDS:
        value = answers.get(field)
        if isinstance(value, str):
            missing = not value.strip()
        elif isinstance(value, list):
            missing = not any(isinstance(item, str) and item.strip() for item in value)
        else:
            missing = True
        if missing:
            gaps.append(f"Critical answer missing: {field.replace('_', ' ')}.")

    for text in _trace_texts(intake, "missing_information"):
        if text not in gaps:
            gaps.append(text)
    for text in _answer_list(answers, "open_gaps"):
        if text not in gaps:
            gaps.append(text)
    return gaps


def _requirement_from_scope(index: int, description: str, source_ref_ids: list[str]) -> dict[str, object]:
    return {
        "requirement_id": f"REQ-{index:03d}",
        "description": description,
        "priority": "must",
        "source_ref_ids": source_ref_ids,
        "capability_ids": [f"CAP-{index:03d}"],
    }


def _build_user_stories_artifact(
    args: argparse.Namespace,
    now: datetime,
    *,
    product_spec_id: str,
    requirements: list[dict[str, object]],
    target_users: list[str],
) -> dict[str, object]:
    artifact = _common(
        args,
        artifact_type="USER_STORIES",
        status="proposed",
        source_refs=[
            _source_ref(
                "SRC-product-spec",
                "artifact",
                "Product spec artifact",
                artifact_id=product_spec_id,
            )
        ],
        human_summary="User stories derived from PRODUCT_SPEC requirements for owner review; not implementation evidence.",
        now=now,
    )
    persona = target_users[0] if target_users else "Primary user pending owner confirmation"
    artifact["stories"] = [
        {
            "user_story_id": f"US-{index:03d}",
            "requirement_id": str(requirement["requirement_id"]),
            "persona": persona,
            "story": f"As {persona}, I want {str(requirement['description']).rstrip('.')} so that the product delivers the confirmed scope.",
            "value": "Makes the requirement reviewable before future governed implementation work.",
            "priority": str(requirement["priority"]),
            "capability_ids": list(requirement.get("capability_ids", [])),
        }
        for index, requirement in enumerate(requirements, start=1)
    ]
    return artifact


def _build_acceptance_criteria_artifact(
    args: argparse.Namespace,
    now: datetime,
    *,
    user_stories_id: str,
    stories: list[dict[str, object]],
    acceptance_criteria: list[str],
) -> dict[str, object]:
    artifact = _common(
        args,
        artifact_type="ACCEPTANCE_CRITERIA",
        status="proposed",
        source_refs=[
            _source_ref(
                "SRC-user-stories",
                "artifact",
                "User stories artifact",
                artifact_id=user_stories_id,
            )
        ],
        human_summary="Future acceptance criteria linked to user stories; no implementation readiness is claimed.",
        now=now,
    )
    criteria: list[dict[str, object]] = []
    for index, story in enumerate(stories, start=1):
        statement = (
            acceptance_criteria[index - 1]
            if index <= len(acceptance_criteria)
            else f"Owner can review {story['user_story_id']} against the linked requirement and recorded open gaps."
        )
        capability_ids = story.get("capability_ids")
        capability_id = "CAP-001"
        if isinstance(capability_ids, list) and capability_ids:
            capability_id = str(capability_ids[0])
        criteria.append(
            {
                "acceptance_criterion_id": f"AC-{index:03d}",
                "user_story_id": str(story["user_story_id"]),
                "capability_id": capability_id,
                "statement": statement,
                "verification_method": "owner_review",
                "expected_evidence": "Future governed implementation evidence plus owner review notes.",
                "status": "proposed",
            }
        )
    artifact["criteria"] = criteria
    return artifact


def _question_options(question_id: str, options: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [
        {
            "option_id": f"OPT-{question_id.removeprefix('Q-')}-{index:03d}",
            "label": label,
            "description": description,
            "tradeoff": tradeoff,
        }
        for index, (label, description, tradeoff) in enumerate(options, start=1)
    ]


def _question(
    *,
    index: int,
    category: str,
    text: str,
    why: str,
    priority: str,
    severity: str,
    options: list[tuple[str, str, str]],
    recommendation: str,
    blocks: bool,
) -> dict[str, object]:
    question_id = f"Q-{index:03d}"
    return {
        "question_id": question_id,
        "question": text,
        "category": category,
        "priority": priority,
        "severity": severity,
        "why_it_matters": why,
        "options": _question_options(question_id, options),
        "default_recommendation": recommendation,
        "blocks_implementation": blocks,
        "source_ref_ids": ["SRC-product-intake"],
    }


def _decision_options(decision_number: int, options: list[tuple[str, str, str, str]]) -> list[dict[str, str]]:
    return [
        {
            "option_id": f"OPT-D{decision_number:03d}-{index:03d}",
            "label": label,
            "description": description,
            "tradeoff": tradeoff,
            "risk": risk,
        }
        for index, (label, description, tradeoff, risk) in enumerate(options, start=1)
    ]


def _decision_card(
    *,
    index: int,
    problem: str,
    options: list[tuple[str, str, str, str]],
    recommendation: str,
    impact: str,
    tradeoffs: list[str],
    risk: str,
    required_owner_action: str,
) -> dict[str, object]:
    return {
        "decision_id": f"DECISION-{index:03d}",
        "problem": problem,
        "options": _decision_options(index, options),
        "recommendation": recommendation,
        "impact": impact,
        "tradeoffs": tradeoffs,
        "risk": risk,
        "required_owner_action": required_owner_action,
        "source_ref_ids": ["SRC-product-intake"],
    }


def _build_clarify(args: argparse.Namespace, now: datetime) -> tuple[dict[str, object] | None, str | None]:
    intake, error = _read_json_object(str(args.from_intake))
    if error is not None or intake is None:
        return None, error
    _artifact_profile(args, intake)
    integrations = _trace_texts(intake, "external_integrations")
    secret_names = _secret_names(intake)
    high_risk_actions = _trace_texts(intake, "high_risk_business_actions")
    has_integrations = bool(integrations)
    has_secrets = bool(secret_names)
    has_high_risk_actions = bool(high_risk_actions)
    integration_hint = "the listed external systems" if has_integrations else "any external systems"
    secret_hint = ", ".join(secret_names) if secret_names else "the secret names needed later"
    risk_hint = "the listed high-risk actions" if has_high_risk_actions else "any action that changes money, access, messages, or customer data"
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
    questions = [
        _question(
            index=1,
            category="product",
            text="What should the first useful version of this product do for the owner?",
            why="A clear first version keeps the plan focused and prevents hidden scope from entering implementation.",
            priority="must",
            severity="high",
            options=[
                ("Narrow first version", "Deliver one complete owner-approved workflow first.", "Faster review, fewer features."),
                ("Broader first version", "Include several related workflows in the first plan.", "More complete, slower to validate."),
                ("Owner-defined scope", "Owner lists exactly what is in and out.", "Best fit, requires more owner input."),
            ],
            recommendation="Use a narrow first version unless the owner confirms a broader scope.",
            blocks=True,
        ),
        _question(
            index=2,
            category="users",
            text="Who will use this product, and should different people have different permissions?",
            why="User roles affect screens, approvals, data access, and what evidence is needed later.",
            priority="must",
            severity="high",
            options=[
                ("Same access for everyone", "All approved users can do the same things.", "Simpler, but less control."),
                ("Separate owner, admin, and user roles", "Different people get different permissions.", "Safer, but more setup."),
                ("Owner-defined roles", "Owner names each role and what it may do.", "Most accurate, requires a role list."),
            ],
            recommendation="Use separate roles only when more than one person type will use the product.",
            blocks=True,
        ),
        _question(
            index=3,
            category="data",
            text="What information should the product store, how long should it keep it, and what exports are needed?",
            why="Storage and retention choices affect privacy, recovery, reporting, and future acceptance checks.",
            priority="must",
            severity="high",
            options=[
                ("Minimal storage", "Keep only the data needed for the first workflow.", "Lower risk, fewer reports."),
                ("Operational history", "Keep records needed for review, support, and audit.", "More useful, more retention responsibility."),
                ("Owner-defined data list", "Owner lists fields, retention time, and export needs.", "Best fit, requires detailed input."),
            ],
            recommendation="Start with minimal storage and add fields only when the owner names a clear use.",
            blocks=True,
        ),
        _question(
            index=4,
            category="integrations",
            text=f"Which external systems should be connected first, and should {integration_hint} start in sandbox or read-only mode?",
            why="External integrations can change real data or money, so scope and rollout mode must be explicit.",
            priority="must" if has_integrations else "should",
            severity="high" if has_integrations else "medium",
            options=[
                ("No external connection first", "Plan the first version without live external systems.", "Safest, may limit usefulness."),
                ("Sandbox or read-only first", "Connect without making real-world changes.", "Good validation, may need extra setup."),
                ("Owner-approved live connection later", "Use live access only after owner approves the policy.", "More useful, higher risk."),
            ],
            recommendation="Use sandbox or read-only mode first when an integration is needed.",
            blocks=has_integrations,
        ),
        _question(
            index=5,
            category="deployment",
            text="Where should the product run first: local machine, test server, or production-like server?",
            why="The first runtime target changes setup, monitoring, access, and release expectations.",
            priority="should",
            severity="medium",
            options=[
                ("Local first", "Run only for review on a local machine.", "Fastest, not suitable for real users."),
                ("Test server first", "Run in a shared review environment.", "Better review, needs environment setup."),
                ("Production-like later", "Plan production-style hosting after acceptance is clearer.", "More realistic, more operations work."),
            ],
            recommendation="Use local or test server first; defer production-like hosting until acceptance is clear.",
            blocks=False,
        ),
        _question(
            index=6,
            category="security",
            text=f"How should access, approvals, and secrets be handled? For secrets such as {secret_hint}, provide names, owner, and setup procedure only; do not paste secret values.",
            why="Security decisions protect users and keep ASO from storing real credentials.",
            priority="must",
            severity="critical" if has_secrets else "high",
            options=[
                ("Names and procedure only", "Record secret names, who owns them, and how they will be added later.", "Safe for planning, needs owner follow-through."),
                ("Approval before sensitive actions", "Require owner approval before the product changes sensitive data.", "Safer, adds review steps."),
                ("Owner-defined security policy", "Owner provides access, approval, and credential handling rules.", "Most complete, requires policy input."),
            ],
            recommendation="Record secret names, owner, and procedure only; never store secret values in product artifacts.",
            blocks=has_secrets,
        ),
        _question(
            index=7,
            category="operations",
            text="Who will monitor the product, handle errors, and decide what happens when something fails?",
            why="Operations ownership keeps failures from becoming undefined owner decisions during implementation.",
            priority="should",
            severity="medium",
            options=[
                ("Owner monitors manually", "Owner checks results and handles failures during early review.", "Simple, more owner effort."),
                ("Operator role monitors", "A named operator watches alerts and handles routine issues.", "More reliable, needs role assignment."),
                ("Defer operations", "Document operations as a gap for later planning.", "Faster now, riskier later."),
            ],
            recommendation="Name an owner or operator for early review before planning live use.",
            blocks=False,
        ),
        _question(
            index=8,
            category="business risks",
            text=f"Which actions need explicit owner approval before the product performs them, especially {risk_hint}?",
            why="Approval rules prevent accidental financial, customer, access, or data-impacting actions.",
            priority="must" if has_high_risk_actions else "should",
            severity="critical" if has_high_risk_actions else "medium",
            options=[
                ("Dry-run only", "Show what would happen without performing the action.", "Safest, no live automation."),
                ("Approval required", "Ask the owner before each sensitive action.", "Balanced, adds owner review."),
                ("Not in first version", "Keep risky actions outside the first scope.", "Lower risk, less automation."),
            ],
            recommendation="Use dry-run or owner approval for any action that changes money, access, messages, or customer data.",
            blocks=has_high_risk_actions,
        ),
        _question(
            index=9,
            category="acceptance",
            text="What evidence will prove the first version is done and acceptable to the owner?",
            why="Acceptance evidence prevents the plan from treating guesses as completed product behavior.",
            priority="must",
            severity="high",
            options=[
                ("Owner demo review", "Owner confirms the workflow from a demo or walkthrough.", "Clear for early versions, manual evidence."),
                ("Checklist evidence", "Each accepted behavior has a documented pass/fail check.", "More structured, takes more setup."),
                ("Owner-defined acceptance", "Owner writes the exact success criteria.", "Most accurate, requires owner input."),
            ],
            recommendation="Use owner demo review plus a short checklist for the first version.",
            blocks=True,
        ),
    ]
    owner_decision_cards = [
        _decision_card(
            index=1,
            problem="Choose the first product scope.",
            options=[
                ("Narrow first version", "Plan one complete workflow.", "Fastest path to review.", "May defer desired features."),
                ("Broader first version", "Plan several workflows together.", "More complete first plan.", "More assumptions and slower review."),
                ("Owner-defined scope", "Owner lists exact in-scope and out-of-scope items.", "Best alignment.", "Requires more owner input now."),
            ],
            recommendation="Choose a narrow first version unless the owner confirms broader scope.",
            impact="This decision controls which capabilities can move into specification and future planning.",
            tradeoffs=["Speed versus breadth", "Clear acceptance versus larger feature coverage"],
            risk="Unclear scope can create downstream plans that do not match the owner need.",
            required_owner_action="Select the first-version scope or provide a revised in-scope/out-of-scope list.",
        ),
        _decision_card(
            index=2,
            problem="Choose user roles and permissions.",
            options=[
                ("Same access", "Every approved user can do the same things.", "Simpler setup.", "Too much access for some users."),
                ("Separate roles", "Owner, admin, operator, and user permissions are separate.", "Better control.", "Requires role decisions."),
                ("Owner-defined roles", "Owner provides the exact role list.", "Most accurate.", "Blocks planning until supplied."),
            ],
            recommendation="Use separate roles when the product has more than one type of user.",
            impact="This decision affects access checks, screens, approvals, and acceptance evidence.",
            tradeoffs=["Simple setup versus controlled access", "Fewer decisions now versus safer operations later"],
            risk="Missing role decisions can expose data or actions to the wrong users.",
            required_owner_action="Confirm whether all users share access or provide the role and permission list.",
        ),
        _decision_card(
            index=3,
            problem="Choose data storage, retention, and export rules.",
            options=[
                ("Minimal storage", "Store only fields needed for the first workflow.", "Lower privacy and maintenance burden.", "Limited reporting."),
                ("Operational history", "Keep useful history for support and review.", "Better traceability.", "More retention responsibility."),
                ("Owner-defined data policy", "Owner names fields, retention, and exports.", "Best fit.", "Requires detailed policy input."),
            ],
            recommendation="Start with minimal storage unless the owner needs audit, support, or reporting history.",
            impact="This decision affects privacy, reporting, recovery, and future migration work.",
            tradeoffs=["Lower data risk versus richer reporting", "Fast setup versus longer-term audit needs"],
            risk="Unclear data rules can lead to storing too much, too little, or the wrong information.",
            required_owner_action="Confirm the fields to store, retention period, and any export format needed.",
        ),
        _decision_card(
            index=4,
            problem="Choose integration rollout and secret handling.",
            options=[
                ("No live integration first", "Plan without connecting external systems.", "Safest first review.", "May not prove end-to-end behavior."),
                ("Sandbox or read-only first", "Connect without making real changes.", "Good validation with limited risk.", "May need test credentials."),
                ("Live later with approval", "Use live access only after explicit owner approval.", "Most realistic.", "Highest operational risk."),
            ],
            recommendation="Use sandbox or read-only mode first when integration is required.",
            impact="This decision affects external system setup, credentials, testing, and rollback expectations.",
            tradeoffs=["Safety versus realism", "Planning speed versus integration confidence"],
            risk="Live integration without explicit approval can change external systems unintentionally.",
            required_owner_action="Name each integration, its first rollout mode, secret owner, and setup procedure; do not provide secret values.",
        ),
        _decision_card(
            index=5,
            problem="Choose deployment target and operations owner.",
            options=[
                ("Local review", "Run locally for owner review.", "Fast and contained.", "Not suitable for real users."),
                ("Test server", "Run in a shared review environment.", "Better stakeholder access.", "Requires environment ownership."),
                ("Production-like later", "Defer production-style hosting until acceptance is clearer.", "Avoids premature operations work.", "Hosting decisions remain open."),
            ],
            recommendation="Use local or test server first, then revisit production-like hosting after acceptance.",
            impact="This decision affects monitoring, access, release steps, and support ownership.",
            tradeoffs=["Fast review versus realistic operations", "Low setup versus shared access"],
            risk="No operations owner means failures and alerts have no clear response path.",
            required_owner_action="Choose the first runtime target and name who owns monitoring and failure response.",
        ),
        _decision_card(
            index=6,
            problem="Choose approval rules for high-risk business actions.",
            options=[
                ("Dry-run only", "Show planned actions without performing them.", "Lowest risk.", "No live automation."),
                ("Owner approval required", "Require approval before each sensitive action.", "Controlled automation.", "Adds review steps."),
                ("Exclude from first version", "Leave risky actions out of scope.", "Simpler first plan.", "Defers important automation."),
            ],
            recommendation="Use dry-run or owner approval for sensitive actions in the first version.",
            impact="This decision controls how the product may affect money, customers, access, messages, or stored data.",
            tradeoffs=["Automation speed versus owner control", "Lower risk versus less hands-off operation"],
            risk="Unapproved sensitive actions can cause customer, financial, legal, or trust damage.",
            required_owner_action="Identify sensitive actions and choose dry-run, approval-required, or out-of-scope for each.",
        ),
        _decision_card(
            index=7,
            problem="Choose acceptance evidence for the first version.",
            options=[
                ("Owner demo review", "Owner confirms behavior from a demo.", "Easy to understand.", "Manual evidence only."),
                ("Checklist evidence", "Each behavior has pass/fail evidence.", "Clearer review trail.", "More preparation."),
                ("Owner-defined criteria", "Owner writes exact success criteria.", "Most precise.", "Requires owner time."),
            ],
            recommendation="Use owner demo review with a short checklist for the first version.",
            impact="This decision defines what later work must prove before it can be considered acceptable.",
            tradeoffs=["Lightweight review versus stronger evidence", "Owner speed versus future auditability"],
            risk="Without acceptance evidence, downstream work can claim progress without proving product value.",
            required_owner_action="Choose the acceptance method and provide any must-pass examples or edge cases.",
        ),
    ]
    artifact.update(
        {
            "question_groups": [
                {
                    "category": str(question["category"]),
                    "question_ids": [str(question["question_id"])],
                }
                for question in questions
            ],
            "questions": questions,
            "owner_decision_cards": owner_decision_cards,
        }
    )
    return artifact, None


def _build_spec(args: argparse.Namespace, now: datetime) -> tuple[dict[str, object] | None, str | None]:
    intake, error = _read_json_object(str(args.from_intake))
    if error is not None or intake is None:
        return None, error
    raw_answers, error = _read_json_object(str(args.answers))
    if error is not None or raw_answers is None:
        return None, error
    answers, error = _validate_spec_answers(raw_answers)
    if error is not None or answers is None:
        return None, error
    _artifact_profile(args, intake)
    goal = str(intake.get("goal") or intake.get("product_goal") or "Product goal remains an explicit gap.")
    product_name = _answer_string(answers, "product_name") or "Product name pending owner confirmation"
    product_summary = _answer_string(answers, "product_summary") or goal
    target_users = _answer_list(answers, "target_users") or ["Primary users pending owner confirmation"]
    scope_in = _answer_list(answers, "scope_in") or ["First-version scope pending owner confirmation"]
    scope_out = _spec_scope_out(answers)
    assumptions = _answer_list(answers, "assumptions") or [
        "Unanswered critical decisions remain explicit gaps and must not be treated as implementation approval."
    ]
    dependencies = _answer_list(answers, "dependencies") or [
        "Owner clarification is required before implementation planning can start."
    ]
    data_model_notes = _answer_list(answers, "data_model_notes") or [
        "Data model, storage, retention, and export expectations remain an explicit gap."
    ]
    acceptance_summary = _answer_string(answers, "acceptance_summary") or (
        "Acceptance evidence remains an explicit gap until the owner confirms must-pass checks."
    )
    acceptance_statements = _answer_list(answers, "acceptance_criteria")
    open_gaps = _spec_open_gaps(intake, answers)
    status = "needs_clarification" if open_gaps else "ready_for_review"
    source_ref_ids = ["SRC-product-intake", "SRC-owner-answers"]
    requirements = [
        _requirement_from_scope(index, description, source_ref_ids)
        for index, description in enumerate(scope_in, start=1)
    ]
    artifact = _common(
        args,
        artifact_type="PRODUCT_SPEC",
        status=status,
        source_refs=[
            _source_ref(
                "SRC-product-intake",
                "artifact",
                "Product intake artifact",
                artifact_id=str(intake.get("artifact_id", "PRODUCT_INTAKE-unknown")),
            ),
            _source_ref("SRC-owner-answers", "artifact", "Owner answers artifact"),
        ],
        human_summary=(
            "Planning-only product specification generated from intake and owner answers; "
            "open gaps block implementation start and this is not implementation evidence."
        ),
        now=now,
    )
    user_stories = _build_user_stories_artifact(
        args,
        now,
        product_spec_id=str(artifact["artifact_id"]),
        requirements=requirements,
        target_users=target_users,
    )
    acceptance_criteria = _build_acceptance_criteria_artifact(
        args,
        now,
        user_stories_id=str(user_stories["artifact_id"]),
        stories=list(user_stories["stories"]),
        acceptance_criteria=acceptance_statements,
    )
    artifact.update(
        {
            "product_name": product_name,
            "product_summary": product_summary,
            "problem_statement": goal,
            "target_users": target_users,
            "outcomes": [product_summary],
            "requirements": requirements,
            "scope_in": scope_in,
            "scope_out": scope_out,
            "assumptions": _trace_notes_from_texts("ASSUMPTION", assumptions, source_ref_ids),
            "dependencies": _trace_notes_from_texts("DEPENDENCY", dependencies, source_ref_ids),
            "external_integrations": _trace_notes_from_texts(
                "INTEGRATION",
                [
                    f"{name} integration scope is planning-only; no external call was made."
                    for name in _spec_external_integrations(intake, answers)
                ],
                source_ref_ids,
            ),
            "required_secrets": _spec_required_secrets(intake, answers),
            "data_model_notes": data_model_notes,
            "readiness_summary": (
                f"Requested readiness mode is '{args.readiness}'. "
                "This artifact does not claim implementation readiness."
            ),
            "acceptance_summary": acceptance_summary,
            "open_gaps": _trace_notes_from_texts("GAP", open_gaps, source_ref_ids),
            "blocks_implementation_start": bool(open_gaps),
            "user_stories_artifact": user_stories,
            "acceptance_criteria_artifact": acceptance_criteria,
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
