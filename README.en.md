# Codex Claude Skills

[简体中文](README.md) · [English](README.en.md)

Call the official Claude Code CLI from Codex in the same project, with continued conversations, development handoffs, and verifiable model receipts.

Community project, not an official Anthropic or OpenAI integration.

**Status: 0.1.0-draft public preview under the [MIT License](LICENSE). No stable release is available. The maintainer has confirmed that this project was not derived from other repositories.**

Repository: [ZHAOBIN-Lee/codex-claude-skills](https://github.com/ZHAOBIN-Lee/codex-claude-skills). Local macOS offline checks have passed. Fresh-machine setup and real cross-platform calls still require validation.

## Ask the installed Skill how to use it

The core installation unit is `skills/claude-bridge/`. It includes the instructions, Python implementation, templates, license, and Chinese and English tutorials. It does not require the repository-root documentation or the author's local directories.

After installation, ask Codex:

```text
$claude-bridge How do I use this Skill? Give me the beginner's guide in English.
$claude-bridge Check what I need for first-time setup. Do not call Claude yet.
$claude-bridge Explain how to keep discussing a project with Claude and switch back to Codex.
```

Help reads the local tutorials without calling Claude. Codex itself still uses its normal allowance; this does not make all model usage free.

## What it supports

| Goal | Example request | Behavior |
| --- | --- | --- |
| One consultation | "Ask Claude Sonnet to analyze this problem" | Uses `consult` for analysis; establish the project and material scope |
| Continued discussion | "For this project and topic, use Claude Sonnet at medium effort until I say switch back to Codex" | Explicit authorization in the current chat; later calls can resume the project's Claude session |
| Verify the actual model | "Include the actual model and call evidence" | Every actual call includes the model, full session ID, status, and matching evidence |
| File work or review | "Have Claude review this project's diff" | Uses `standard` with normal permissions; Codex verifies the result independently |
| Development workflow | Install the optional `dev-orchestrator` | Experimental: Claude plans and reviews, native GPT executes, tools validate |

The Codex chat keeps its native model. This does not add Claude to Codex's native model menu or share either model's hidden reasoning. Expressions such as `@claude` are semantic conventions understood by the Skill.

## Install the preview

**Read the platform and validation table before installing. This is a preview, not a stable release.**

Send this to Codex:

```text
$skill-installer Install skills/claude-bridge from https://github.com/ZHAOBIN-Lee/codex-claude-skills using the main branch preview. If a Skill with that name is installed, compare and back it up first.
```

Install the entire Skill directory, not only `SKILL.md`. If the installer asks you to restart Codex to discover the new Skill, follow its instructions. Then ask for the beginner's guide and setup check before making a real call. There is no stable tag yet; a future stable installation should pin a tag or commit rather than follow a changing `main` branch.

For a local review, open the [Skill instructions](skills/claude-bridge/SKILL.md) and [five-minute tour](skills/claude-bridge/references/en/00-tour.md). Before using it in another environment, complete [first-time setup](skills/claude-bridge/references/en/01-setup.md). Compare and back up an existing installation before replacing it.

Each user installs and signs in to the official Claude Code CLI, establishes their own CLI path, version and integrity evidence, and confirms their account's cost settings. The repository includes no Claude binary, account, credentials, author-specific cost confirmation, or runtime state. See [official Claude Code setup](https://code.claude.com/docs/en/setup).

## Configuration and project state

- [Preference example](skills/claude-bridge/templates/preferences.example.json): suggested defaults are Sonnet and medium effort; explicit user choices take priority.
- [Runtime example](skills/claude-bridge/templates/runtime.example.json): cost settings start unconfirmed and cannot authorize a real call.
- Store personal configuration outside the Skill directory and pass it explicitly with `--runtime`. Preserve it during upgrades.
- Project `.ai/` files hold handoffs, sessions, incremental-context fingerprints, and logs. Installing the Skill, setting defaults, or finding a cache does not authorize model calls.

Preferences are interpreted by the Skill; the Bridge does not automatically parse a new preference subsystem. They do not change Codex's native model or effort settings. Ask for Chinese or English help as needed.

## Platforms and validation

| Component | macOS | Linux / WSL | Native Windows |
| --- | --- | --- | --- |
| Skill text and tutorials | Shareable | Shareable | Shareable |
| Current Bridge implementation | Real calls tested in the author's environment | Independent validation needed | POSIX locks and process handling need adaptation |
| Repackaged preview | Local checks documented below | Not tested | Not tested; no native-runtime support claim |

The goal is one Skill and tutorial set with platform-specific execution adapters. Claude Code supporting a platform does not prove that this Bridge already works on it. See the [compatibility plan](docs/en/COMPATIBILITY.md).

## Tutorials

Both languages are included in the installed Skill. English guides:

1. [Five-minute tour](skills/claude-bridge/references/en/00-tour.md)
2. [First-time setup](skills/claude-bridge/references/en/01-setup.md)
3. [Continued conversations and switching back](skills/claude-bridge/references/en/02-conversation.md)
4. [Models, effort, and receipts](skills/claude-bridge/references/en/03-models-effort-receipt.md)
5. [Development handoffs](skills/claude-bridge/references/en/04-dev-handoff.md)
6. [Troubleshooting](skills/claude-bridge/references/en/05-troubleshooting.md)
7. [Updates and removal](skills/claude-bridge/references/en/06-update-uninstall.md)
8. [Limits](skills/claude-bridge/references/en/07-limits.md)

The optional workflow also has an [English introduction](skills/dev-orchestrator/references/guide.en.md).

## Maintenance

- [Project provenance](docs/en/PROVENANCE.md)
- [Third-party notices](THIRD_PARTY_NOTICES.en.md)
- [License details](LICENSING.en.md)
- [Preview and release checklist](docs/en/RELEASE_CHECKLIST.md)
- [Local verification](docs/en/LOCAL_VERIFICATION.md)
- [Contributing](CONTRIBUTING.en.md)
- [Privacy and reporting issues](SECURITY.en.md)
- [Changelog](CHANGELOG.en.md)

The maintainer authorized this public preview. It is not a stable release or proof of independent-user and cross-platform acceptance. Only reviewed source files, offline tests, generic templates, documentation, and licenses are included. Review future files, Git history, and Actions logs before publication. Existing forks and copies are not recalled by making a public repository private. See [GitHub's visibility documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
