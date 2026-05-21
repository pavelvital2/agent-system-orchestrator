# PRODUCT_INTAKE_P4_CONTRACT

## Purpose

Product Intake P4 defines a governed planning/intake layer for ASO package
version `3.6.0`, governance ruleset version `3.6.0`, Runtime Schema version
`3.1.0`, and product artifact schema version `1.0.0`.

P4 does not redefine Runtime Schema `3.1.0` sidecars, P3 proposal/apply
artifacts, or Project Factory lockfiles. It defines local product planning
artifacts only.

## Product Artifact Authority Boundary

Product artifacts are planning records. They may summarize owner input,
open questions, product decisions, requirements, stories, acceptance criteria,
capability analysis, and plans. They are not implementation evidence,
deployment evidence, checkpoint evidence, audit evidence, or final acceptance.

P4 product artifacts may inform later task packets and owner decisions only
after the governed orchestration flow accepts them. They do not authorize live
agent dispatch, source code generation, product build execution, deployment,
external API calls, secret collection, commit, push, tag, or checkpoint
execution.

Owner-provided source material remains owner input. Product artifacts must not
overwrite or delete owner input, runtime state sidecars, release evidence, or
package governance files.

## Allowed Runtime Product Artifact Roots

Confirmed product artifact writes are workspace-local and unpublished. They
must stay under ignored runtime roots:

```text
project-runtime/product/
project-runtime/reports/
project-runtime/rendered/   # only when existing render conventions allow it
```

Dry-run commands must not write workspace artifacts. Explicit output paths such
as `--json-out` may be written only when the caller requested that path and the
path is allowed by the command contract.

Package repository files are not writable by product-intake workspace commands.
Active product artifacts under `project-runtime/` must not be published from
the package repository or generated-project publication flows.

## Product Artifact Types

P4 may define and generate local planning artifacts such as:

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

P4 artifact statuses may include:

```text
proposed
needs_clarification
blocked
ready_for_review
accepted_by_owner
out_of_scope
```

P4 artifacts must not claim product completion statuses such as:

```text
implemented
mvp_ready
product_pass
final_acceptance
checkpoint_done
```

## Secret Handling

P4 may identify required secret names, but it must not collect, infer, store,
or render real secret values. Secret values in owner input or generated
artifacts must be redacted. Required secrets should be represented only as
names and collection status, for example:

```json
{ "required_secrets": [{ "name": "TELEGRAM_BOT_TOKEN", "value_status": "not_collected" }] }
```

## Non-Goals

P4 explicitly does not implement or authorize:

```text
live agent dispatch
runtime daemon
checkpoint executor
git commit/push automation
web dashboard or GUI
external API calls
product build execution
deployment execution
secret collection UI
payment, marketplace, Telegram, or other live integration execution
distributed workers
multi-project registry
application source code generation
```

## Compatibility

Runtime Schema `3.1.0` remains the canonical sidecar schema. P4 may add product
planning schemas, templates, fixtures, docs, tests, and CLI surfaces in later
bounded tasks, but those artifacts must not redefine P2/P3 runtime-state,
proposal, receipt, or checkpoint authority.

Existing P0/P1/P2/P3 behavior remains governed by its accepted compatibility
rules. P4 adds planning contract authority only; it does not silently migrate
workspaces or broaden publication authority.
