# First-time installation and local configuration

[简体中文](../01-setup.md) · [English](01-setup.md)

If you're not sure where to start, ask Codex:

```text
$claude-bridge Guide me through first-time setup. Establish my operating system, installation directory, and test project first. Do not call Claude yet.
```

## What you need first

- A Codex environment that can load Skills.
- Python 3.9 or newer. The bundled Bridge currently relies on POSIX features (`fcntl` file locks, process groups, private file permissions); see [limits](07-limits.md) for other platforms.
- The official Claude Code CLI on your machine, signed in with your own claude.ai subscription.
- A project directory and a task you're willing to send to Claude. Installing the Skill doesn't authorize any project.

Follow the [official setup](https://code.claude.com/docs/en/setup) and [authentication](https://code.claude.com/docs/en/authentication) guides for Claude Code. Do the browser sign-in yourself, and don't send Codex passwords, cookies, tokens, or verification codes. Which systems Claude Code supports and which systems this Bridge has been tested on are separate questions.

The Bridge currently accepts only `authMethod: claude.ai` with `subscriptionType: pro|max`. Team, Enterprise, Console API, and third-party providers aren't adapted yet. Don't edit the authentication result to get past the check.

## Install the Skill

Install the whole `skills/claude-bridge/` directory. `SKILL.md`, `lib/bridge.py`, the templates, and the `references/` tutorials all live in it. Copying only `SKILL.md` leaves out the program and the help files.

Install into the Skill directory your Codex actually reads. If a Skill with the same name is already there, back it up and compare before replacing or keeping it. You can ask Codex's Skill installer to do it:

```text
$skill-installer Install skills/claude-bridge from https://github.com/ZHAOBIN-Lee/codex-claude-skills using the main branch preview. If a Skill with that name is installed, compare and back it up first.
```

That uses the installer that ships with Codex. This repo has no custom one-step setup tool, and there is no stable tag yet.

Afterward, invoke `$claude-bridge` once and see whether Codex finds the Skill and its tutorials. If it doesn't, check that the directory is complete and the Skill format validates, then follow your Codex version's discovery behavior. You may not need to restart, but don't assume the Skill is live the moment it's copied.

## Create your own runtime file

`runtime.json` is configuration for your machine, kept outside the Skill directory. Use [runtime.example.json](../../templates/runtime.example.json) as the format, and fill in:

- The absolute path of your official CLI.
- The version you verified. The author currently uses 2.1.285.
- That file's SHA-256. Compute it on your own machine; the author's hash isn't yours to copy.
- Evidence that the file came from the official source. A hash of some random file on your PATH only identifies that file; it doesn't show the file is official.

Don't leave the version or hash empty to slip past the checks.

The cost status is yours to confirm too. Check your account's cost settings and confirm that extra usage credits are off. Then record `subscription_usage_credits_disabled: true` plus the source and date of your confirmation in `usage_credits_confirmation`. This is your own confirmation; the script doesn't read Billing. Don't reuse the example's values, the author's confirmation, or another account's.

Leave it as unconfirmed until you've checked, and real calls stay blocked. Confirm again if you switch accounts or change cost settings. If it's already confirmed and still true, no need to ask again. Keep credentials and authentication files out of the repo and out of the runtime file.

## Check your first project

These lines show the Bridge's existing argument shape. `<SKILL_DIR>`, `<RUNTIME_JSON>`, and `<PROJECT_DIR>` are placeholders; swap in your real absolute paths.

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> doctor --project <PROJECT_DIR>
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> init --project <PROJECT_DIR>
```

`doctor` only checks the environment and makes no model call. `init` fills in missing `.ai/` files in a project you've authorized. Existing handoffs stay, and it never creates or rewrites the root `AGENTS.md` or `CLAUDE.md`. If the project already has `.ai/`, read what's there first.

To verify for real, run one short consultation. A plain "how do I use this" request never does this, and the run uses your Claude subscription allowance. `--dry-run` only checks preparation and can't show that Claude was actually called.

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow consult --mode sonnet --task "Give one sentence of advice for this test task" --effort medium --effort-source user --effort-reason "User-selected first-test effort" --timeout 180
```

When Codex runs this, paths and your text go in as separate arguments or with correct shell quoting. After it succeeds, look at four things: this call's actual model, the full session ID, the status, and the single matching evidence. Then try a continuation using the [conversation guide](02-conversation.md). Templates created, a successful login, and a passing `doctor` don't mean you're done. A real call that succeeds does.
