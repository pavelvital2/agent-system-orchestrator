# SECRET_SCAN_RULES

## Purpose

This document defines checkpoint-time detection rules for secrets and sensitive
artifacts.

The goal is fail-closed protection before staging, commit, or push. Validators
must identify only the path, field, and redacted risk class. They must never
print, copy, summarize, or commit secret values.

## Required status values

```text
SECRET_SCAN_STATUS: not_checked | passed | potential_secret_exposure | blocked
```

`potential_secret_exposure` blocks `git add`, `git commit`, and `git push`.

Audit and checkpoint evidence must also expose the checkpoint-facing alias:

```text
SECRET_EXPOSURE_STATUS: not_checked | passed | potential_secret_exposure | blocked
```

`SECRET_EXPOSURE_STATUS` has the same blocking semantics as
`SECRET_SCAN_STATUS`. `not_checked` is valid only before secret scanning is
required; after audit or checkpoint scope includes changed files, evidence, or
commit text, `not_checked` blocks auditor pass and checkpoint eligibility.

## Forbidden artifact classes

The following path or content classes must be treated as
`potential_secret_exposure` unless a governed secret-handling correction
explicitly proves the file contains placeholders only:

- `.env` files with real values;
- local environment dumps;
- private keys and public/private key bundles;
- SSH keys and SSH agent material;
- API tokens and bearer tokens;
- passwords and password manager exports;
- cookies and browser session cookies;
- HAR files and devtools network dumps;
- session storage, local storage, and browser profile material;
- cloud provider credentials and kubeconfig files;
- package manager auth files such as npm, Python, Ruby, Docker, or Git auth;
- database dumps containing credentials or session tables;
- command output that includes credential headers, cookies, or tokens.

## Forbidden path patterns

Path-only matches are enough to block checkpoint for common sensitive
artifacts:

```text
.env
.env.*
*.pem
*.key
*.p12
*.pfx
*.kdbx
*.har
*cookie*
*session*
*localstorage*
*Local Storage*
*Login Data*
id_rsa
id_dsa
id_ecdsa
id_ed25519
.npmrc
.pypirc
.netrc
.docker/config.json
kubeconfig
credentials
credentials.json
token
tokens.json
```

Validators may implement stricter case-insensitive matching.

## Content risk indicators

Content scans must be redacted. A validator may report only:

```text
potential_secret_exposure at <path> (<risk_class>)
```

Risk classes include:

```text
private_key_material
bearer_token
api_key_assignment
password_assignment
cookie_header
cloud_access_key
oauth_token
session_material
har_or_devtools_dump
credential_store
```

## Allowed placeholder references

Documentation may mention non-secret configuration names, expected purpose, and
clearly fake placeholders, for example:

```text
API_TOKEN=<placeholder>
DATABASE_URL=<set in local environment>
PASSWORD=<redacted>
```

A placeholder is safe only when it is visibly non-secret and cannot be used as a
credential.

## Checkpoint behavior

When secret scan finds `potential_secret_exposure`:

- do not stage additional files;
- do not commit;
- do not push;
- do not print the suspected value;
- write only the affected path, field, and redacted risk class to checkpoint
  evidence;
- route to governed correction or owner handling.
- if the finding appears after auditor `STATUS: pass` for work the auditor was
  required to inspect, record `AUDIT_FALSE_PASS_DETECTED` with
  `FAILURE_TYPE: audit_miss`.

## Scope

Secret scan applies to changed files, staged files, generated checkpoint
receipts, RESULT summaries, audit summaries, runtime event summaries, and commit
messages.
