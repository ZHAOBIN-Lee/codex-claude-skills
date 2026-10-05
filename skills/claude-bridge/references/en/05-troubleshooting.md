# Failures and waiting time

[简体中文](../05-troubleshooting.md) · [English](05-troubleshooting.md)

Ask:

```text
$claude-bridge Explain this failure. Inspect the current status and necessary metadata first. Do not automatically retry or read account secrets.
```

Start with the current result and only the fields needed. Do not paste complete authentication configuration, tasks, session text, or environment-variable values into a public issue.

## Common cases

| Symptom | Check | Response |
| --- | --- | --- |
| Skill not discovered | Directory, complete resources, format, current discovery state | Follow the local host's setup guidance; new-install routing needs a real check |
| CLI path or hash mismatch | Whether the pinned official file exists or was upgraded | Verify official origin and version, then update your own pin; do not bypass checks |
| `subscription_usage_credits_status_unconfirmed` | Your confirmation of extra usage credits | Check your account settings and record the actual confirmation; do not inherit the author's |
| `consult_usage_credits_user_confirmation_required` | Confirmation source and date | Supply your real confirmation; do not fabricate metadata |
| Authentication or provider blocked | Safe authentication status and returned variable/field names | Resolve official login yourself; do not print values or switch to an API |
| Effort environment override blocked | Nonempty `CLAUDE_CODE_EFFORT_LEVEL` | Explain the variable-name conflict; the user decides their settings, without automatic deletion or bypass |
| Model unavailable or allowance exhausted | Current CLI result and account availability | Report the result and return to authorized GPT work; do not buy credits or silently change models |
| Permission denied | Exact operation and existing authorization | Retry through normal permissions only when the operation is authorized; do not broaden rules |
| Project busy or locked | Another call or actual process in that project | Wait or inspect it; do not blindly delete a lock or edit concurrently |
| `state_update_failed` | Inference result, session saving, failed writes | Report inference and saving separately and retain evidence; do not assume incremental continuation is safe |
| Timeout | Whether completion is known | Mark unknown completion and inspect necessary metadata; do not send a duplicate task automatically |

Bridge `doctor` is useful for initial diagnosis, program changes, or failed checks. Normal consultation `run` already includes preflight, so do not run it before every follow-up. Bridge `doctor` and the official CLI's `claude doctor` are different tools.

## Missing background

Inspect the current `session_id`, `resumed_session`, `context_delivery`, changes, and truncation metadata. A new session, mode change, or invalid baseline may cause full delivery. The existence of `.ai/consult.json` alone does not prove resumption.

Consultation includes only prescribed summaries, rules, and Git snapshots. Explicitly supply new documents, untracked-file contents, and relevant omitted material. Report `truncated_context_names` and `unavailable_context_names`. Fingerprints detect changes, not complete reading. Applicable rules exceeding the allowed budget must block rather than be silently truncated.

## Why it may still be slow

Waiting has three parts: Codex preparing the call, Bridge/Claude execution, and Codex processing the result. Bridge preflight and `cli_wall_ms` measure only the script portion, not the entire chat.

Continued consultation reduces repeated preparation through a fixed project session, incremental material, one `run`, and focused verification. Long chats, Codex's native effort, response length, and networking still matter. Claude's effort parameter does not change Codex's effort.

Official duration fields may be session-cumulative. Do not subtract `duration_api_ms` from current wall time to infer startup overhead. Use the Bridge's monotonic-clock fields for that CLI execution and chat events for end-to-end waiting. `--progress` reports stage metadata, not streaming first-token timing.

Existing real-call evidence includes a long Sonnet planning consultation with about 176.5 seconds of CLI wall time and about 350 milliseconds of script preflight. Those are observations from one call, not a speed guarantee or validation of every new-machine setup.

## Reporting an issue

Provide OS, Python version, Bridge version or commit, official CLI version, mode, redacted status/reason, necessary timing fields, and reproduction steps. Absolute paths, full session IDs, and project metadata can be private; review before posting. Do not upload runtime or authentication files, keys, tokens, cookies, complete sessions, or business material.
