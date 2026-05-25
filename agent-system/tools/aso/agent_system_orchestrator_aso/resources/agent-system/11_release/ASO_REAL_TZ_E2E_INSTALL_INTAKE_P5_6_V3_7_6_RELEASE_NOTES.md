# ASO Real-TZ E2E Install and Intake P5.6 v3.7.6 Release Notes

## Version Tuple

```text
CURRENT_PACKAGE_VERSION: 3.7.6
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.6
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Summary

P5.6 closes the real-TZ installed-orchestrator E2E correction line. The active
package and governance ruleset versions advance to `3.7.6`; Runtime Schema
remains `3.1.1`; Artifact Package Schema remains `1.1.0`.

The accepted operator path is an installed ASO CLI from the clean source
installer, a project TZ document under an external workspace
`project-input/`, confirmed state initialization, confirmed intake bootstrap,
strict state verification, and read-only `plan-next`.

## Official Installed-Orchestrator Workflow

```text
ASO_ROOT=$(pwd)
WORK=/tmp/aso_p56_real_tz_workspace
rm -rf "$WORK"
mkdir -p "$WORK/project-input"
cp /path/to/TZ_REAL_E2E_TELEGRAM_BOT.md "$WORK/project-input/TZ_REAL_E2E_TELEGRAM_BOT.md"
bash agent-system/scripts/install_aso_clean.sh --source "$ASO_ROOT" --venv /tmp/aso_p56_installed_venv --source-copy /tmp/aso_p56_source_copy --with-test
. /tmp/aso_p56_installed_venv/bin/activate
aso state init --root "$WORK" --tz project-input/TZ_REAL_E2E_TELEGRAM_BOT.md --confirm-write
aso intake bootstrap --root "$WORK" --tz project-input/TZ_REAL_E2E_TELEGRAM_BOT.md --target-role requirements_analyst --confirm-write
aso state verify --root "$WORK" --strict
aso plan-next --root "$WORK" --strict
```

Expected planning result: dispatch-capable `CREATE_AGENT` for one bounded
`requirements_analyst` bootstrap task packet. ASO does not launch that agent;
the orchestrator still follows the governed audit, correction, and checkpoint
rules after any worker RESULT.

## Unsupported Patterns

- Clean install validation with virtualenvs or source copies inside the live
  checkout.
- Direct `pip install .` or `pip install -e .` as clean-source install
  evidence.
- Passing an IANA timezone string where a project TZ document path is required.
- Expecting `intake bootstrap` to mutate state without `--confirm-write`.
- Treating `plan-next` as live dispatch, audit, checkpoint, commit, push,
  product generation, or secret collection authority.

## Not Included

- Runtime schema migration.
- Artifact package schema migration.
- Semantic reading of TZ content.
- Product source generation.
- Telegram API calls or token collection.
- Daemon mode, live dispatch executor, checkpoint executor, ASO Studio, or
  distributed workers.

## Validation

Local final validation evidence is recorded in
`agent-system/11_release/ASO_REAL_TZ_E2E_INSTALL_INTAKE_P5_6_V3_7_6_VALIDATION_REPORT.md`.
Remote GitHub Actions evidence remains a post-push observation and is not
claimed by these local release evidence edits.
