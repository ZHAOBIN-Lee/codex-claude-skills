# Changelog

[简体中文](CHANGELOG.md) · [English](CHANGELOG.en.md)

## Unreleased — local permission and timeout repair

This is a local repair on top of public commit 567dd9d. It is not a new GitHub release and has no new version number.

- Add `--output PATH`: the host declares each output file, and the Bridge runs a static exact-Edit-rule preflight before inference and stops the call if the grant is missing. Existence, byte count, and a hash are recorded before and after.
- Add `--stream-events`: optional on the standard workflow. An official `permission_denied` event ends the batch immediately; only event counts are kept, never event text.
- Read stdout/stderr with bounds, and terminate the whole process group on timeout, so a descendant holding a pipe can no longer hang a call.
- Add `permission_denials_status` (listed/none_reported/unavailable); evidence that wasn't obtained is no longer treated as "no denials". When the final result carries a valid session ID it is reported even on failure, but only `complete` saves it.
- Truncated structured results set `result_complete` to false; `--max-turns` is limited to 1..20 and `--timeout` must be a finite number of seconds, 0 < seconds <= 3600 (zero is invalid).
- Add the [permissions and failures](skills/claude-bridge/references/en/08-permissions-and-failures.md) tutorial, and fix the conflict in `dev-orchestrator` that said every failure must ask the user.
- Verification: offline tests, plus a small real-subscription test on macOS with the official CLI 2.1.285. Linux and Windows haven't been validated.

## 0.1.0-draft — 2026-10-05

- Package Claude-related resources as a self-contained public-preview Skill.
- Include local help routing, continued-conversation conventions, preference examples, and actual-model receipts.
- Exclude personal runtime configuration, installation manifests, official binaries, sessions, logs, and backups.
- Keep `dev-orchestrator` optional and experimental.
- Record the maintainer's provenance confirmation and document platform adaptation work.
- Add Chinese and English README pages, user tutorials, and maintenance documentation.
- Apply the maintainer-selected MIT License with attribution to ZHAOBIN-Lee, including copies in the installable Skill directories.
- Rewrite the Chinese and English README, tutorials, and maintenance docs so the front page covers purpose, install, and a first request, with the details moved into the tutorials.

Public repository: ZHAOBIN-Lee/codex-claude-skills. No stable release or version tag has been published. Fresh-machine installation and real cross-platform validation remain pending.
