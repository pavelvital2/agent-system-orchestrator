# Project profile: frontend_app

## When to use

Use this profile for browser-based user interfaces, static sites, single-page applications, or frontend-heavy application surfaces.

## Required gates and checks

- Verify primary user flows, navigation, loading states, empty states, error states, and accessibility expectations.
- Check responsive behavior for supported viewport classes.
- Confirm API, asset, routing, caching, and environment configuration assumptions.
- Validate that visual changes match the project design source-of-truth when one exists.
- Confirm that build output, static assets, and generated files are handled according to repository rules.

## Typical artifacts

- UI flow notes or screen specifications;
- component or page implementation files;
- styles, assets, or design tokens;
- frontend configuration files;
- build output notes when generated artifacts are not committed;
- visual or browser smoke evidence.

## Test expectations

- Unit or component tests for interactive behavior where supported.
- Browser smoke checks for key flows.
- Accessibility checks for semantic structure, keyboard access, and visible focus where applicable.
- Responsive checks for representative desktop and mobile viewports.
- Build and lint checks when tooling exists.

## Setup considerations

- Document package manager, install command, development server command, build command, and required configuration key names.
- Identify API base URL or service dependency configuration without exposing values.
- Note browser support assumptions when relevant.

## Launch considerations

- Confirm production build succeeds.
- Confirm routes, assets, static hosting behavior, and cache invalidation expectations.
- Confirm key user flows pass smoke checks against the intended environment.
- Confirm fallback, error, and loading states do not block launch readiness.

## Handover considerations

- Provide build/run commands, environment key names, route map, browser support notes, and known UI limitations.
- Include where visual evidence or smoke results are stored.
