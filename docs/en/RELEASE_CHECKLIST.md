# Release checklist

[简体中文](../RELEASE_CHECKLIST.md) · [English](RELEASE_CHECKLIST.md)

On 2026-10-05 the maintainer authorized upload and making the repository public, and chose MIT. This is the 0.1.0-draft public preview; there's no stable release. The checklist separates what the preview has done from what a stable release still needs. Anything unchecked hasn't been done.

## Source and documentation

- [x] The maintainer confirmed no external code was borrowed; documentation writing references are listed separately.
- [x] MIT license, attributed to ZHAOBIN-Lee; every installable unit carries a copy.
- [x] Public files are limited to reviewed source, offline tests, generic templates, tutorials, and licenses.
- [x] No author local paths, login data, cost confirmations, real sessions, task text, logs, or backups (the maintainer's public attribution aside).
- [x] Local doc references and tutorial links checked; the tutorials live inside the Skill directory and don't depend on files outside it.
- [x] The docs say personal config belongs outside the install directory; a full upgrade-preservation run hasn't been tested yet.
- [ ] An executable setup flow that binds the CLI's origin, version, and capabilities (for now this is manual, following the tutorial).
- [ ] Runtime adapters finished for each platform, and the support table updated from the results.

## Runtime acceptance

- [x] Offline tests passed: Bridge 84/84, orchestrator 48/48 (results from the existing baseline).
- [ ] From a fresh clone, install only the core Skill through Codex's Skill installer and confirm every resource is in place.
- [ ] In a fresh desktop chat, ask "how do I use this?" and get the local tutorial without a Claude call.
- [ ] "Help me set up" and "help me debug" go to the right mode and aren't treated as inference requests.
- [ ] First real call, a follow-up, and switching back to Codex all follow the user's authorization.
- [ ] The model, session, and status in each receipt match that call's official result, with unique evidence.
- [ ] Failures, timeouts, unconfirmed cost, permission denials, and save failures are never reported as success.
- [ ] After an upgrade, revert, or removal, the existing CLI, account history, and project handoffs are still there.
- [ ] An independent friend completes the tutorial without relying on the author's setup.

## GitHub

Preview repository: [ZHAOBIN-Lee/codex-claude-skills](https://github.com/ZHAOBIN-Lee/codex-claude-skills). It's public, and an anonymous clone with a check of its 82 files has been completed. The maintainer directly authorized creating it and making it public. Inviting friends, running real-model tests, and publishing a stable release each need separate authorization; this checklist doesn't imply it.

Before publishing anything new, review the files, Git history, Actions logs, and attachments. If CI is added, it should run only offline tests, hold no personal Claude account or subscription credentials, pin third-party Actions to reviewed commits, use `contents: read`, and make no automatic real-model calls.

A stable release needs a version tag or Release and a changelog. The first release centers on `claude-bridge`; `dev-orchestrator` stays experimental until its dependency install and independent-user flow have been verified.

Forks and copies that already exist can't be recalled by switching the repository back to private. See [GitHub's visibility documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
