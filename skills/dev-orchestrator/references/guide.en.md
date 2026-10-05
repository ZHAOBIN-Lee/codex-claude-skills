# Optional development workflow

[简体中文](../SKILL.md) · [English](guide.en.md)

`dev-orchestrator` is an experimental Skill that splits a development task into stages: Claude plans and reviews, native GPT does the editing, and scripts check the result. Ordinary Claude questions only need `claude-bridge`. Set up the Bridge first, then try this. It's under the [MIT License](../LICENSE).

It's a workflow for you to try on a task you're willing to supervise. It isn't a promise that it handles every kind of development work on its own.

## How a task moves

1. **Architect:** Claude plans the change you authorized and writes small, scoped tasks.
2. **Executor:** the host's native GPT implements one task, inside that task's scope.
3. **Validator:** the orchestrator runs the project's deterministic checks and verifies the actual diff.
4. **Reviewer:** Claude reviews and, by default, doesn't edit business code. Problems it finds become rework tasks.
5. **Orchestrator:** records each task and state change, then continues or stops according to the rules.

Plans, tasks, state, validation results, handoffs, and blockers live in the project's `.ai/` directory. `PROJECT_CONTEXT.md`, `DECISIONS.md`, `HANDOFF.md`, session metadata, and Bridge logs keep the owners they already have. Don't edit lifecycle state by hand. Use the `scripts/devflow.py` transitions, which keep task status and project state in sync.

## Asking for it

```text
$dev-orchestrator Explain this workflow in English. Do not call Claude yet.
Use the development workflow to implement this change in the specified project.
Use Claude Sonnet at medium effort for planning and review; preserve existing uncommitted changes.
Show the development status without calling a model.
Continue the next development stage.
```

The Skill also understands these shortcuts: `/dev new`, `/dev continue` (one next stage), `/dev run` (advance within the limits), `/dev status` (read only), `/dev plan`, `/dev review`, and `/dev resolve`. They're a way of phrasing the request, and no separate command parser sits behind them.

The strong tier goes through the existing Bridge, in the `sonnet`, `opus`, or `default` mode you choose. The efficient tier uses whatever native GPT model the current chat is on. No new model gateway is added. If a strong-model stage fails, GPT doesn't quietly fill in for it. Bridge `review` mode isn't used for the Reviewer either, because it could change the model you picked or authorize fixes beyond a read-only review.

## Dispatch and evidence

Before dispatching anything, the orchestrator pins down the project's absolute path and your authorization, reads the applicable rules, checks Git status, and notes existing changes without cleaning them up. It initializes missing workflow files only if you authorized creating those project files. It advances state with the deterministic `next`, `route`, and `transition` operations.

For a Claude stage, the role instructions and task schemas are embedded in the task text, and project material is read step by step from authorized project paths. Claude isn't asked to read Skill files outside the project. The assembled task has to fit within the Bridge's size limit without trimming role constraints or acceptance criteria. Anything that writes runs one at a time.

After a Claude stage, the answer includes the actual model, the full session ID of that call, the status, and the matching evidence, following `claude-bridge`'s rules. Claimed changes and tests are verified independently. Read-only status and help requests don't reuse an earlier successful receipt.

## When it stops

It stops when:

- a business decision is missing, or the scope conflicts with the repo;
- the workspace has conflicts it can't resolve;
- the Bridge, login, allowance, or cost confirmation isn't available;
- the validation tools can't run;
- the configured limits on tasks, rework, or retries are used up;
- you tell it to stop.

High-risk or irreversible operations are judged against what you actually authorized. It never bypasses a permission or integrity check just to keep going.

The binding role definitions, task schema, state machine, routing, review, and escalation rules ship locally, mostly written in Chinese for now. Codex should explain them in the language you ask for, without changing what they require. This introduction doesn't establish cross-platform support or acceptance by independent users.
