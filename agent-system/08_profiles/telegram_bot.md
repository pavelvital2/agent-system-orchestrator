# Project profile: telegram_bot

## When to use

Use this profile for chat bots that interact with users through Telegram bot APIs or compatible bot-hosting patterns.

## Required gates and checks

- Verify command list, conversation flows, callback handling, message formatting, and user-facing error behavior.
- Check authentication, authorization, rate limiting, abuse handling, and private data handling where applicable.
- Confirm update delivery mode, webhook or polling behavior, and retry expectations.
- Validate storage, state management, and background job behavior when in scope.
- Confirm bot token and chat identifiers are treated as secrets or sensitive configuration as appropriate.

## Typical artifacts

- bot command and flow specification;
- handler implementation files;
- message templates or formatting rules;
- state storage or persistence notes;
- runtime configuration notes;
- chat interaction smoke evidence with non-sensitive data.

## Test expectations

- Unit tests for handlers, formatting, validation, and state transitions.
- Integration tests with mocked bot API interactions where possible.
- Smoke checks for startup and representative commands in a safe environment.
- Negative tests for invalid commands, unauthorized access, and API failures where applicable.

## Setup considerations

- Document runtime, dependency installation, update delivery mode, local run command, and required configuration key names.
- Keep bot tokens, webhook secrets, chat identifiers, and user data out of logs and artifacts unless explicitly safe and non-sensitive.
- Note webhook URL, certificate, or network requirements by configuration key name only.

## Launch considerations

- Confirm webhook or polling mode is intentionally selected and tested.
- Confirm representative commands, error handling, and restart behavior pass smoke checks.
- Confirm monitoring, logging, rate limits, and rollback behavior are addressed when in scope.

## Handover considerations

- Provide command list, flow map, run commands, configuration key names, update delivery notes, smoke procedure, and operational limitations.
- Include safe guidance for rotating bot credentials without exposing values.
