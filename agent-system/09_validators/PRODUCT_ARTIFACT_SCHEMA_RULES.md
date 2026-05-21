# Product Artifact Schema Rules

P4 product artifact schemas live under:

```text
agent-system/09_validators/schemas/product_artifacts/
```

Reusable JSON templates live under:

```text
agent-system/03_templates/product_artifacts/
```

The aggregate schema is `product_artifact.schema.json`. The per-artifact
schema files reference aggregate definitions for:

```text
PRODUCT_INTAKE
OPEN_QUESTIONS
OWNER_DECISION_CARDS
PRODUCT_SPEC
USER_STORIES
ACCEPTANCE_CRITERIA
CAPABILITY_MATRIX
PRODUCT_PLAN
```

Every artifact uses the P4 common envelope:

```text
artifact_id
artifact_type
schema_version: 1.0.0
package_version: 3.6.0
runtime_schema_version: 3.1.0
created_at
created_by: aso
target_root
profile
readiness_mode
status
source_refs
human_summary
```

Allowed readiness modes are `mvp`, `business_ready`, `production_ready`, and
`enterprise_like`.

Allowed artifact statuses are `proposed`, `needs_clarification`, `blocked`,
`ready_for_review`, `accepted_by_owner`, and `out_of_scope`. Product completion
statuses such as `implemented`, `mvp_ready`, `product_pass`,
`final_acceptance`, and `checkpoint_done` are not valid P4 artifact statuses.

Product artifact templates are planning templates only. They must not collect
or store real secret values, create task packets, queue dispatches, execute
checkpoints, commit, push, deploy, or call external APIs.
