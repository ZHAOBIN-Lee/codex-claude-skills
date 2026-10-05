# Failures and waiting time

[简体中文](../05-troubleshooting.md) · [English](05-troubleshooting.md)

When something fails, you can ask:

```text
$claude-bridge Explain this failure. Inspect the current status and necessary metadata first. Do not automatically retry or read account secrets.
```

Start from this call's result and pull out only the fields you need. In a public issue, don't paste complete authentication config, task text, session content, or environment-variable values.

## Common cases

| Symptom | What to check | What to do |
| --- | --- | --- |
| Codex can't find the Skill | That the directory and files are complete, the Skill format validates, and the current discovery state | See the install part of [first-time setup](01-setup.md). A new machine's routing only counts once you've actually tried it |
| CLI path or hash mismatch | Whether the official file your runtime points to still exists, or was upgraded | Verify the official install and version, then update your own pin. Don't bypass the check |
| `subscription_usage_credits_status_unconfirmed` | Whether you've confirmed your own account's extra usage credits | Check your cost settings and record what you find. The author's confirmation doesn't carry over |
| `consult_usage_credits_user_confirmation_required` | Whether the confirmation's source and date are valid | Add your own real confirmation. Don't invent a date or source |
| Non-subscription or provider route blocked | Authentication status, and the variable or field names returned | Sort out the official login yourself. Don't print values or switch to an API |
| Effort environment override blocked | Whether `CLAUDE_CODE_EFFORT_LEVEL` is set to something non-empty | Codex names the variable and the conflict; how to change your settings is your call. It won't delete or bypass anything |
| Model unavailable or allowance used up | This call's CLI result and your account's actual availability | Report it and go back to the GPT work you authorized. Don't buy extra credits or switch models on your own |
| Permission denied (`needs_permission`) | `permission_denials_status`, and whether the exact operation was already authorized | Look at the real files first. If existing authorization covers that exact operation, add the exact rule and make a new call. Don't widen wildcard rules. See [permissions and failures](08-permissions-and-failures.md) |
| `declared_output_edit_permission_unconfirmed` | Each `--output`'s verdict: `missing_rule`, `deny_or_ask_may_apply`, or `unknown` | No inference happened. An applicable deny/ask is a protection: respect it, don't remove or bypass it. For an authorized, non-conflicting scope you can look into the settings and add the exact `Edit(/path)` (neither `Write(path)` nor a bare `Edit` counts as an exact grant). Changing a protective policy for real takes the appropriate existing authority from the user. See [permissions and failures](08-permissions-and-failures.md) |
| `max_turns_out_of_bounds`, `timeout_out_of_bounds` | The returned `allowed_range` (max-turns 1..20, timeout greater than 0 and at most 3600) | Use a value in range. No call was made |
| `claude_stream_malformed_frame`, `claude_stream_final_result_unavailable` | A line in the stream couldn't be parsed, or there was no final result | Treat it as unfinished and look at the real files. With no final result there's no model or session evidence |
| Project busy or locked | Whether another call in that project is still running | Wait, or check the actual process. Don't just delete the lock or edit in parallel |
| `state_update_failed` | Whether inference finished, whether the session was saved, which local writes failed | Report the result and the saving status separately, and keep the evidence. Don't assume incremental continuation will still work |
| Timeout | Whether only the wait ended or the work really didn't finish | Mark completion as unknown and look at the real files and the necessary metadata first. Don't silently resend, or the task may run twice. If it really needs doing again, state the scope and make a new call |

Run the Bridge's `doctor` for a first diagnosis, after the program changes, or when a check fails. In normal continued consultation, `run` already includes the preflight, so you don't need to run it before every question. The Bridge's `doctor` and the official CLI's `claude doctor` are different tools.

## Claude seems to have lost the background

Look at this call's `session_id`, `resumed_session`, `context_delivery`, and the change and truncation metadata. A new session, a mode change, or an invalid baseline makes the Bridge send the full context again. The existence of `.ai/consult.json` alone doesn't show the session was resumed.

A consultation carries only the defined summaries, rules, and Git snapshot. New documents, untracked files, and truncated parts need to be supplied by you. Anything listed in `truncated_context_names` or `unavailable_context_names` should be reported to you as is. Fingerprints detect changes. They don't prove Claude read everything. If the applicable rules exceed the allowed total, the call should be blocked rather than silently truncated.

## Why it can still feel slow

Waiting has three parts: Codex preparing the call, the Bridge and Claude running, and Codex processing the result. The Bridge's preflight time and `cli_wall_ms` cover only the script's part. They can't tell you how long the whole chat took.

Continued consultation cuts repeated steps with a fixed project session, incremental material, a single `run`, and checking on demand. Long chats, Codex's own effort setting, response length, and the network still affect the wait. Claude's effort parameter doesn't change Codex's.

Durations reported by the official result may be cumulative over the whole session. Don't subtract `duration_api_ms` from this round's wall time to estimate startup overhead. For how long this round's CLI run took, use the Bridge's monotonic-clock fields. For how long you actually waited, use the timestamps of the chat events. `--progress` prints stage metadata only; it isn't a streaming first-token measurement.

The maintainer validated the current receipt rules with real Sonnet calls on macOS. In one long planning consultation, CLI wall time was about 176.5 seconds and the script's preflight about 350 milliseconds. That's one call's observation, not a speed promise, and it says nothing about other machines' install routes.

## What to include in an issue

Please include: the operating system, Python version, Bridge version or commit, official CLI version, mode, redacted status/reason, the necessary timing fields, and steps to reproduce. Absolute paths, full session IDs, and project metadata in logs can be private, so review them before posting. Don't upload the runtime file, authentication files, API keys, tokens, cookies, complete sessions, or business material.
