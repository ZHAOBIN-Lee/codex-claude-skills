# Models, effort, and call receipts

[简体中文](../03-models-effort-receipt.md) · [English](03-models-effort-receipt.md)

Just say it: "use Claude Sonnet at medium effort for this step," or "use Claude Opus at high effort to assess this." Before the call, Codex briefly states the model and effort it requested. After the call, it adds a receipt you can check.

The default preference is Sonnet at medium. That's a preference the Skill follows, not a new parameter the Bridge parses, and it doesn't touch the desktop app's model menu. If you ask for something else, you get that.

## Model modes

| `--mode` | What it does | Watch out for |
| --- | --- | --- |
| `sonnet` | Explicitly requests Sonnet | Whether your account and CLI allow it shows up in the actual response |
| `opus` | Explicitly requests Opus | Not guaranteed for every plan or every request |
| `default` | Doesn't pass `--model` | A resumed session may keep that session's earlier model rather than going back to your account default |
| `review` | A review task run on Sonnet | A task mode, not a separate model. If you've already fixed on Opus, use `opus` and put the review instructions in the task |

`@claude`, `@claude-sonnet`, and `@claude-opus` are plain-language shorthands the Skill understands. They aren't in Codex's native model menu, and there's no dedicated command parser behind them. To invoke the Skill explicitly, use `$claude-bridge`.

## How effort is chosen

If you state an effort, it's used and recorded as `--effort-source user`. If you don't, Codex picks `medium` or `high` based on how hard the task actually is and records it as `auto`. Automatic choices never use `xhigh` or `max`.

Routine cleanup and well-bounded local tasks usually get medium. Cross-module problems and high-impact judgment calls usually get high. It's a judgment about the task, not a keyword match. If the value you asked for isn't supported by the current model or CLI, Codex tells you and checks with you instead of quietly substituting another.

On every call the Skill passes `--effort`, `--effort-source`, and `--effort-reason` explicitly. The reason is a single line of at most 160 characters, with no task text and no hidden reasoning. The requested effort in the log is the value you asked for. The effective effort is always recorded as `unknown`, because existing caps can lower a request and you can't infer Claude's real internal effort from the parameter. Claude's effort setting also doesn't change Codex's own.

## Confirming Claude was really called

After every real call, Codex's answer should include a line like this:

```text
Claude receipt: actual model <this call's actual_models> | session <this call's full session_id> | status <this call's status> | evidence <this call's evidence link>
```

The angle brackets are field placeholders. This example is not evidence of any call.

- **Actual model** comes from the `actual_models` the Bridge returned for this call, which is derived from the official CLI's `modelUsage`. The requested mode, the model's description of itself, and older records can't stand in for it. If it wasn't returned, the receipt says no actual-model evidence was obtained.
- **Session ID** is the full `session_id` this call returned. If none came back, the receipt says "not returned." The old ID you asked to resume can't be substituted.
- **Status** comes from this call's `status`, `reason`, and the official result together. `inference: true` alone doesn't show the task was handled. A failure, a denial, or a timeout isn't reported as done.
- **Evidence** has to match this call's time, session, and run metadata uniquely. Don't just grab the newest log or borrow a record from another successful call. If the match isn't unique, say so.

The `.ai/logs/*.json` files in a project are runtime metadata the Bridge needs. Codex can link the log that matches this call, or save a short metadata excerpt under the task's output rules, with no task text, full response, or secrets. The excerpt says it came from this call's result and names the original log's location. Leave Bridge-owned logs alone. The public tutorials contain no personal project logs and no real account session IDs.

When local saving goes wrong, report the inference result and the saving result separately. For `state_update_failed`, give both `inference_status` and `session_saved`: the model may have answered, with only some of the local state written. If no log was saved, don't make one up.

## Multiple calls, and no calls

When one round includes several Claude calls, such as planning and review, each gets a receipt. They can be combined into one table, with the GPT execution parts kept separate. For `init`, `doctor`, `--dry-run`, or anything blocked before the call, say plainly that Claude wasn't called. Fake-CLI checks are labeled offline validation. Ordinary GPT help needs no Claude receipt.

For everyday receipts, this call's result and its log are enough. Look at the official local session metadata only if you ask for deeper verification, information is missing, or the records contradict each other. Don't call Claude again or read the full session text just to fill in a receipt.
