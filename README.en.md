# Codex Claude Skills

[简体中文](README.md) · [English](README.en.md)

You're working in Codex and want Claude's opinion on a design, a diff, or a bug that won't die. The usual routine is to copy the material into Claude's app, wait, and paste the answer back. After a few rounds the context is scattered across two windows.

The `claude-bridge` Skill skips the copying. Ask in Codex, and Codex hands the question to Claude through the official Claude Code CLI already signed in on your machine, then brings the answer back to the same chat. Follow-ups work the same way. Every call comes with a short receipt: which model actually answered, the session ID, and whether the call succeeded. You don't have to take "I'm Sonnet" from the model's own mouth; you can check.

Codex itself stays on native GPT. Claude is only called when you ask for it.

This is a community project, not affiliated with Anthropic or OpenAI, under the [MIT License](LICENSE).

> **0.1.0-draft public preview; no stable release yet.** Tested on the maintainer's Mac. See [Platforms and validation](#platforms-and-validation) for other environments.

## Quick start

You need:

- Codex with Skill support.
- The official Claude Code CLI on your machine, signed in with your own claude.ai Pro or Max subscription. See the [official setup guide](https://code.claude.com/docs/en/setup).
- Python 3.9 or newer.

Send this to Codex to install the whole `skills/claude-bridge/` directory:

```text
$skill-installer Install skills/claude-bridge from https://github.com/ZHAOBIN-Lee/codex-claude-skills using the main branch preview. If a Skill with that name is installed, compare and back it up first.
```

If the installer says Codex needs a restart to see the new Skill, do that. Then ask how it works before making any real call:

```text
$claude-bridge How do I use this Skill? Give me the beginner's guide in English.
$claude-bridge Check what I need for first-time setup. Do not call Claude yet.
```

Both only read the local tutorials. Neither calls Claude.

First-time setup means writing a runtime file for your own official CLI (CLI path, version, SHA-256; see [runtime.example.json](skills/claude-bridge/templates/runtime.example.json) for the format). Keep it outside the Skill directory and pass it with `--runtime`. You also check your own account, confirm that extra usage credits are off, and record that. The example file starts as "unconfirmed", and real calls stay blocked until you confirm. Both steps are per user; don't copy the author's. The details are in [first-time setup](skills/claude-bridge/references/en/01-setup.md), and Codex can walk you through it. Default preferences live in [preferences.example.json](skills/claude-bridge/templates/preferences.example.json).

## One real request

Once setup is done, ask in your project:

```text
In this project, use Claude Sonnet at medium effort to find holes in docs/plan.md. Discussion only; don't edit files.
```

Codex states the model and effort first, sends Claude the material it needs, and brings back the advice with a receipt at the end:

```text
Claude receipt: actual model <this call's actual_models> | session <full session_id> | status <status> | evidence <this call's log link>
```

The angle brackets are placeholders. Each call fills them from its own result.

To keep the discussion going, say so once:

```text
From now on, keep using Claude Sonnet at medium effort for this plan until I say switch back to Codex.
```

After that, "continue and expand the second point" in the same chat is enough. "Switch back to Codex" stops it. A different project or a new chat needs a fresh instruction.

## What it does

| Goal | You can say | What runs |
| --- | --- | --- |
| Ask one question | "Ask Claude Sonnet to look at this problem" | `consult`: analyzes only the material you supply, with built-in tools and MCP off for that call |
| Keep a discussion going | "For this project, use Claude until I say switch back to Codex" | Requests the project's previous session; `consult` sends only changes when resuming succeeds and the baseline remains valid |
| Check the model | "Include the actual model and call evidence" | Included by default on every call |
| Edit files or review a diff | "Have Claude review this project's diff" | `standard`: normal permissions, and Codex checks the result independently |
| Development workflow (optional) | Install `dev-orchestrator` | Experimental: Claude plans and reviews, native GPT executes, scripted checks move the state forward |

The suggested default is Sonnet at medium effort. That's a preference the Skill follows. Name another model or effort and yours wins.

## Platforms and validation

| | macOS | Linux / WSL | Native Windows |
| --- | --- | --- | --- |
| Skill text and tutorials | Shared | Shared | Shared |
| Bundled Bridge program | Tested in the maintainer's environment | Not validated | Needs adapting (uses POSIX locks and process control) |

The maintainer's Mac runs official CLI 2.1.285. The permissions and timeout repair on 2026-10-06 passed 136/136 Bridge and 48/48 dispatcher offline tests. Real subscription checks also covered an allowed write, a missing-permission block before inference, and an early stop on a runtime denial. There is no stable tag or Release yet.

Still to do: install by an independent friend, Codex install on a fresh machine, real calls on Linux/WSL, native Windows, and GitHub CI. Team, Enterprise, Console API, and third-party providers are not supported.

For the itemized lists, see [local verification](docs/en/LOCAL_VERIFICATION.md) and the [compatibility plan](docs/en/COMPATIBILITY.md).

## Tutorials

The tutorials ship inside the Skill, so Codex can read them on demand. You can also ask it to explain in English or Chinese. The Chinese versions are one directory up in [references/](skills/claude-bridge/references/00-tour.md).

1. [Five-minute tour](skills/claude-bridge/references/en/00-tour.md)
2. [First-time setup](skills/claude-bridge/references/en/01-setup.md)
3. [Continued conversations and switching back](skills/claude-bridge/references/en/02-conversation.md)
4. [Models, effort, and receipts](skills/claude-bridge/references/en/03-models-effort-receipt.md)
5. [Development handoffs](skills/claude-bridge/references/en/04-dev-handoff.md)
6. [Troubleshooting](skills/claude-bridge/references/en/05-troubleshooting.md)
7. [Updates and removal](skills/claude-bridge/references/en/06-update-uninstall.md)
8. [Limits](skills/claude-bridge/references/en/07-limits.md)
9. [Writing permissions and failure handling](skills/claude-bridge/references/en/08-permissions-and-failures.md)

The optional workflow has its own [English guide](skills/dev-orchestrator/references/guide.en.md). To look around before installing, the [Skill instructions](skills/claude-bridge/SKILL.md) and the tour are enough.

## Other docs

- [Compatibility plan](docs/en/COMPATIBILITY.md): what each platform still needs
- [Local verification](docs/en/LOCAL_VERIFICATION.md)
- [Preview and release checklist](docs/en/RELEASE_CHECKLIST.md)
- [License](LICENSING.en.md), [provenance](docs/en/PROVENANCE.md), [third-party notices](THIRD_PARTY_NOTICES.en.md)
- [Contributing](CONTRIBUTING.en.md), [privacy and issue reporting](SECURITY.en.md), [changelog](CHANGELOG.en.md)

The repository contains source, offline tests, generic templates, and tutorials. You provide Claude Code and your own account; personal configuration and runtime state stay on your machine.
