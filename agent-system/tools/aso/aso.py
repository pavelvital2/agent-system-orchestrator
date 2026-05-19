#!/usr/bin/env python3
"""Read-only ASO command line scaffold."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from commands import (
    archive_verify,
    checkpoint_preflight,
    dashboard,
    doctor,
    lint,
    plan_next,
    state_verify,
    status,
    validate_context_pack,
    validate_design,
    validate_rules,
)


EXIT_USAGE = 2


def _root_path(value: str) -> Path:
    return Path(value).expanduser()


def _existing_root(value: str) -> Path:
    root = _root_path(value)
    if not root.exists() or not root.is_dir():
        raise argparse.ArgumentTypeError(f"project root is not a readable directory: {value}")
    return root


def _add_root_argument(parser: argparse.ArgumentParser, *, validate: bool = True) -> None:
    parser.add_argument(
        "--root",
        default=Path("."),
        type=_existing_root if validate else _root_path,
        help="Project root to inspect (default: current directory).",
    )


def _add_mode_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mode",
        choices=("workspace", "package"),
        default="workspace",
        help=(
            "Inspection mode. workspace reads generated project-runtime state; "
            "package validates the packaged agent-system tree without requiring root "
            "project-runtime (default: workspace)."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aso",
        description="Read-only Agent System Orchestrator control-plane helper.",
    )
    parser.set_defaults(handler=None)

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    status_parser = subparsers.add_parser(
        "status",
        help="Summarize workspace runtime state or package repository checks.",
        description=(
            "Read project-runtime files in workspace mode, or validate packaged "
            "agent-system structure in package mode."
        ),
    )
    _add_root_argument(status_parser)
    _add_mode_argument(status_parser)
    status_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the status report JSON to this explicit path.",
    )
    status_parser.set_defaults(handler=status.run)

    lint_parser = subparsers.add_parser(
        "lint",
        help="Check workspace runtime consistency or package repository rules.",
        description=(
            "Inspect runtime files in workspace mode, or validate package repository "
            "structure in package mode."
        ),
    )
    _add_root_argument(lint_parser, validate=False)
    _add_mode_argument(lint_parser)
    lint_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing lint result.",
    )
    lint_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the lint report JSON to this explicit path.",
    )
    lint_parser.set_defaults(handler=lint.run)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run read-only package or workspace diagnostics.",
        description=(
            "Inspect ASO package command readiness in package mode, or workspace "
            "runtime, identity, repository lock, and checkpoint readiness signals "
            "in workspace mode."
        ),
    )
    _add_root_argument(doctor_parser, validate=False)
    _add_mode_argument(doctor_parser)
    doctor_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing doctor result.",
    )
    doctor_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the doctor report JSON to this explicit path.",
    )
    doctor_parser.set_defaults(handler=doctor.run)

    validate_design_parser = subparsers.add_parser(
        "validate-design",
        help="Validate a solution architect design Markdown artifact.",
        description=(
            "Read-only validation for DESIGN_OUTPUT_CONTRACT, design traceability "
            "rules, downstream task readiness, testing strategy, and product "
            "capability evidence."
        ),
    )
    validate_design_parser.add_argument(
        "design_path",
        metavar="DESIGN.md",
        help="Markdown design artifact to inspect.",
    )
    _add_root_argument(validate_design_parser, validate=False)
    validate_design_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing validation result.",
    )
    validate_design_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the design validation report JSON to this explicit path.",
    )
    validate_design_parser.set_defaults(handler=validate_design.run)

    validate_context_pack_parser = subparsers.add_parser(
        "validate-context-pack",
        help="Validate a bounded JSON context pack.",
        description=(
            "Read-only validation for inter-agent JSON context packs, including "
            "required shape, context budget, archive/deprecated path rejection, "
            "forbidden document checks, and required document existence under --root."
        ),
    )
    validate_context_pack_parser.add_argument(
        "context_pack_path",
        metavar="CONTEXT_PACK.json",
        help="JSON context pack artifact to inspect.",
    )
    _add_root_argument(validate_context_pack_parser, validate=False)
    validate_context_pack_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing validation result.",
    )
    validate_context_pack_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the context pack validation report JSON to this explicit path.",
    )
    validate_context_pack_parser.set_defaults(handler=validate_context_pack.run)

    validate_rules_parser = subparsers.add_parser(
        "validate-rules",
        help="Validate the packaged governance rule registry.",
        description=(
            "Read-only validation for governance_rules.json structure, source "
            "links, severities, uniqueness, rationale, and expected action semantics."
        ),
    )
    _add_root_argument(validate_rules_parser, validate=False)
    validate_rules_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing validation result.",
    )
    validate_rules_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the rule registry validation report JSON to this explicit path.",
    )
    validate_rules_parser.set_defaults(handler=validate_rules.run)

    plan_next_parser = subparsers.add_parser(
        "plan-next",
        help="Dry-run/read-only next orchestrator action planning.",
        description=(
            "Dry-run/read-only planner that verifies workspace state sidecars, "
            "reads governance rules, and reports the next orchestrator action "
            "or blockers without mutating state."
        ),
    )
    _add_root_argument(plan_next_parser, validate=False)
    plan_next_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat verification warnings as blocking dry-run planner findings.",
    )
    plan_next_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the dry-run/read-only plan report JSON to this explicit path.",
    )
    plan_next_parser.set_defaults(handler=plan_next.run)

    checkpoint_preflight_parser = subparsers.add_parser(
        "checkpoint-preflight",
        help="Read-only checkpoint eligibility preflight.",
        description=(
            "Read-only checkpoint eligibility preflight. Reports checkpoint "
            "eligibility and blockers without staging, committing, pushing, "
            "repairing state, or cleaning up files."
        ),
    )
    _add_root_argument(checkpoint_preflight_parser, validate=False)
    _add_mode_argument(checkpoint_preflight_parser)
    checkpoint_preflight_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as blocking checkpoint eligibility findings.",
    )
    checkpoint_preflight_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the read-only checkpoint preflight report JSON to this explicit path.",
    )
    checkpoint_preflight_parser.set_defaults(handler=checkpoint_preflight.run)

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Render a safe static workspace dashboard.",
        description=(
            "Render static HTML summarizing workspace state, blockers, task, audit, "
            "checkpoint, and context-budget signals. Prints HTML to stdout by "
            "default; explicit file output is restricted to /tmp or "
            "<workspace>/project-runtime/dashboard."
        ),
    )
    _add_root_argument(dashboard_parser, validate=False)
    dashboard_parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write static HTML to /tmp/... or <workspace>/project-runtime/dashboard/...",
    )
    dashboard_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the dashboard report JSON to /tmp/... or <workspace>/project-runtime/dashboard/...",
    )
    dashboard_parser.set_defaults(handler=dashboard.run)

    archive_parser = subparsers.add_parser(
        "archive",
        help="Archive inspection commands.",
        description="Read-only archive inspection commands.",
    )
    archive_subparsers = archive_parser.add_subparsers(dest="archive_command", metavar="COMMAND")
    verify_parser = archive_subparsers.add_parser(
        "verify",
        help="Verify packaged ASO archive structure.",
        description="Inspect an ASO archive for required project content.",
    )
    _add_root_argument(verify_parser)
    verify_parser.add_argument(
        "--archive",
        required=True,
        metavar="PATH",
        help="Archive to inspect (.zip, .tgz, .tar.gz, or .tar).",
    )
    verify_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the archive verification report JSON to this explicit path.",
    )
    verify_parser.set_defaults(handler=archive_verify.run)

    state_parser = subparsers.add_parser(
        "state",
        help="Workspace state inspection commands.",
        description="Read-only workspace state inspection commands.",
    )
    state_subparsers = state_parser.add_subparsers(dest="state_command", metavar="COMMAND")
    state_verify_parser = state_subparsers.add_parser(
        "verify",
        help="Verify workspace JSON state sidecars.",
        description=(
            "Read-only verification for project-runtime/state JSON sidecars, "
            "matching Markdown compatibility views, task references, and checkpoint policy signals."
        ),
    )
    _add_root_argument(state_verify_parser, validate=False)
    state_verify_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing state verification result.",
    )
    state_verify_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the state verification report JSON to this explicit path.",
    )
    state_verify_parser.set_defaults(handler=state_verify.run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.handler is None:
        parser.print_help()
        return EXIT_USAGE
    return int(args.handler(args))


if __name__ == "__main__":
    sys.exit(main())
