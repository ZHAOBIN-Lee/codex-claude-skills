# Development workflow

[简体中文](../SKILL.md) · [English](guide.en.md)

`dev-orchestrator` is an experimental Skill that splits a development task into stages: Claude plans and reviews, GPT (or Claude) writes the code, and scripts check the result. It runs entirely on Codex's native models and sub-agents, so it needs Claude and GPT in the same Codex model picker. Set that up first with [codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin). It's under the [MIT License](../LICENSE).

It's a workflow for you to try on a task you're willing to supervise. It isn't a promise that it handles every kind of development work on its own.

## How a task moves

1. **Architect:** Claude plans the change you authorized and writes small, scoped tasks.
2. **Executor:** one task is implemented inside that task's scope, by GPT or Claude depending on the mode below.
3. **Validator:** the orchestrator runs the project's deterministic checks itself and verifies the actual diff.
4. **Reviewer:** Claude reviews and, by default, doesn't edit business code. Problems it finds become rework tasks.
5. **Orchestrator:** records each task and state change, then continues or stops according to the rules.

Plans, tasks, state, validation results, handoffs, and blockers live in the project's `.ai/` directory. `devflow.py init` creates any missing files, including `PROJECT_CONTEXT.md`, `DECISIONS.md` and `HANDOFF.md`, and never overwrites existing ones. Don't edit lifecycle state by hand. Use the `scripts/devflow.py` transitions, which keep task status and project state in sync.

## Choosing how it runs

The strong model is the Claude model the current chat already uses; you aren't asked again. You're asked only for the execution mode, once per run:

| Mode | Plan | Code | Review |
| --- | --- | --- | --- |
| `claude_dispatch_gpt` (Claude dispatches GPT sub-agents) | the Claude chat | GPT sub-agents | the Claude chat itself, which writes rework tasks and dispatches GPT again |
| `switch_to_gpt` (switch to GPT) | the Claude chat | you switch the chat to GPT, which codes | GPT spawns a read-only Claude sub-agent |
| `claude_only` (Claude does everything) | Claude | Claude | a fresh-context Claude sub-agent, reported as same-model-family review |

Planning happens only in a Claude chat. If the current chat's model doesn't match what the next step needs (for example the plan is done and it's time to switch to GPT), the workflow stops and asks you to switch. A high-risk or sensitive task can be upgraded so Claude writes its code; its review then also runs in a fresh Claude context.

## Asking for it

```text
$dev-orchestrator Explain this workflow in English. Do not start yet.
Use the development workflow to implement this change in the specified project.
Show the development status without calling a model.
Continue the next development stage.
```

The Skill also understands these shortcuts: `/dev new`, `/dev continue` (one next stage), `/dev run` (advance within the limits), `/dev status` (read only), `/dev plan`, `/dev review`, and `/dev resolve`. They're a way of phrasing the request, and no separate command parser sits behind them.

## Dispatch and evidence

Before dispatching anything, the orchestrator pins down the project's absolute path and your authorization, reads the applicable rules, checks Git status, and notes existing changes without cleaning them up. It advances state with the deterministic `next`, `route`, and `transition` operations; `route` also says where each step runs.

A sub-agent starts without the chat history, so its task text is self-contained: the role instructions and task schemas are embedded, and project material is read step by step from listed project paths. Sub-agents run one at a time, and only one executor changes the project at once.

The report lists the execution mode and, for each sub-agent, the actual model and session taken from its session or receipt ("not captured" if unavailable). Claimed changes and tests are verified independently.

## When it stops

It stops when:

- a business decision is missing, or the scope conflicts with the repo;
- the workspace has conflicts it can't resolve;
- the Claude or GPT route, sub-agents, login, or allowance isn't available;
- the current chat's model doesn't match the next step;
- the validation tools can't run;
- the configured limits on tasks, rework, or retries are used up;
- you tell it to stop.

High-risk or irreversible operations are judged against what you actually authorized. It never bypasses a permission or integrity check just to keep going, and never quietly substitutes GPT for a Claude stage.

The binding role definitions, task schema, state machine, routing, review, and escalation rules ship locally, mostly written in Chinese for now. Codex should explain them in the language you ask for, without changing what they require. This introduction doesn't establish cross-platform support or acceptance by independent users.
