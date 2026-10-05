# Optional development workflow

[简体中文](../SKILL.md) · [English](guide.en.md)

`dev-orchestrator` is an optional experimental Skill for organizing development stages. Ordinary Claude questions need only `claude-bridge`. Install and configure the Bridge before trying the orchestrator. The current implementation is distributed under the [MIT License](../LICENSE).

## Workflow

1. **Architect:** Claude plans the authorized change and writes scoped tasks.
2. **Executor:** the host's native GPT implements one task within its scope.
3. **Validator:** the orchestrator runs deterministic project checks and verifies the actual diff.
4. **Reviewer:** Claude reviews without editing business code by default; issues become rework tasks.
5. **Orchestrator:** records task/state transitions and continues or stops according to the rules.

The project `.ai/` directory stores plans, tasks, state, validation, handoffs, and blockers. `PROJECT_CONTEXT.md`, `DECISIONS.md`, `HANDOFF.md`, session metadata, and Bridge logs keep their existing ownership. Do not hand-edit lifecycle state; use `scripts/devflow.py` transitions, which synchronize task status and project state.

## Example requests

```text
$dev-orchestrator Explain this workflow in English. Do not call Claude yet.
Use the development workflow to implement this change in the specified project.
Use Claude Sonnet at medium effort for planning and review; preserve existing uncommitted changes.
Show the development status without calling a model.
Continue the next development stage.
```

Recognized semantic shortcuts include `/dev new`, `/dev continue` (one next stage), `/dev run` (advance within limits), `/dev status` (read only), `/dev plan`, `/dev review`, and `/dev resolve`. They are conventions, not a separate native command parser.

The strong tier uses the existing Bridge and the user's chosen `sonnet`, `opus`, or `default` mode. The efficient tier uses the current native GPT host model. No new model gateway is introduced. Do not silently substitute GPT for a failed strong-model stage or use Bridge `review` when it would change the selected model or authorize fixes beyond a read-only review.

## Dispatch and evidence

Establish the absolute project path and authorization, read applicable rules, inspect Git status, and record existing changes without cleaning them. Initialize missing workflow files only if creating those project files is authorized. Use deterministic `next`, `route`, and `transition` operations to advance state.

For Claude stages, embed the relevant role instructions and task schemas in the task text. Project materials are read progressively from authorized project paths; do not ask Claude to read Skill files outside the project. Keep the assembled task within the Bridge limit without truncating role constraints or acceptance criteria. Run writers serially.

After a Claude stage, provide the actual model, full current session ID, status, and uniquely matched evidence according to `claude-bridge`. Verify claimed changes and tests independently. Read-only status and help operations do not reuse historical successful receipts.

## When to stop

Stop for missing business decisions, conflicting scope, unresolved workspace conflicts, unavailable Bridge/login/allowance/cost confirmation, unavailable validation tools, exhausted configured task/rework/retry limits, or the user's stop request. Evaluate high-risk and irreversible operations under the user's actual authorization. Do not bypass permission or integrity checks to continue.

The normative role, task-schema, state-machine, routing, review, and escalation instructions are bundled locally and currently primarily written in Chinese. Codex should explain them in the user's requested language without changing their constraints. This introduction does not establish cross-platform runtime support or independent-user acceptance.
