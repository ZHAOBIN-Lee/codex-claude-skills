# First-time installation and local configuration

[简体中文](../01-setup.md) · [English](01-setup.md)

Start with:

```text
$claude-bridge Guide me through first-time setup. Establish my operating system, installation directory, and test project first. Do not call Claude yet.
```

## Prerequisites

- A Codex environment that can load Skills.
- Local Python 3.9 or newer and the runtime capabilities needed by the bundled Bridge. The current implementation uses POSIX features; see [limits](07-limits.md) for other platforms.
- The local official Claude Code CLI, signed in with your own Claude.ai subscription.
- An explicit project directory, task, and material you authorize sending to Claude. A global Skill installation does not establish project authorization.

Follow [official setup](https://code.claude.com/docs/en/setup) and [authentication instructions](https://code.claude.com/docs/en/authentication). Complete browser sign-in yourself; do not give Codex passwords, cookies, tokens, or verification codes. Distinguish Claude Code's platform support from this Bridge's verified support.

The current Bridge accepts only `authMethod: claude.ai` with `subscriptionType: pro|max`. Other official account routes exist, but this preview has not adapted every route. Do not claim Team, Enterprise, Console, or third-party-provider support or fabricate authentication output to pass a check.

## Installing the whole Skill

Install the complete `skills/claude-bridge/` directory, including `SKILL.md`, `lib/bridge.py`, templates, license, and `references/`. Copying only `SKILL.md` omits the program and tutorials.

Use the Skill directory actually discovered by your Codex environment. Compare and back up a modified Skill with the same name before replacing it. With Codex's Skill installer, you can request:

```text
$skill-installer Install skills/claude-bridge from https://github.com/ZHAOBIN-Lee/codex-claude-skills using the main branch preview. Compare and back up an existing installation first.
```

This uses the host's installer; the repository does not provide a custom setup utility. No stable tag is published yet. Explicitly invoke `$claude-bridge` and have Codex confirm it can find the Skill and its tutorials. If discovery fails, check the directory and format, then follow the host's discovery guidance. Do not assume immediate discovery or that every environment must restart.

## Create your own runtime file

Use [runtime.example.json](../../templates/runtime.example.json) as a schema example. Keep your personal runtime outside the Skill directory. Fill in your local official CLI's absolute path, verified version, and SHA-256 hash, and retain evidence of its official origin. Hashing an arbitrary PATH executable does not establish its source. Do not leave version or hash empty to bypass checks.

Cost confirmation must come from you. After checking your own account's settings and confirming extra usage credits are disabled, record `subscription_usage_credits_disabled: true` with a user-sourced, dated `usage_credits_confirmation`. This is your confirmation, not proof that the script read Billing directly. Do not inherit the author's or another account's confirmation.

Keep unknown fields unconfirmed so real calls are blocked. Update confirmation when the account or cost settings change. Do not repeatedly ask for the same still-valid fact. Do not place credentials or authentication files in the runtime or repository.

## First project check

These examples show the existing parameter structure. Replace `<SKILL_DIR>`, `<RUNTIME_JSON>`, and `<PROJECT_DIR>` with verified local absolute paths; do not execute literal placeholders.

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> doctor --project <PROJECT_DIR>
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> init --project <PROJECT_DIR>
```

`doctor` checks the environment without model inference. `init` creates missing `.ai/` files only in an authorized project, preserving existing handoffs. It does not create or rewrite root `AGENTS.md` or `CLAUDE.md`. Inspect existing project state first.

An actual short test is optional and requires your explicit request. It uses your Claude subscription allowance. `--dry-run` checks preparation only and cannot prove a real model call.

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow consult --mode sonnet --task "Give one sentence of advice for this test task" --effort medium --effort-source user --effort-reason "User-selected first-test effort" --timeout 180
```

Use separate arguments or correct shell quoting for paths and text. Verify the current actual model, full session ID, status, and uniquely matched evidence. Then use [the conversation guide](02-conversation.md) to test continuation if needed. Created templates, a successful login, or a passing `doctor` check do not establish end-to-end installation acceptance.
