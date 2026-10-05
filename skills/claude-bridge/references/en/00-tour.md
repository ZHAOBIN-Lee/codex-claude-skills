# Start here

[简体中文](../00-tour.md) · [English](00-tour.md)

Claude Bridge lets you hand a problem to Claude without leaving Codex. Codex calls the official Claude Code CLI on your machine, then brings Claude's answer back to the current chat. Codex stays on native GPT and handles scheduling and checking. Claude works on whatever you give it.

Once it's installed, start by asking how it works:

```text
$claude-bridge Teach me how to use this Skill in English. Do not actually call Claude.
```

That's a plain help request. Codex reads the tutorials in this folder and answers, without calling Claude. If something isn't installed, configured, or verified yet, it should say so.

## Common uses

| Goal | What to say | What happens next |
| --- | --- | --- |
| See what's missing | "Check what I still need; don't call Claude yet" | Reads the install info and runs `doctor` if needed. No model receipt, because nothing was called |
| Ask Claude a question | "In this project, use Claude Sonnet at medium effort to analyze this plan; discussion only" | Runs `consult` and returns the advice with that call's receipt |
| Keep talking | "For this project and topic, keep using Claude Sonnet at medium effort until I say switch back to Codex" | Follow-ups in this chat reuse the choice and request the project's previous Claude session |
| Make a change | "Ask Claude to plan this change, have Codex implement and test it, then ask Claude to review" | Follows the standard development handoff; `dev-orchestrator` can help |

Sonnet at medium effort is a starting suggestion. It doesn't become standing permission on its own, and you can name another model or effort at any time.

## A first try

Pick a test project where creating `.ai/` files is fine, and tell Codex:

```text
$claude-bridge Help set up this test project.
You may create the necessary .ai/ handoff files in this project.
First check the official Claude Code CLI and my subscription login; don't read or save account secrets.
Once it's ready, use Claude Sonnet at medium effort to answer a short question and include the actual-model receipt.
```

If the project path, the material to send, or your account's cost settings are unclear, Codex asks first. After setup, follow-ups in the same project need no reinstalling, reinitializing, or `doctor` run.

## Where to go next

- [First-time setup](01-setup.md)
- [Continued conversations](02-conversation.md)
- [Models, effort, and receipts](03-models-effort-receipt.md)
- [Development handoffs](04-dev-handoff.md)
- [Failures and waiting time](05-troubleshooting.md)
- [Updates and removal](06-update-uninstall.md)
- [Support and limits](07-limits.md)

This is a public preview. The bundled Bridge has real-call results on the maintainer's macOS. A new machine, Linux, WSL, and native Windows haven't been checked. The Skill's text works anywhere, but the bundled program needs its own validation per platform; see [limits](07-limits.md).
