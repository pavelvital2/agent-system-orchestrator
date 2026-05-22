# Negative case: unanswered blocking gap crossing stage

Expected failure: `DG4_GATE_002` when verifying the `IMPLEMENTATION` gate.

The gap is deferred until implementation, requires owner input, and has no owner
answer or accepted assumption. Design may continue, but crossing into
implementation must be blocked.
