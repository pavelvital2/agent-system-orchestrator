# Project profile: browser_automation

## When to use

Use this profile for browser-driven automation, end-to-end testing, scraping with browser rendering, workflow automation, or visual verification tasks.

## Required gates and checks

- Verify target pages, selectors, navigation paths, wait conditions, and failure handling.
- Check authentication, session handling, rate limits, and access permissions without exposing credentials.
- Confirm headless/headed behavior, browser dependencies, viewport coverage, and artifact retention.
- Validate that automation is deterministic enough for the intended gate.
- Confirm screenshots, traces, videos, or logs do not leak sensitive data.

## Typical artifacts

- automation scripts or test specs;
- selector strategy notes;
- fixture or mock data when safe;
- screenshot, trace, or report paths;
- browser setup notes;
- smoke execution evidence.

## Test expectations

- Smoke checks for representative navigation and interaction paths.
- Assertions for visible state, network outcomes, files, or other observable results.
- Retry and timeout behavior only when justified and documented.
- Cross-viewport checks when UI behavior is in scope.
- Artifact review for sensitive data before inclusion in evidence.

## Setup considerations

- Document runtime, browser installation, driver requirements, test command, and required configuration key names.
- Define how authentication is provided without printing or storing credentials.
- Specify local and CI display/headless assumptions when applicable.

## Launch considerations

- Confirm automation passes against the intended target environment.
- Confirm selectors and waits are stable enough for release gating.
- Confirm generated artifacts are retained or discarded according to evidence and privacy requirements.
- Confirm automation does not perform unintended production mutations unless explicitly approved.

## Handover considerations

- Provide test command, target environment notes, configuration key names, selector strategy, artifact locations, and known flake risks.
- Include maintenance guidance for target page changes.
