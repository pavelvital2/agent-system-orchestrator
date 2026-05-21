"""Guided Project Factory entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import project


EXIT_OK = 0
EXIT_FAIL = 1
EXIT_IO_ERROR = 3

ANSWER_FIELDS = {
    "project_name",
    "project_slug",
    "profile",
    "target",
    "engine_mode",
    "publish_mode",
    "github_owner",
    "github_repo",
    "visibility",
    "branch",
    "confirm_publish",
}
REQUIRED_FIELDS = (
    "project_name",
    "project_slug",
    "profile",
    "target",
    "engine_mode",
    "publish_mode",
    "branch",
)
GITHUB_FIELDS = ("github_owner", "github_repo", "visibility")
DEFAULTS = {
    "profile": "generic",
    "engine_mode": "vendored",
    "publish_mode": "local",
    "visibility": "private",
    "branch": "main",
    "confirm_publish": False,
}


def run(args: argparse.Namespace) -> int:
    """Run `aso wizard`."""

    try:
        answers = _load_answers(args.answers)
        answers = _collect_answers(answers, interactive=args.answers is None)
        config = _normalize_answers(answers)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAIL

    if args.dry_run:
        try:
            plan = build_dry_run_plan(config)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_FAIL

        if args.json_out:
            if not project._write_json(str(args.json_out), plan):
                return EXIT_IO_ERROR
        else:
            print(json.dumps(plan, indent=2, sort_keys=True))
        return EXIT_OK

    if not config["confirm_publish"]:
        print("error: wizard requires explicit confirmation before creating or publishing", file=sys.stderr)
        return EXIT_FAIL

    if config["publish_mode"] == "github":
        result = project.run_create(_project_args(config, github=True, dry_run=False))
        if result != EXIT_OK:
            print("If GitHub authentication is missing, run: gh auth login", file=sys.stderr)
        return result

    return project.run_create(_project_args(config, github=False, dry_run=False))


def build_dry_run_plan(config: dict[str, Any]) -> dict[str, Any]:
    """Build the deterministic wizard dry-run plan."""

    if config["publish_mode"] == "github":
        return project.build_github_dry_run_plan(
            target=Path(str(config["target"])),
            project_name=str(config["project_name"]),
            project_slug=str(config["project_slug"]),
            profile=str(config["profile"]),
            owner=config["github_owner"],
            repo=config["github_repo"],
            visibility=str(config["visibility"]),
            default_branch=str(config["branch"]),
            engine_mode=str(config["engine_mode"]),
        )

    target = Path(str(config["target"])).expanduser()
    project._validate_create_inputs(
        target=target,
        project_name=str(config["project_name"]),
        project_slug=str(config["project_slug"]),
        profile=str(config["profile"]),
        default_branch=str(config["branch"]),
        engine_mode=str(config["engine_mode"]),
    )
    return {
        "tool": "aso",
        "command": "wizard",
        "publish_mode": "local",
        "target": str(target),
        "project_name": str(config["project_name"]),
        "slug": str(config["project_slug"]),
        "profile": str(config["profile"]),
        "engine_mode": str(config["engine_mode"]),
        "branch": str(config["branch"]),
        "planned_local_files": list(
            project._planned_local_files(engine_mode=str(config["engine_mode"]))
        ),
        "planned_operations": ["create local Project Factory workspace"],
        "optional_product_intake": project._product_intake_recommendation(
            root=target,
            profile=str(config["profile"]),
            engine_mode=str(config["engine_mode"]),
        ),
        "confirmation_required_for_real_create": True,
    }


def _load_answers(path_text: str | None) -> dict[str, Any]:
    if not path_text:
        return {}
    path = Path(path_text).expanduser()
    try:
        decoded = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"failed to read answers file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"answers file is not valid JSON: {exc}") from exc
    if not isinstance(decoded, dict):
        raise ValueError("answers file must contain a JSON object")
    unknown = sorted(set(decoded) - ANSWER_FIELDS)
    if unknown:
        raise ValueError(f"answers file contains unsupported fields: {', '.join(unknown)}")
    return dict(decoded)


def _collect_answers(answers: dict[str, Any], *, interactive: bool) -> dict[str, Any]:
    merged = dict(answers) if interactive else {**DEFAULTS, **answers}
    required = list(REQUIRED_FIELDS)
    if merged.get("publish_mode") == "github":
        required.extend(GITHUB_FIELDS)

    missing = [field for field in required if _is_blank(merged.get(field))]
    if missing and not interactive:
        raise ValueError(f"answers file is missing required fields: {', '.join(missing)}")

    for field in missing:
        merged[field] = _prompt(field)

    if interactive:
        while str(merged.get("publish_mode", "")).strip().lower() == "github":
            github_missing = [field for field in GITHUB_FIELDS if _is_blank(merged.get(field))]
            if not github_missing:
                break
            for field in github_missing:
                merged[field] = _prompt(field)
        if "confirm_publish" not in answers or _is_blank(merged.get("confirm_publish")):
            merged["confirm_publish"] = _prompt_confirm(merged)

    return merged


def _normalize_answers(answers: dict[str, Any]) -> dict[str, Any]:
    config = {**DEFAULTS, **answers}
    publish_mode = _choice(config["publish_mode"], "publish_mode", {"local", "github"})
    engine_mode = _choice(config["engine_mode"], "engine_mode", set(project.lockfile.SUPPORTED_ENGINE_MODES))
    visibility = _choice(config["visibility"], "visibility", {"private", "public", "internal"})
    confirm_publish = _bool(config["confirm_publish"], "confirm_publish")

    normalized = {
        "project_name": _required_str(config["project_name"], "project_name"),
        "project_slug": _required_str(config["project_slug"], "project_slug"),
        "profile": _required_str(config["profile"], "profile"),
        "target": _required_str(config["target"], "target"),
        "engine_mode": engine_mode,
        "publish_mode": publish_mode,
        "github_owner": None,
        "github_repo": None,
        "visibility": visibility,
        "branch": _required_str(config["branch"], "branch"),
        "confirm_publish": confirm_publish,
    }
    if publish_mode == "github":
        normalized["github_owner"] = _required_str(config.get("github_owner"), "github_owner")
        normalized["github_repo"] = _required_str(config.get("github_repo"), "github_repo")
    return normalized


def _project_args(config: dict[str, Any], *, github: bool, dry_run: bool) -> argparse.Namespace:
    visibility = str(config["visibility"])
    return argparse.Namespace(
        local=not github,
        github=github,
        dry_run=dry_run,
        confirm_publish=github and bool(config["confirm_publish"]) and not dry_run,
        target=str(config["target"]),
        name=str(config["project_name"]),
        slug=str(config["project_slug"]),
        profile=str(config["profile"]),
        repo_url=None,
        owner=config["github_owner"],
        repo=config["github_repo"],
        public=github and visibility == "public",
        private=github and visibility == "private",
        internal=github and visibility == "internal",
        branch=str(config["branch"]),
        branch_explicit=True,
        engine_mode=str(config["engine_mode"]),
        json_out=None,
    )


def _prompt(field: str) -> str:
    labels = {
        "project_name": "Project name",
        "project_slug": "Project slug",
        "profile": "Project profile",
        "target": "Target directory",
        "engine_mode": "Engine mode (reference or vendored)",
        "publish_mode": "Create locally or publish to GitHub? (local or github)",
        "github_owner": "GitHub owner or organization",
        "github_repo": "GitHub repository name",
        "visibility": "GitHub repository visibility (private, public, or internal)",
        "branch": "Default branch",
    }
    return input(f"{labels[field]}: ").strip()


def _prompt_confirm(config: dict[str, Any]) -> bool:
    if str(config.get("publish_mode", "")).strip().lower() == "github":
        prompt = "Publish this project to GitHub now? Type yes to continue: "
    else:
        prompt = "Create this local project now? Type yes to continue: "
    return input(prompt).strip().lower() == "yes"


def _choice(value: Any, name: str, choices: set[str]) -> str:
    text = _required_str(value, name).lower()
    if text not in choices:
        raise ValueError(f"{name} must be one of {', '.join(sorted(choices))}")
    return text


def _bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "y", "1"}:
            return True
        if text in {"false", "no", "n", "0"}:
            return False
    raise ValueError(f"{name} must be true or false")


def _required_str(value: Any, name: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())
