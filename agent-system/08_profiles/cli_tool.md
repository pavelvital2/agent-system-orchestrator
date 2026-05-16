# Project profile: cli_tool

## When to use

Use this profile for command-line tools, local automation commands, developer utilities, or scripts intended to be invoked from a shell.

## Required gates and checks

- Verify command names, flags, arguments, exit codes, stdin/stdout/stderr behavior, and help output expectations.
- Check error handling for invalid input, missing files, missing configuration, and unavailable dependencies.
- Confirm portability assumptions for supported operating systems and shells.
- Validate that file reads and writes are scoped, documented, and safe.
- Confirm commands do not print secrets or sensitive local values.

## Typical artifacts

- CLI entrypoint or script files;
- command reference or help text;
- configuration notes;
- sample input and output fixtures when safe;
- packaging or installation metadata;
- smoke command evidence.

## Test expectations

- Unit tests for parsing and core command behavior.
- Command invocation tests for success and failure paths where tooling supports them.
- Fixture-based tests for file input/output behavior.
- Smoke checks for help output and representative commands.
- Static checks or linting when available.

## Setup considerations

- Document runtime version, installation command, executable path, and required configuration key names.
- Specify expected working directory assumptions.
- Avoid requiring global machine changes unless explicitly accepted by the task.

## Launch considerations

- Confirm packaging, executable permissions, and invocation path are correct.
- Confirm help output, version output, and representative commands work.
- Confirm error messages are actionable and do not expose sensitive values.

## Handover considerations

- Provide installation steps, command reference, examples with non-sensitive values, configuration key names, and known limitations.
- Include smoke command outputs or paths to evidence.
