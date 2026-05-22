# Negative case: missing blocking stage

Expected failures: `DG4_QUESTION_007` and `DG4_GAP_002`.

The gap and linked question omit a concrete blocking stage. Corrected P4 requires
explicit `blocking_stage` and `can_continue_until` values so gates can decide
when unresolved owner input blocks progression.
