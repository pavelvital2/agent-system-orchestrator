#!/usr/bin/env python3
"""Read-only ASO command line scaffold."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import artifact_storage
from . import runtime_schema_contracts
from .commands import (
    apply,
    archive_verify,
    artifact,
    checkpoint_preflight,
    context_pack_build,
    dashboard,
    dag,
    design,
    doctor,
    incident_fixture,
    intake,
    lifecycle,
    lint,
    package_layout,
    package_sync,
    orchestrator,
    plan_next,
    propose_checkpoint,
    propose_next_task,
    propose_transition,
    project,
    record_result,
    state_init,
    state_migrate,
    state_render,
    state_verify,
    status,
    validate_context_pack,
    validate_design,
    validate_rules,
    wizard,
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


class _StoreExplicitBranch(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | None,
        option_string: str | None = None,
    ) -> None:
        setattr(namespace, self.dest, values)
        setattr(namespace, "branch_explicit", True)


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

    design_parser = subparsers.add_parser(
        "design",
        help="Design gap governance commands.",
        description=(
            "Validate project-designer-authored gap, owner question, owner decision, "
            "and stage gate artifacts. These commands route existing audited question "
            "cards only; they do not read raw TZ semantically or generate questions."
        ),
    )
    design_subparsers = design_parser.add_subparsers(dest="design_command", metavar="COMMAND")

    design_verify_parser = design_subparsers.add_parser(
        "verify",
        help="Verify design gap and owner question artifacts.",
        description=(
            "Read-only validation for gap register shape, owner question card shape, "
            "non-technical owner question policy, audit-pass evidence, owner answer "
            "linkage, one-question-at-a-time routing, and gap/question cross-links."
        ),
    )
    _add_root_argument(design_verify_parser, validate=False)
    design_verify_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing design governance result.",
    )
    design_verify_parser.set_defaults(handler=design.run_verify)

    design_questions_parser = design_subparsers.add_parser(
        "questions",
        help="Owner question routing commands.",
        description="Route existing audited owner question cards one at a time.",
    )
    design_questions_subparsers = design_questions_parser.add_subparsers(
        dest="design_questions_command",
        metavar="COMMAND",
    )
    design_questions_next_parser = design_questions_subparsers.add_parser(
        "next",
        help="Return the next audited ready owner question card.",
        description=(
            "Select the next existing ready_for_owner card by queue position. "
            "The command does not create or rewrite question content."
        ),
    )
    _add_root_argument(design_questions_next_parser, validate=False)
    design_questions_next_parser.add_argument(
        "--json-out",
        required=True,
        metavar="PATH",
        help="Write the selected question JSON to /tmp/... or an allowed runtime report path.",
    )
    design_questions_next_parser.set_defaults(handler=design.run_questions_next)

    design_decision_parser = design_subparsers.add_parser(
        "decision",
        help="Owner decision record commands.",
        description="Record an owner answer against an existing audited question card.",
    )
    design_decision_subparsers = design_decision_parser.add_subparsers(
        dest="design_decision_command",
        metavar="COMMAND",
    )
    design_decision_record_parser = design_decision_subparsers.add_parser(
        "record",
        help="Plan or write an owner answer record for an existing question.",
        description=(
            "Validates the selected option against an existing question card. "
            "--dry-run writes nothing; --confirm-write writes only under "
            "project-runtime/owner-decisions."
        ),
    )
    _add_root_argument(design_decision_record_parser, validate=False)
    design_decision_record_parser.add_argument("--question-id", required=True, metavar="Q-ID")
    design_decision_record_parser.add_argument("--answer", required=True, metavar="OPTION_ID")
    decision_mode_group = design_decision_record_parser.add_mutually_exclusive_group(required=True)
    decision_mode_group.add_argument("--dry-run", action="store_true", help="Validate and render the answer record without writing files.")
    decision_mode_group.add_argument("--confirm-write", action="store_true", help="Write the answer record under project-runtime/owner-decisions.")
    design_decision_record_parser.set_defaults(handler=design.run_decision_record)

    design_gate_parser = design_subparsers.add_parser(
        "gate",
        help="Design stage gate commands.",
        description="Verify whether unanswered blocking gaps prevent crossing a lifecycle stage.",
    )
    design_gate_subparsers = design_gate_parser.add_subparsers(dest="design_gate_command", metavar="COMMAND")
    design_gate_verify_parser = design_gate_subparsers.add_parser(
        "verify",
        help="Verify that a lifecycle stage is not blocked by unanswered gaps.",
        description=(
            "Fails closed when the requested stage reaches or crosses an unanswered "
            "gap's blocking_stage and no accepted assumption or answer linkage exists."
        ),
    )
    _add_root_argument(design_gate_verify_parser, validate=False)
    design_gate_verify_parser.add_argument("--stage", required=True, metavar="STAGE")
    design_gate_verify_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing design gate result.",
    )
    design_gate_verify_parser.set_defaults(handler=design.run_gate_verify)

    context_pack_parser = subparsers.add_parser(
        "context-pack",
        help="Context pack proposal commands.",
        description="Dry-run/read-only context pack proposal commands.",
    )
    context_pack_subparsers = context_pack_parser.add_subparsers(dest="context_pack_command", metavar="COMMAND")
    context_pack_build_parser = context_pack_subparsers.add_parser(
        "build",
        help="Build a dry-run JSON context pack proposal from a task packet.",
        description=(
            "Parse a bounded task packet and emit a JSON context pack proposal to stdout "
            "or /tmp/... or <workspace>/project-runtime/proposals/... via --json-out. "
            "This command does not dispatch agents, "
            "mutate runtime state, commit, push, checkpoint, or approve owner decisions."
        ),
    )
    _add_root_argument(context_pack_build_parser, validate=False)
    context_pack_build_parser.add_argument(
        "--task-packet",
        required=True,
        metavar="TASK_PACKET.md",
        help="Markdown task packet to parse.",
    )
    context_pack_build_parser.add_argument(
        "--strict",
        action="store_true",
        help="Reject missing required docs and warnings as failed proposal builds.",
    )
    context_pack_build_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write proposal JSON to /tmp/... or <workspace>/project-runtime/proposals/...",
    )
    context_pack_build_parser.set_defaults(handler=context_pack_build.run_build)

    intake_parser = subparsers.add_parser(
        "intake",
        help="Raw project input intake commands.",
        description=(
            "Create governed bootstrap state from a raw TZ input without interpreting "
            "product requirements or dispatching agents."
        ),
    )
    intake_subparsers = intake_parser.add_subparsers(dest="intake_command", metavar="COMMAND")
    intake_bootstrap_parser = intake_subparsers.add_parser(
        "bootstrap",
        help="Create the first bounded requirements_analyst bootstrap task.",
        description=(
            "Validate a workspace-local TZ document and, with --confirm-write, create "
            "exactly one bootstrap task packet plus dispatch-capable runtime state."
        ),
    )
    _add_root_argument(intake_bootstrap_parser, validate=False)
    intake_bootstrap_parser.add_argument(
        "--tz",
        required=True,
        metavar="PATH",
        help="Workspace-local raw TZ Markdown path, relative to --root or absolute inside --root.",
    )
    intake_bootstrap_parser.add_argument(
        "--target-role",
        required=True,
        choices=("requirements_analyst",),
        help="Bootstrap profile role to receive the first bounded task.",
    )
    intake_bootstrap_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Explicitly allow bootstrap task and runtime state writes.",
    )
    intake_bootstrap_parser.add_argument(
        "--deterministic-timestamps",
        action="store_true",
        help="Use the fixed regression timestamp for tests and fixtures instead of current UTC.",
    )
    intake_bootstrap_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the bootstrap receipt JSON to PATH.",
    )
    intake_bootstrap_parser.set_defaults(handler=intake.run_bootstrap)

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

    propose_parser = subparsers.add_parser(
        "propose",
        help="Build guarded proposal artifacts without dispatching agents.",
        description=(
            "Build P3 proposal artifacts from existing runtime state. Proposal "
            "commands never dispatch agents or mutate canonical state sidecars."
        ),
    )
    propose_subparsers = propose_parser.add_subparsers(dest="propose_command", metavar="COMMAND")
    propose_next_task_parser = propose_subparsers.add_parser(
        "next-task",
        help="Propose the next task from current P2 state sidecars.",
        description=(
            "Verify runtime state, inspect TASK_REGISTRY, NEXT_ACTION, and CURRENT_GATE, "
            "then emit a schema-compatible next_task proposal with base state hashes. "
            "Dry-run is the default and writes no workspace files unless --json-out is "
            "explicitly supplied. --confirm-write writes only under project-runtime/proposals."
        ),
    )
    _add_root_argument(propose_next_task_parser, validate=False)
    propose_write_group = propose_next_task_parser.add_mutually_exclusive_group()
    propose_write_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Default behavior; write no workspace files except an explicit allowed --json-out.",
    )
    propose_write_group.add_argument(
        "--confirm-write",
        action="store_true",
        help="Write the proposal artifact under project-runtime/proposals/.",
    )
    propose_next_task_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write proposal JSON to /tmp/... or an allowed project-runtime proposals/reports path.",
    )
    propose_next_task_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format for stdout when --json-out is not used (default: text).",
    )
    propose_next_task_parser.set_defaults(handler=propose_next_task.run_next_task)

    propose_transition_parser = propose_subparsers.add_parser(
        "transition",
        help="Propose a guarded lifecycle transition from current P2 state sidecars.",
        description=(
            "Verify runtime state, read PROJECT_STATE current_phase, check CURRENT_GATE "
            "compatibility and evidence, then emit a schema-compatible transition proposal "
            "with base state hashes. Dry-run is the default and writes no workspace files "
            "unless --json-out is explicitly supplied. --confirm-write writes only under "
            "project-runtime/proposals."
        ),
    )
    _add_root_argument(propose_transition_parser, validate=False)
    propose_transition_parser.add_argument(
        "--to",
        required=True,
        metavar="STAGE",
        help="Requested lifecycle target stage. Unknown values produce a blocked proposal.",
    )
    propose_transition_write_group = propose_transition_parser.add_mutually_exclusive_group()
    propose_transition_write_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Default behavior; write no workspace files except an explicit allowed --json-out.",
    )
    propose_transition_write_group.add_argument(
        "--confirm-write",
        action="store_true",
        help="Write the proposal artifact under project-runtime/proposals/.",
    )
    propose_transition_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write proposal JSON to /tmp/... or an allowed project-runtime proposals/reports path.",
    )
    propose_transition_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format for stdout when --json-out is not used (default: text).",
    )
    propose_transition_parser.set_defaults(handler=propose_transition.run_transition)

    propose_checkpoint_parser = propose_subparsers.add_parser(
        "checkpoint",
        help="Propose checkpoint eligibility without executing a checkpoint.",
        description=(
            "Verify current runtime state, inspect CHECKPOINT_STATE, accepted artifacts, "
            "and audit evidence, then integrate read-only checkpoint-preflight diagnostics "
            "into a schema-compatible checkpoint proposal. P3 checkpoint execution is not "
            "implemented: this command never stages, commits, pushes, tags, invokes gh, "
            "or creates checkpoint receipts."
        ),
    )
    _add_root_argument(propose_checkpoint_parser, validate=False)
    propose_checkpoint_write_group = propose_checkpoint_parser.add_mutually_exclusive_group()
    propose_checkpoint_write_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Default behavior; write no workspace files except an explicit allowed --json-out.",
    )
    propose_checkpoint_write_group.add_argument(
        "--confirm-write",
        action="store_true",
        help="Write only the proposal artifact under project-runtime/proposals/.",
    )
    propose_checkpoint_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write proposal JSON to /tmp/... or an allowed project-runtime proposals/reports path.",
    )
    propose_checkpoint_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format for stdout when --json-out is not used (default: text).",
    )
    propose_checkpoint_parser.set_defaults(handler=propose_checkpoint.run_checkpoint)

    apply_parser = subparsers.add_parser(
        "apply",
        help="Dry-run guarded proposal apply planning.",
        description=(
            "Validate a P3 proposal against the current workspace and emit a read-only "
            "apply plan. --dry-run writes no runtime sidecars or state. --confirm-apply "
            "re-runs guards immediately before applying supported safe operations and "
            "writing a project-runtime receipt."
        ),
    )
    _add_root_argument(apply_parser, validate=False)
    apply_parser.add_argument(
        "--proposal",
        required=True,
        metavar="PATH",
        help="JSON proposal artifact to validate.",
    )
    apply_mode_group = apply_parser.add_mutually_exclusive_group()
    apply_mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Default behavior; validate and plan without mutating runtime state.",
    )
    apply_mode_group.add_argument(
        "--confirm-apply",
        action="store_true",
        help="Apply supported safe proposal operations and write an apply receipt.",
    )
    apply_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the dry-run plan or confirmed receipt JSON to /tmp/... or allowed project-runtime output paths.",
    )
    apply_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format for stdout when --json-out is not used (default: text).",
    )
    apply_parser.set_defaults(handler=apply.run)

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

    artifact_parser = subparsers.add_parser(
        "artifact",
        help="P5 artifact storage commands.",
        description=(
            "Validate and classify existing P5 artifact package manifests under "
            "project-runtime/artifacts. Write operations require --confirm-write and "
            "do not dispatch agents, mutate lifecycle state, or execute checkpoints."
        ),
    )
    artifact_subparsers = artifact_parser.add_subparsers(dest="artifact_command", metavar="COMMAND")
    artifact_validate_parser = artifact_subparsers.add_parser(
        "validate",
        help="Validate a P5 artifact package manifest.",
        description="Read-only validation for artifact_package_manifest.schema.json and package path boundaries.",
    )
    _add_root_argument(artifact_validate_parser, validate=False)
    artifact_validate_parser.add_argument(
        "--package",
        "--artifact",
        dest="artifact",
        required=True,
        metavar="PATH",
        help="Artifact package manifest JSON to validate.",
    )
    artifact_validate_parser.add_argument(
        "--type",
        dest="artifact_type",
        choices=artifact.ALLOWED_ARTIFACT_TYPES,
        help="Expected artifact_type value for the package manifest.",
    )
    artifact_validate_parser.add_argument(
        "--task-id",
        help="Expected task_id value for the package manifest.",
    )
    artifact_validate_parser.add_argument(
        "--role",
        choices=artifact.ALLOWED_ROLES,
        help="Expected role value for the package manifest.",
    )
    artifact_validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Run validation in strict mode.",
    )
    artifact_validate_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    artifact_validate_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write validation report JSON to /tmp/... or project-runtime/reports/...",
    )
    artifact_validate_parser.set_defaults(handler=artifact.run_validate)

    artifact_accept_parser = artifact_subparsers.add_parser(
        "accept",
        help="Copy a candidate artifact into the accepted bucket.",
        description=(
            "Classify an existing candidate artifact as accepted by append-only copy. "
            "Without --confirm-write the command returns a blocked dry-run plan."
        ),
    )
    _add_root_argument(artifact_accept_parser, validate=False)
    artifact_accept_parser.add_argument(
        "--package",
        "--artifact",
        dest="artifact",
        required=True,
        metavar="project-runtime/artifacts/candidates/...",
        help="Candidate artifact path under project-runtime/artifacts/candidates.",
    )
    artifact_accept_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Write the accepted copy under project-runtime/artifacts/accepted.",
    )
    artifact_accept_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    artifact_accept_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write classification report JSON to /tmp/... or project-runtime/reports/...",
    )
    artifact_accept_parser.set_defaults(handler=artifact.run_accept)

    artifact_reject_parser = artifact_subparsers.add_parser(
        "reject",
        help="Copy a candidate artifact into the rejected bucket.",
        description=(
            "Classify an existing candidate artifact as rejected by append-only copy. "
            "Without --confirm-write the command returns a blocked dry-run plan."
        ),
    )
    _add_root_argument(artifact_reject_parser, validate=False)
    artifact_reject_parser.add_argument(
        "--package",
        "--artifact",
        dest="artifact",
        required=True,
        metavar="project-runtime/artifacts/candidates/...",
        help="Candidate artifact path under project-runtime/artifacts/candidates.",
    )
    artifact_reject_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Write the rejected copy under project-runtime/artifacts/rejected.",
    )
    artifact_reject_parser.add_argument(
        "--reason",
        help="Reason for rejecting the candidate artifact.",
    )
    artifact_reject_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    artifact_reject_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write classification report JSON to /tmp/... or project-runtime/reports/...",
    )
    artifact_reject_parser.set_defaults(handler=artifact.run_reject)

    artifact_list_parser = artifact_subparsers.add_parser(
        "list",
        help="List governed artifact storage files.",
        description="Read-only listing of project-runtime/artifacts buckets.",
    )
    _add_root_argument(artifact_list_parser, validate=False)
    artifact_list_parser.add_argument(
        "--state",
        dest="bucket",
        choices=("candidates", "accepted", "rejected"),
        help="Limit listing to one artifact state.",
    )
    artifact_list_parser.add_argument(
        "--bucket",
        dest="bucket",
        choices=artifact_storage.ARTIFACT_STORAGE_BUCKETS,
        help="Limit listing to one bucket.",
    )
    artifact_list_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    artifact_list_parser.set_defaults(handler=artifact.run_list)

    artifact_render_parser = artifact_subparsers.add_parser(
        "render",
        help="Render a deterministic artifact storage report.",
        description=(
            "Render a read-only artifact storage report to stdout. Writing with --out "
            "is limited to project-runtime/reports, "
            "project-runtime/rendered, or /tmp."
        ),
    )
    _add_root_argument(artifact_render_parser, validate=False)
    artifact_render_parser.add_argument(
        "--package",
        dest="artifact",
        metavar="PATH",
        help="Render a report for one artifact package path.",
    )
    artifact_render_parser.add_argument(
        "--state",
        dest="bucket",
        choices=("candidates", "accepted", "rejected"),
        help="Limit rendering to one artifact state.",
    )
    artifact_render_parser.add_argument(
        "--bucket",
        dest="bucket",
        choices=artifact_storage.ARTIFACT_STORAGE_BUCKETS,
        help="Limit rendering to one bucket.",
    )
    artifact_render_parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    artifact_render_parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write rendered report to /tmp/... or project-runtime/reports|rendered/...",
    )
    artifact_render_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Accepted for compatibility; explicit --out report writes are path-policy guarded.",
    )
    artifact_render_parser.set_defaults(handler=artifact.run_render)

    orchestrator_parser = subparsers.add_parser(
        "orchestrator",
        help="Read-only orchestrator conveyor summaries.",
        description=(
            "Summarize ASO conveyor state from runtime sidecars and receipt/report "
            "JSON without dispatching agents, executing checkpoints, or mutating state."
        ),
    )
    orchestrator_subparsers = orchestrator_parser.add_subparsers(dest="orchestrator_command", metavar="COMMAND")

    orchestrator_status_parser = orchestrator_subparsers.add_parser(
        "status",
        help="Summarize current orchestrator-visible state.",
    )
    _add_root_argument(orchestrator_status_parser, validate=False)
    orchestrator_status_parser.add_argument("--format", choices=("text", "json"), default="text")
    orchestrator_status_parser.add_argument("--json-out", metavar="PATH")
    orchestrator_status_parser.set_defaults(handler=orchestrator.run_status)

    orchestrator_next_parser = orchestrator_subparsers.add_parser(
        "next",
        help="Summarize the current NEXT_ACTION sidecar.",
    )
    _add_root_argument(orchestrator_next_parser, validate=False)
    orchestrator_next_parser.add_argument("--format", choices=("text", "json"), default="text")
    orchestrator_next_parser.add_argument("--json-out", metavar="PATH")
    orchestrator_next_parser.set_defaults(handler=orchestrator.run_next)

    record_result_parser = subparsers.add_parser(
        "record-result",
        help="Dry-run/read-only RESULT routing proposal.",
        description=(
            "Dry-run/read-only parser for a profile-agent RESULT or AUDIT_RESULT. "
            "Reports the governed "
            "next-action proposal without mutating state, dispatching agents, "
            "checkpointing, committing, pushing, or approving owner decisions."
        ),
    )
    record_result_parser.add_argument(
        "--result",
        required=True,
        metavar="RESULT.md",
        help="Profile RESULT or AUDIT_RESULT Markdown artifact to inspect.",
    )
    record_result_parser.add_argument(
        "--dry-run",
        required=True,
        action="store_true",
        help="Required safety acknowledgement; command is proposal/read-only only.",
    )
    record_result_parser.add_argument(
        "--strict",
        action="store_true",
        help="Reject malformed or overclaiming RESULT files.",
    )
    record_result_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the dry-run routing report as JSON to stdout.",
    )
    record_result_parser.set_defaults(handler=record_result.run)

    lifecycle_parser = subparsers.add_parser(
        "lifecycle",
        help="Agent lifecycle event materializers.",
        description="Orchestrator-owned lifecycle event materializers; no agent dispatch is performed.",
    )
    lifecycle_subparsers = lifecycle_parser.add_subparsers(dest="lifecycle_command", metavar="COMMAND")
    receive_result_parser = lifecycle_subparsers.add_parser(
        "receive-result",
        help="Record a RESULT_RECEIVED event for a completed agent RESULT.",
        description=(
            "Validate a RESULT artifact and append a RESULT_RECEIVED lifecycle event "
            "to project-runtime/agents/instances.jsonl. Writes require --confirm-write."
        ),
    )
    _add_root_argument(receive_result_parser, validate=False)
    receive_result_parser.add_argument(
        "--from-result",
        required=True,
        metavar="RESULT.md",
        help="Profile RESULT or AUDIT_RESULT Markdown artifact received from the agent instance.",
    )
    receive_result_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Append the result receipt event under project-runtime/agents/instances.jsonl.",
    )
    receive_result_parser.set_defaults(handler=lifecycle.run_receive_result)

    terminate_agent_parser = lifecycle_subparsers.add_parser(
        "terminate-agent",
        help="Record an agent termination event after RESULT receipt.",
        description=(
            "Validate a RESULT artifact, require RESULT_RECEIVED and ARTIFACT_ACCEPTED "
            "predecessor events, then append AGENT_TERMINATED and AUDIT_ROUTE_READY "
            "lifecycle events to project-runtime/agents/instances.jsonl. Writes require "
            "--confirm-write."
        ),
    )
    _add_root_argument(terminate_agent_parser, validate=False)
    terminate_agent_parser.add_argument(
        "--from-result",
        required=True,
        metavar="RESULT.md",
        help="Profile RESULT or AUDIT_RESULT Markdown artifact that completed the agent instance.",
    )
    terminate_agent_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Append the termination event under project-runtime/agents/instances.jsonl.",
    )
    terminate_agent_parser.set_defaults(handler=lifecycle.run_terminate_agent)

    incident_parser = subparsers.add_parser(
        "incident",
        help="Incident recovery proposal commands.",
        description="Dry-run/read-only incident recovery proposal commands.",
    )
    incident_subparsers = incident_parser.add_subparsers(dest="incident_command", metavar="COMMAND")
    incident_fixture_parser = incident_subparsers.add_parser(
        "fixture",
        help="Build a dry-run regression fixture proposal from an incident.",
        description=(
            "Parse explicit incident metadata and emit a deterministic regression "
            "fixture proposal without mutating runtime state, dispatching agents, "
            "checkpointing, committing, pushing, weakening validators, or approving "
            "owner decisions."
        ),
    )
    _add_root_argument(incident_fixture_parser, validate=False)
    incident_fixture_parser.add_argument(
        "--incident",
        required=True,
        metavar="INCIDENT.md",
        help="Structured incident artifact to inspect.",
    )
    incident_fixture_parser.add_argument(
        "--dry-run",
        required=True,
        action="store_true",
        help="Required safety acknowledgement; command is proposal/read-only only.",
    )
    incident_fixture_parser.add_argument(
        "--strict",
        action="store_true",
        help="Reject vague incidents, missing rule ids, and safety-bypass claims.",
    )
    incident_fixture_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write proposal JSON to /tmp/... or <workspace>/project-runtime/proposals/...",
    )
    incident_fixture_parser.add_argument(
        "--out",
        metavar="PATH",
        help="Render proposal Markdown to /tmp/... or <workspace>/project-runtime/proposals/...",
    )
    incident_fixture_parser.set_defaults(handler=incident_fixture.run_fixture)

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

    dag_parser = subparsers.add_parser(
        "dag",
        help="Task dependency graph inspection commands.",
        description="Read-only task dependency graph verification and rendering commands.",
    )
    dag_subparsers = dag_parser.add_subparsers(dest="dag_command", metavar="COMMAND")
    dag_verify_parser = dag_subparsers.add_parser(
        "verify",
        help="Verify TASK_REGISTRY dependency graph consistency.",
        description=(
            "Read-only verification for TASK_REGISTRY dependencies, duplicate task ids, "
            "cycles, status/dependency consistency, and requester-return metadata."
        ),
    )
    _add_root_argument(dag_verify_parser, validate=False)
    dag_verify_parser.add_argument(
        "--strict",
        action="store_true",
        help="Accepted for consistency with verification commands; DAG findings are always enforced.",
    )
    dag_verify_parser.set_defaults(handler=dag.run_verify)

    dag_render_parser = dag_subparsers.add_parser(
        "render",
        help="Render TASK_REGISTRY dependency graph.",
        description=(
            "Read-only rendering for TASK_REGISTRY dependencies. Prints to stdout by "
            "default or writes to /tmp/... or <workspace>/project-runtime/reports/..."
        ),
    )
    _add_root_argument(dag_render_parser, validate=False)
    dag_render_parser.add_argument(
        "--format",
        choices=("mermaid", "dot"),
        default="mermaid",
        help="Graph output format (default: mermaid).",
    )
    dag_render_parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write rendered graph to /tmp/... or <workspace>/project-runtime/reports/...",
    )
    dag_render_parser.set_defaults(handler=dag.run_render)

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

    package_layout_parser = subparsers.add_parser(
        "package-layout",
        help="Package layout inspection commands.",
        description="Read-only package layout inspection commands.",
    )
    package_layout_subparsers = package_layout_parser.add_subparsers(
        dest="package_layout_command",
        metavar="COMMAND",
    )
    package_layout_verify_parser = package_layout_subparsers.add_parser(
        "verify",
        help="Verify the canonical ASO package layout.",
        description=(
            "Read-only verification that the canonical ASO package lives under "
            "agent-system/tools/aso and no root duplicate package is tracked."
        ),
    )
    _add_root_argument(package_layout_verify_parser, validate=False)
    package_layout_verify_parser.add_argument(
        "--mode",
        choices=("package",),
        default="package",
        help="Verification mode (only package is supported).",
    )
    package_layout_verify_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing package-layout result.",
    )
    package_layout_verify_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the package-layout verification report as JSON to stdout.",
    )
    package_layout_verify_parser.set_defaults(handler=package_layout.run_verify)

    package_sync_parser = subparsers.add_parser(
        "package-sync",
        help="Deprecated alias for package-layout inspection commands.",
        description="Deprecated read-only alias for package-layout inspection commands.",
    )
    package_sync_subparsers = package_sync_parser.add_subparsers(
        dest="package_sync_command",
        metavar="COMMAND",
    )
    package_sync_verify_parser = package_sync_subparsers.add_parser(
        "verify",
        help="Deprecated alias for package-layout verify.",
        description="Deprecated read-only alias for package-layout verify.",
    )
    _add_root_argument(package_sync_verify_parser, validate=False)
    package_sync_verify_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a failing package-layout result.",
    )
    package_sync_verify_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the package-layout verification report as JSON to stdout.",
    )
    package_sync_verify_parser.set_defaults(handler=package_sync.run_verify)

    state_parser = subparsers.add_parser(
        "state",
        help="Workspace state commands.",
        description="Workspace runtime state commands.",
    )
    state_subparsers = state_parser.add_subparsers(dest="state_command", metavar="COMMAND")
    state_init_parser = state_subparsers.add_parser(
        "init",
        help="Initialize Runtime Schema 3.1.1 JSON state sidecars.",
        description=(
            "Plan or create Runtime Schema 3.1.1 JSON sidecars under project-runtime/state. "
            "Runtime writes use current UTC timestamps by default. Dry-run writes nothing; "
            "writes require --confirm-write."
        ),
    )
    _add_root_argument(state_init_parser, validate=False)
    state_init_parser.add_argument(
        "--project-name",
        metavar="TEXT",
        help="Project display name for PROJECT_STATE (default: derived from --root).",
    )
    state_init_parser.add_argument(
        "--project-slug",
        metavar="TEXT",
        help="Project slug for workspace identity (default: derived from --root).",
    )
    state_init_parser.add_argument(
        "--profile",
        default="orchestrator",
        metavar="TEXT",
        help="Profile name recorded in SCHEMA_MANIFEST (default: orchestrator).",
    )
    state_init_parser.add_argument(
        "--repo-url",
        metavar="URL_OR_NONE",
        help="Expected repository URL (default: detected remote.origin.url or NONE).",
    )
    state_init_parser.add_argument(
        "--branch",
        metavar="TEXT",
        help="Expected branch (default: detected current branch or NONE).",
    )
    state_init_parser.add_argument(
        "--package-version",
        default=runtime_schema_contracts.ACTIVE_PACKAGE_VERSION,
        help=f"Package version to record (default: {runtime_schema_contracts.ACTIVE_PACKAGE_VERSION}).",
    )
    state_init_parser.add_argument(
        "--runtime-schema-version",
        default="3.1.1",
        help="Runtime schema version to initialize (default: 3.1.1).",
    )
    state_init_parser.add_argument(
        "--tz",
        metavar="PATH",
        help="Workspace-local TZ document to validate and canonicalize to project-input/TZ.md.",
    )
    state_init_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a deterministic JSON plan and write no files.",
    )
    state_init_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Explicitly allow writes under project-runtime/state.",
    )
    state_init_parser.add_argument(
        "--deterministic-timestamps",
        action="store_true",
        help="Use the fixed regression timestamp for tests and fixtures instead of current UTC.",
    )
    state_init_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the dry-run plan or confirmed write receipt JSON to PATH.",
    )
    state_init_parser.set_defaults(handler=state_init.run)

    state_migrate_parser = state_subparsers.add_parser(
        "migrate",
        help="Migrate compatible legacy JSON state sidecars to Runtime Schema 3.1.1.",
        description=(
            "Plan or perform a deterministic migration from compatible Runtime Schema "
            "2.0.0 sidecars to Runtime Schema 3.1.1 envelopes. Dry-run writes nothing; "
            "writes require --confirm-write and produce a governed migration receipt."
        ),
    )
    _add_root_argument(state_migrate_parser, validate=False)
    state_migrate_parser.add_argument(
        "--to",
        default="3.1.1",
        help="Target runtime schema version (default: 3.1.1).",
    )
    state_migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a deterministic JSON migration plan and write no files.",
    )
    state_migrate_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Explicitly allow writes under project-runtime/state and project-runtime/reports.",
    )
    state_migrate_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the migration plan or receipt JSON under /tmp or project-runtime reports/receipts.",
    )
    state_migrate_parser.set_defaults(handler=state_migrate.run)

    state_render_parser = state_subparsers.add_parser(
        "render",
        help="Render Runtime Schema reports or materialize compatibility views.",
        description=(
            "Render deterministic Markdown or JSON reports from project-runtime/state "
            "JSON sidecars. The command is read-only except for explicit --out report "
            "writes or --confirm-write materialization of derived project-runtime/*.md "
            "compatibility views."
        ),
    )
    _add_root_argument(state_render_parser, validate=False)
    state_render_parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Report output format (default: markdown).",
    )
    state_render_parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write report to /tmp/... or <workspace>/project-runtime/reports|rendered/...",
    )
    state_render_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Materialize derived project-runtime/*.md compatibility views from JSON sidecars.",
    )
    state_render_parser.set_defaults(handler=state_render.run)

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

    project_parser = subparsers.add_parser(
        "project",
        help="Project Factory workspace commands.",
        description="Project Factory local workspace creation commands.",
    )
    project_subparsers = project_parser.add_subparsers(dest="project_command", metavar="COMMAND")
    project_create_parser = project_subparsers.add_parser(
        "create",
        help="Create a local Project Factory workspace.",
        description=(
            "Create a clean local Project Factory workspace. Local mode does not "
            "create GitHub repositories, use credentials, commit, push, dispatch agents, "
            "or mutate runtime schema."
        ),
    )
    create_mode_group = project_create_parser.add_mutually_exclusive_group(required=True)
    create_mode_group.add_argument(
        "--local",
        action="store_true",
        help="Create a local workspace only; no network or GitHub operations are performed.",
    )
    create_mode_group.add_argument(
        "--github",
        action="store_true",
        help="Plan or publish a GitHub-backed workspace.",
    )
    project_create_parser.add_argument(
        "--target",
        required=True,
        metavar="PATH",
        help="Empty target directory to create, or a path whose final directory does not yet exist.",
    )
    project_create_parser.add_argument(
        "--name",
        required=True,
        metavar="TEXT",
        help="Generated project display name.",
    )
    project_create_parser.add_argument(
        "--slug",
        required=True,
        metavar="TEXT",
        help="Filesystem and repository safe project slug.",
    )
    project_create_parser.add_argument(
        "--profile",
        default="generic",
        metavar="TEXT",
        help="Project profile metadata to record in aso.lock (default: generic).",
    )
    project_create_parser.add_argument(
        "--repo-url",
        default=None,
        metavar="URL_OR_NONE",
        help="Repository URL metadata to record in aso.lock; use none when unknown.",
    )
    project_create_parser.add_argument(
        "--branch",
        default="main",
        action=_StoreExplicitBranch,
        metavar="TEXT",
        help="Default branch metadata to record in aso.lock (default: main).",
    )
    project_create_parser.add_argument(
        "--engine-mode",
        choices=project.lockfile.SUPPORTED_ENGINE_MODES,
        default="vendored",
        help="ASO engine mode for the generated project (default: vendored).",
    )
    project_create_parser.add_argument(
        "--owner",
        default=None,
        metavar="OWNER",
        help="GitHub owner or organization for --github mode.",
    )
    project_create_parser.add_argument(
        "--repo",
        default=None,
        metavar="REPO",
        help="GitHub repository name for --github mode.",
    )
    visibility_group = project_create_parser.add_mutually_exclusive_group()
    visibility_group.add_argument(
        "--public",
        action="store_true",
        help="Plan or publish a public GitHub repository.",
    )
    visibility_group.add_argument(
        "--private",
        action="store_true",
        help="Plan or publish a private GitHub repository.",
    )
    visibility_group.add_argument(
        "--internal",
        action="store_true",
        help="Plan or publish an internal GitHub repository.",
    )
    publish_mode_group = project_create_parser.add_mutually_exclusive_group()
    publish_mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="For --github, emit a deterministic publication plan without git, gh, network, or filesystem writes.",
    )
    publish_mode_group.add_argument(
        "--confirm-publish",
        action="store_true",
        help="Confirm real GitHub publication; requires explicit visibility and GitHub CLI authentication.",
    )
    project_create_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write a GitHub dry-run plan or publish receipt JSON to this explicit path.",
    )
    project_create_parser.set_defaults(handler=project.run_create)

    project_verify_clean_parser = project_subparsers.add_parser(
        "verify-clean",
        help="Verify a generated project publication boundary.",
        description=(
            "Read-only verification for Project Factory generated project cleanliness, "
            "including aso.lock, .gitignore, tracked forbidden artifacts, nested vendored "
            "Git metadata, and repository metadata when available."
        ),
    )
    _add_root_argument(project_verify_clean_parser, validate=False)
    project_verify_clean_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when generated project cleanliness violations are found.",
    )
    project_verify_clean_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the verify-clean report JSON to this explicit path.",
    )
    project_verify_clean_parser.set_defaults(handler=project.run_verify_clean)

    wizard_parser = subparsers.add_parser(
        "wizard",
        help="Guided Project Factory workspace creation.",
        description=(
            "Guide users through Project Factory workspace creation. Dry-run emits a "
            "deterministic plan without git, gh, network, or filesystem writes. Real "
            "creation or publication requires explicit confirmation."
        ),
    )
    wizard_parser.add_argument(
        "--answers",
        metavar="PATH",
        help="Read non-interactive wizard answers from a JSON file.",
    )
    wizard_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit a deterministic plan and perform no local creation, git, gh, or publish operations.",
    )
    wizard_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the wizard dry-run plan JSON to this explicit path.",
    )
    wizard_parser.set_defaults(handler=wizard.run)

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
