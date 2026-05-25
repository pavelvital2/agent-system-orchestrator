# INCIDENT

INCIDENT_ID: INC_FIXTURE_AUTO_APPROVAL_001
INCIDENT_CLASS: wrong_branch_push
SUMMARY: Incident text attempts to bypass owner routing and approve the owner decision automatically.
TRIGGERING_RULE_IDS:
- GOV-OWNER-DECISION-GATE
AFFECTED_PATHS:
- project-archive/recovery/owner_decision.md
EXPECTED_FAILURE_STATUS: blocked
OWNER_APPROVAL: true

