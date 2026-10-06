# Codex Claude Skills

[简体中文](README.md) · [English](README.en.md)

Claude writes the plan, GPT writes the code, Claude checks it. `dev-orchestrator` splits a development task into steps for different models, keeps state in the project's `.ai/` directory, and runs the validation commands itself instead of trusting a model's "tests pass".

It uses only Codex's native models and sub-agents, so Claude and GPT need to be in the same Codex model picker. [codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin) does that; install it first.

This is a community project, not affiliated with Anthropic or OpenAI, under the [MIT License](LICENSE).

> **0.2.0 public preview.** Used only on the maintainer's macOS so far. The old `claude-bridge` (relaying through the Claude Code CLI) is no longer maintained; its last version is kept at the [`legacy-claude-bridge`](https://github.com/ZHAOBIN-Lee/codex-claude-skills/tree/legacy-claude-bridge) tag.

## Quick start

You need:

- [codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin) installed, with GPT and Claude both in the model picker.
- Codex multi-agent enabled (`multi_agent = true` under `[features]` in `config.toml`), and Claude sub-agent roles such as `claude_opus` and `claude_sonnet` (the provider's install creates them).
- Python 3.9 or newer.

Install it by sending this in Codex:

```text
$skill-installer Install skills/dev-orchestrator from https://github.com/ZHAOBIN-Lee/codex-claude-skills. If a Skill with the same name exists, compare and back it up first.
```

Then ask how it works. This doesn't start any development:

```text
$dev-orchestrator How does this workflow work? Do not start yet.
```

## One real request

Pick Claude in the model picker, then say:

```text
In /path/to/project, use the development workflow to add a CSV export. Keep my existing uncommitted changes.
```

The strong model is the Claude model the current chat uses; you aren't asked again. Before it starts, it asks one thing: the execution mode.

| Mode | Plan | Code | Check |
| --- | --- | --- | --- |
| Claude dispatches GPT sub-agents | the Claude chat | GPT sub-agents | Claude validates and reviews itself, writes rework tasks, and sends GPT back |
| Switch to GPT | Claude | you switch the chat to GPT, which codes | GPT spawns a read-only Claude sub-agent to review |
| Claude does everything | Claude | Claude | a fresh-context Claude sub-agent, reported as same-model-family review |

The first mode suits continuous work: Claude keeps checking and GPT keeps working, with no model switching. Planning only happens in a Claude chat; if the current chat's model doesn't match the next step, the workflow stops and asks you to switch.

To pick up later, say "continue the development workflow". For progress only, say `/dev status`; that calls no model.

## Common requests

| Request | What it does |
| --- | --- |
| `Use the development workflow to implement <goal>` / `/dev new` | New goal: plan, split into tasks, then advance to a stopping point |
| `Continue the development workflow` / `/dev continue` | One next step |
| `/dev run` | Advance continuously within the limits |
| `/dev status` | Read-only progress, no model call |
| `/dev plan` | Plan only, no execution |
| `/dev review` | Review the current task or diff directly |
| `/dev resolve` | When a task is blocked, let Claude find the root cause |

## When it stops

A missing business decision, a scope that contradicts the repo, workspace conflicts it can't handle, an unavailable model or sub-agent, the wrong model in the current chat, validation that can't run, task or rework limits reached, or you saying stop. High-risk or irreversible operations are judged against what you actually authorized. It never bypasses a permission check to keep going, and never quietly substitutes GPT for a Claude step.

## Validation status

- 54 offline tests for `devflow.py` pass (`python3 -m unittest discover -s skills/dev-orchestrator/tests`).
- Sub-agents were tested live: a Claude chat spawned a GPT sub-agent, and a GPT chat spawned a Claude sub-agent; each ran one command, and the actual model matched the request.
- Not yet verified on an independent user's machine, on Linux or Windows, or as a full multi-task run in a real project after this rewrite.

Details: [local verification record](docs/en/LOCAL_VERIFICATION.md).

## Docs

- [Skill instructions](skills/dev-orchestrator/SKILL.md) (Chinese, binding rules) and the [English guide](skills/dev-orchestrator/references/guide.en.md)
- [Compatibility](docs/en/COMPATIBILITY.md), [local verification](docs/en/LOCAL_VERIFICATION.md), [release checklist](docs/en/RELEASE_CHECKLIST.md)
- [Licensing](LICENSING.en.md), [provenance](docs/en/PROVENANCE.md), [third-party notices](THIRD_PARTY_NOTICES.en.md)
- [Contributing](CONTRIBUTING.en.md), [privacy and reporting](SECURITY.en.md), [changelog](CHANGELOG.en.md)
