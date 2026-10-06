# Release checklist

[简体中文](../RELEASE_CHECKLIST.md) · [English](RELEASE_CHECKLIST.md)

On 2026-10-05 the maintainer authorized making the repository public and chose MIT. This is the 0.2.0 public preview; there's no stable release. Anything unchecked hasn't been done.

## Source and documentation

- [x] The maintainer confirmed no external code was borrowed; the provider it depends on is a separate repository with its own attribution.
- [x] MIT license, attributed to ZHAOBIN-Lee; `skills/dev-orchestrator/` carries a copy.
- [x] Public files are limited to reviewed source, offline tests, templates, docs, and licenses.
- [x] No author local paths, login data, real sessions, task text, logs, or backups (the maintainer's public attribution aside).
- [x] The old `claude-bridge` is off the main branch and kept at the `legacy-claude-bridge` tag.
- [ ] Update the compatibility table after each platform is verified.

## Runtime acceptance

- [x] `devflow.py` offline tests: 54/54.
- [x] One live test each: a Claude chat spawning a GPT sub-agent, and a GPT chat spawning a Claude sub-agent.
- [ ] A full `/dev` run in a practice project for each execution mode (plan → code → validate → review → rework).
- [ ] Install from a fresh clone with the Skill installer; every resource is in place.
- [ ] In a fresh chat, "how do I use this?" explains without starting work.
- [ ] An independent friend installs it and completes a first `/dev` run from the docs.

## GitHub

Repository: [ZHAOBIN-Lee/codex-claude-skills](https://github.com/ZHAOBIN-Lee/codex-claude-skills). Before publishing anything new, review the files, Git history, Actions logs, and attachments. If CI is added, run offline tests only, hold no personal account or subscription credentials, pin third-party Actions to reviewed commits, and use `contents: read`.

Forks and copies that already exist can't be recalled by switching the repository back to private. See [GitHub's visibility documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
