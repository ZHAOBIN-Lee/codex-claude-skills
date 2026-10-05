# Start here

[简体中文](../00-tour.md) · [English](00-tour.md)

Claude Bridge lets Codex call your local official Claude Code CLI when you request it, then bring the result back to the current chat. Codex schedules the work and checks the result; Claude handles the part you explicitly assign to it.

After installation, ask:

```text
$claude-bridge Teach me how to use this Skill in English. Do not actually call Claude.
```

This is a help request. Codex should read the relevant local tutorials and explain the workflow without calling Claude merely to explain its use. It should state which installation, configuration, or validation steps remain incomplete.

## Common uses

| Goal | What to say | What happens |
| --- | --- | --- |
| Check setup | "Check what is missing; do not call Claude yet" | Read installation details and use Bridge `doctor` if needed; no successful model-call receipt |
| Ask one question | "In this project, use Claude Sonnet at medium effort to analyze this plan; discussion only" | Supply the necessary material, use `consult`, return advice and the current call receipt |
| Continue a discussion | "For this project and topic, keep using Claude Sonnet at medium effort until I say switch back to Codex" | Relevant follow-ups in the current chat use that choice; the project's Claude session can be resumed |
| Develop a change | "Ask Claude to plan this change, have Codex implement and test it, then ask Claude to review it" | Follow the authorized standard development workflow; `dev-orchestrator` is optional |

Sonnet and medium are suggested starting choices, not standing authorization. You can choose another supported model or effort explicitly.

## A first test

Choose a test project where creating `.ai/` files is allowed. Tell Codex:

```text
$claude-bridge Help set up this test project.
You may create the necessary .ai/ handoff files in this project.
First check the official Claude Code CLI and my subscription login; do not read or save account secrets.
Once ready, use Claude Sonnet at medium effort to answer a short question and include the actual-model receipt.
```

If the project path, material to send, or account cost confirmation is unclear, Codex should ask for the missing information first. Normal follow-ups in the same project do not require reinstalling, reinitializing, or running `doctor` every time.

## Read as needed

- [First-time setup](01-setup.md)
- [Continued conversations](02-conversation.md)
- [Models, effort, and receipts](03-models-effort-receipt.md)
- [Development handoffs](04-dev-handoff.md)
- [Failures and waiting time](05-troubleshooting.md)
- [Updates and removal](06-update-uninstall.md)
- [Support and limits](07-limits.md)

This is a public-preview draft. The existing Bridge has real-call evidence in the author's macOS environment; new-machine installation, Linux, WSL, and native Windows need separate acceptance. Portable Skill text does not prove portable execution.
