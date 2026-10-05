# Models, effort, and call receipts

[简体中文](../03-models-effort-receipt.md) · [English](03-models-effort-receipt.md)

You can request "Claude Sonnet at medium effort" or "Claude Opus at high effort." Before a call, Codex briefly states the requested model and effort. Afterward it provides a verifiable receipt for the actual call.

## Model modes

| `--mode` | Request | Caveat |
| --- | --- | --- |
| `sonnet` | Explicitly request Sonnet | Availability depends on the account and CLI response |
| `opus` | Explicitly request Opus | Not guaranteed for every account or request |
| `default` | Omit an explicit `--model` | A resumed session may retain its previous model rather than return to the account default |
| `review` | A Sonnet review-task mode | A task mode, not a separate model; retain `opus` when that is the user's fixed choice and state the review instructions in the task |

`@claude`, `@claude-sonnet`, and `@claude-opus` are semantic conventions. They are not a native Codex model menu, dedicated parser, or new provider. The explicit Skill name is `$claude-bridge`.

## Selecting effort

An explicit user choice takes priority and uses `--effort-source user`. Otherwise, Codex selects `medium` or `high` according to the actual task, with source `auto`. Automatic selection does not use `xhigh` or `max`.

Routine, clearly scoped work usually fits medium; cross-module diagnosis and high-impact judgments often need high. This is a task judgment, not keyword matching. If the model or CLI does not support the requested value, report the limit and clarify rather than silently substitute.

The Skill explicitly supplies `--effort`, `--effort-source`, and `--effort-reason` every time. The reason is a single line of at most 160 characters, not the task body or hidden reasoning. Logged requested effort is the request; effective effort remains `unknown`. Caps may limit it. Claude effort does not change Codex's native effort setting.

## Confirming a real Claude call

Every actual call's response includes:

```text
Claude receipt: actual model <current actual_models> | session <current full session_id> | status <current status> | evidence <matching evidence link>
```

Angle brackets are placeholders, not proof of an actual call.

- **Actual model:** current Bridge `actual_models`, derived from the official CLI's `modelUsage`. Do not substitute the requested mode, model self-identification, or historical output. Report missing model evidence explicitly.
- **Session:** the full `session_id` returned in this call. If missing, say it was not returned. Do not substitute the old ID requested for resumption.
- **Status:** assess the current `status`, `reason`, and official result. `inference: true` alone does not prove processing. Failed, denied, or timed-out calls are not completed tasks.
- **Evidence:** uniquely match this call's time, session, and runtime metadata. Do not select a log merely because it is newest or reuse another successful call. Report ambiguous matching.

Project `.ai/logs/*.json` files contain necessary Bridge runtime metadata. Codex may link the matching log or save a minimal metadata excerpt under the task's output rules. Excerpts omit the task body, complete response, and secrets, and identify the current result source and original log path. Do not rewrite Bridge-owned logs. Public tutorials include no personal project logs or actual account session IDs.

Report inference and saving separately when local state writing fails. For `state_update_failed`, preserve `inference_status` and `session_saved`: the model may have completed while saving was incomplete. Do not invent a successful log when none was saved.

## Multiple calls and non-call actions

List a receipt for each planning, review, or other Claude call, optionally in a compact table. Distinguish GPT execution from Claude processing. `init`, `doctor`, `--dry-run`, and preflight-blocked operations must say "Claude was not actually called." Fake-CLI checks are offline validation; ordinary GPT help needs no Claude receipt.

Reuse the current result and matching log. Inspect official local session metadata only when the user requests deeper verification, evidence is missing, or records conflict. Do not make another Claude call or read complete session text merely to add a receipt.
