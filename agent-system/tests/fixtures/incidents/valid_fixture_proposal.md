# INCIDENT

INCIDENT_ID: INC_FIXTURE_VALID_001
INCIDENT_CLASS: forbidden_files
SUMMARY: Profile result attempted to include a forbidden runtime mutation as accepted evidence.
TRIGGERING_RULE_IDS:
- GOV-FORBIDDEN-FILES
- GOV-CHECKPOINT-AUDIT-GATE
AFFECTED_PATHS:
- project-runtime/state/project_state.md
EXPECTED_FAILURE_STATUS: failed

