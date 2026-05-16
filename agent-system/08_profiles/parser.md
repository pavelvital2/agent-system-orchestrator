# Project profile: parser

## When to use

Use this profile for projects that extract, normalize, transform, or validate structured information from source documents, text, files, pages, feeds, or messages.

## Required gates and checks

- Verify source format assumptions, encoding, schema, versioning, and malformed input handling.
- Confirm extraction, normalization, deduplication, and validation rules are explicit.
- Check behavior for partial data, missing fields, duplicate records, and unsupported formats.
- Verify output schema, ordering, determinism, and error reporting expectations.
- Confirm legal, access, and rate-limit constraints are documented when external sources are in scope.

## Typical artifacts

- parser rules or grammar notes;
- source and output schema documentation;
- sample fixtures with non-sensitive data;
- transformation or normalization code;
- error handling and rejection rules;
- validation reports or fixture comparison evidence.

## Test expectations

- Fixture-based tests for representative valid, invalid, edge-case, and malformed inputs.
- Snapshot or golden-output tests where stable output is required.
- Unit tests for normalization and validation rules.
- Regression tests for previously discovered parsing failures when applicable.
- Performance checks when input size or throughput is in scope.

## Setup considerations

- Document required libraries, source access method, input location assumptions, and output location assumptions.
- Keep sample fixtures free of secrets and private data unless explicitly approved and safely handled.
- Define retry, timeout, and rate-limit configuration key names where applicable.

## Launch considerations

- Confirm fixtures pass and output schema is stable.
- Confirm failure handling does not silently corrupt output.
- Confirm source access, rate-limit behavior, and monitoring expectations are addressed when runtime execution is in scope.

## Handover considerations

- Provide source format notes, output schema, fixture paths, validation commands, configuration key names, and known unsupported cases.
- Include guidance for adding new fixtures for future source changes.
