# Updates, backups, and removal

[简体中文](../06-update-uninstall.md) · [English](06-update-uninstall.md)

Installation and removal interfaces depend on actual implementation and release version. This guide describes a reviewable manual process, not proposed commands presented as existing features.

## Before updating

1. Confirm no Bridge call is running and no agent is editing the project.
2. Record the version or commit, full Skill installation directory, and personal configuration location.
3. Back up the Skill, runtime, and local modifications outside the public repository.
4. Read the changes, platform support, and migration requirements. Compare files and preserve user modifications instead of overwriting them.

```text
$claude-bridge Compare this new version with my installation.
Prepare upgrade steps and a backup list first. Do not replace files or upgrade the official CLI until I explicitly request it.
```

If the user has already requested the upgrade, complete authorized preparation and replacement without asking again. Clarify account, system, or project changes outside that authorization.

## Applying and checking an update

Use a reviewed version. Keep the Skill, implementation, templates, tutorials, and license together. Preserve or migrate the user's runtime, cost confirmation, and pinned CLI path; do not replace them with the author's settings.

Upgrading official Claude Code is separate. If the CLI changes, verify its official origin, required flags, version, and integrity before updating the local pin. Do not remove guards to avoid errors or treat a Bridge update as authorization to upgrade all machine software.

Run format/offline checks and `doctor` first. Then, if authorized, make a real short consultation and verify its receipt. Continued-use acceptance includes a second round in the same session. Offline or dry-run success cannot replace real calls. Record new systems and installation routes independently as tested or pending.

## Reverting

Preserve runtime evidence and inspect user changes added after the upgrade. Confirm that the affected files belong to this installation before restoring the Skill and its configuration from backup. Do not use `git reset --hard`, `git clean -fd`, or global cleanup commands.

Restoring an older Skill does not automatically revert Claude sessions, project handoffs, or external tasks. Check project state separately and never use old cache data as proof of a new successful recovery.

## Removing the Skill

Stop calls and identify the actual installation directory and managed files. To stop routing only, say "switch back to Codex"; no uninstall is needed.

For removal, first archive or move the installed `claude-bridge` directory and handle only entries belonging to this installation. Preserve user modifications. If installed separately, handle optional `dev-orchestrator` according to its own file list; do not remove other Skills, MCP configuration, or agent settings.

Keep these unless the user explicitly requests a specific cleanup:

- Official Claude Code installation, login, account configuration, and native session history.
- Codex login, chat history, and other tool configuration.
- Existing project `.ai/` summaries, decisions, handoffs, logs, backups, and session metadata.
- Project code, uncommitted work, and Git history.

Project `.ai/` may contain human work or other tools' data. Do not delete it wholesale when removing a Skill. Check ownership and preservation value item by item and prefer archiving.
