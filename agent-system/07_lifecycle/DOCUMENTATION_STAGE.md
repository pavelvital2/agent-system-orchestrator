# DOCUMENTATION_STAGE

## Purpose

Documentation verifies that accepted project behavior, setup, operation, limitations, and handover notes are recorded before handover and final acceptance.

## Main role

`agent-system/01_roles/TECHNICAL_WRITER.md`

## Inputs

- documentation task packet;
- accepted requirements, design, implementation, audit, testing, setup, run, and launch evidence required by the task packet;
- verified behavior and command evidence;
- owner decisions relevant to documentation;
- existing owner-facing, technical, operational, or handover documentation.

## Required work

- update owner-facing documentation required by the task packet;
- update technical documentation required by the task packet;
- document verified setup, run, launch, operation, or acceptance instructions;
- document known limitations, open risks, deferred work, and accepted exceptions or explicitly mark them `NONE`;
- document handover notes needed for future operation, maintenance, or acceptance;
- ensure documentation describes verified behavior only;
- verify documentation artifacts are complete enough for handover or final acceptance routing.

## Required documentation checks

Documentation cannot pass until the RESULT records evidence for each applicable check:

- required documentation artifacts exist and are listed with paths;
- setup, run, launch, operation, or acceptance instructions match accepted evidence;
- owner-facing and technical documentation are separated when the task packet requires separate audiences;
- known limitations, open risks, deferred work, and accepted exceptions are documented or explicitly marked `NONE`;
- handover notes identify artifact references, operational notes, maintenance notes, and ownership boundaries when applicable;
- documentation avoids unverified behavior, future functionality, and project-specific assumptions outside accepted source material;
- documentation is accepted before handover or final acceptance routing.

## Outputs

- documentation RESULT;
- changed documentation file list;
- documentation index or artifact list;
- verified instruction references;
- limitations, risks, and handover notes;
- readiness recommendation for handover or orchestrator-controlled final acceptance.

## Exit criteria

Documentation exits with `STATUS: pass` only when required documentation artifacts are present, aligned with accepted evidence, free of unverified behavior, and ready for handover or final acceptance routing.
