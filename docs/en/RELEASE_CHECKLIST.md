# Preview and release checklist

[简体中文](../RELEASE_CHECKLIST.md) · [English](RELEASE_CHECKLIST.md)

On 2026-10-05, the maintainer explicitly authorized upload and public visibility and selected MIT. This checklist distinguishes the public preview from stable-release acceptance. Unchecked items remain incomplete.

## Source and documentation

- [x] Record the maintainer's confirmation of no borrowed external sources.
- [x] Select MIT and the copyright attribution ZHAOBIN-Lee; include license copies in installation units.
- [x] Limit public files to reviewed source, offline tests, generic templates, documentation, and licenses.
- [x] Exclude personal local paths, login data, cost confirmations, real sessions, complete tasks, logs, and backups; retain public maintainer attribution.
- [x] Check local documentation links and include tutorials inside the Skill directory.
- [x] Specify external personal configuration in the docs; complete upgrade-preservation acceptance remains pending.
- [ ] Provide a fully executable official-CLI origin/version/capability setup flow.
- [ ] Finish platform adapters and update the support table with evidence.

## Runtime acceptance

- [x] Bridge 84/84 and orchestrator 48/48 offline tests passed.
- [ ] Install only the core Skill from a fresh clone through the actual host installer.
- [ ] Verify help without a real Claude call in a fresh desktop chat.
- [ ] Verify setup/troubleshooting routing without unintended inference.
- [ ] Verify first real call, follow-up, and switching back under user authorization.
- [ ] Match receipt model, session, status, and unique evidence to each official result.
- [ ] Verify failures, timeouts, cost-blocked operations, denials, and save failures are not reported as success.
- [ ] Verify upgrade, revert, and removal preserve existing CLI, account history, and project handoffs.
- [ ] Have an independent user complete the tutorial without the author's environment.

## GitHub

Public preview repository: [ZHAOBIN-Lee/codex-claude-skills](https://github.com/ZHAOBIN-Lee/codex-claude-skills). Creation and public visibility were explicitly authorized. This checklist does not authorize invitations, real-model tests, or a stable release.

Review files, Git history, Actions logs, and attachments before publication. Any future CI should run offline tests without personal accounts or credentials, use reviewed pinned Actions, and have `contents: read` permissions. It should not make automatic real-model calls.

A stable release needs a version tag/Release and changelog. The core component is `claude-bridge`; keep `dev-orchestrator` experimental until dependency installation and independent-user flows pass.

Public forks and existing copies cannot be recalled by switching visibility back to private. See [GitHub's visibility documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
