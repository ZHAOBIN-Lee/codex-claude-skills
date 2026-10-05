# Updates, backups, and removal

[简体中文](../06-update-uninstall.md) · [English](06-update-uninstall.md)

There are no ready-made update or removal scripts yet. What follows is a manual process you can check step by step.

## Before updating

1. Make sure no Bridge call is running and no agent is editing the project.
2. Note the current repo version or commit, the full Skill installation directory, and where your personal configuration lives.
3. Back up the existing Skill, your runtime file, and your own modifications. Keep the backup out of the public repo.
4. Read the new version's changes, platform support, and migration notes, and compare the files. Keep what you've changed, and don't overwrite same-named files outright.

You can have Codex help with that step. Spell out the scope:

```text
$claude-bridge Compare this new version with my installation.
Prepare upgrade steps and a backup list first. Don't replace files or upgrade the official CLI until I explicitly ask you to apply them.
```

If you've already asked for the upgrade to be carried out, Codex does the preparation and replacement within that scope without asking again. It only needs to ask first when a change reaches an account, system, or project beyond what you authorized.

## Applying and checking

Replace with a version you've reviewed. Treat the Skill, program, templates, and tutorials as one unit and keep them at the same version. Your runtime file, cost confirmation, and pinned CLI path stay yours. Keep or migrate them yourself, and don't overwrite them with the author's.

Upgrading the official Claude Code is a separate job. The Bridge may pin the CLI's version and hash. After the CLI changes, re-verify the official file on your machine, the flags it needs, its version, and its integrity, then update the pin. Don't remove a guard to get rid of an error. Updating the Bridge also doesn't authorize upgrading other software on your machine.

Run the format check, the offline checks, and `doctor` first. Then run one real consultation in an authorized test project and check the receipt. If you plan to use continued conversations, also verify a second round in the same session. Passing offline or `--dry-run` checks can't replace a real call. For a new system or install route, record separately whether it passed or is still to be verified.

## Reverting

When something goes wrong, keep the current run records first, and look at whether you've added changes since the upgrade. Confirm that the files you're about to restore belong to this installation, then restore the Skill and its configuration from backup. Don't use `git reset --hard`, `git clean -fd`, or global cleanup commands to roll back.

Restoring an older Skill doesn't roll back Claude sessions, project handoffs, or tasks that went outside. Check each part of the project state on its own, and don't use old cache data as proof of a new successful recovery.

## Removing the Skill

Stop making calls first, and identify the installation location and the specific files the install put there. If you only want to stop routing to Claude, say "switch back to Codex" in the current chat. No removal is needed.

To remove it, first archive or move the installed `claude-bridge` directory, then deal with any entries that belong only to this tool, following the actual install record. Save anything you've modified. If you installed the optional `dev-orchestrator` separately, handle it using its own file list, and don't take other Skills, MCP configuration, or agent settings with it.

Leave these alone unless you explicitly ask to clean up a specific one:

- The official Claude Code installation, its login, account configuration, and native session history.
- Codex's login, chat history, and other tool configuration.
- Existing `.ai/` summaries, decisions, handoffs, logs, backups, and session metadata in your projects.
- Project code, uncommitted work, and Git history.

A project's `.ai/` may hold work by hand or by other tools, so removing the Skill is no reason to delete it wholesale. If cleanup is really needed, confirm who owns each item and whether it's worth keeping, and archive in preference to deleting.
