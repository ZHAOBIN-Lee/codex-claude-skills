# Verification notes

[简体中文](../LOCAL_VERIFICATION.md) · [English](LOCAL_VERIFICATION.md)

This page records how far verification has got and what hasn't been done.

## Where things stand

The repository is public. An anonymous clone of the public repository and a check of its 82 files have both been completed.

On the maintainer's own Mac, with official CLI 2.1.285, real calls, continued sessions, and development handoffs have been run. That is the baseline for the current implementation. A friend's machine, a fresh Codex install, Linux/WSL, native Windows, and GitHub CI have not been verified yet; the to-do list is at the end of this page.

## Offline test baseline

These are the local checks made at packaging time, dated 2026-10-05. The Python implementation and offline test files still match the hashes of the tested baseline, and only documentation has changed since. So the results below belong to the existing baseline, and they have not been rerun.

| Check | Result | Notes |
| --- | --- | --- |
| Repackaged Bridge offline tests | 84/84 passed, 49.465 seconds | Fake CLI, no real model calls |
| Optional orchestrator offline tests | 48/48 passed, 0.447 seconds | Task lifecycle and deterministic behavior |
| Two Skill-format checks | Passed | Frontmatter and naming |
| Core Skill directory copied alone | Passed | Only copied; not installed into a global Skill directory |
| Python entry point and init from a standalone directory | Passed; init reported `inference=false` | Program and resources found; no real inference |
| Eight Chinese tutorials and relative links | Present; link check passed | Automatic routing in a fresh chat wasn't tested |
| Check for author paths and runtime material | Passed | No author paths, real sessions, runtime config, installation records, logs, or backups |
| Six help/setup/call scenarios | Independent review of the instruction rules passed | Not a desktop routing test |
| One real Claude planning consultation during packaging | Completed; official result Sonnet 5.5 | Used the maintainer's existing Bridge, not a fresh-machine setup of this preview |

Before exporting the source, real configuration and state were removed, and the maintainer's active installation wasn't replaced. The source keeps its existing implementation. The distributed Skill adds help routing and notes on a portable entry point, and the example config starts with the cost status "unconfirmed".

Packaging also fixed a few problems in the tutorials: leftover "upstream source to be checked" wording, the Python minimum, and consultation-metadata entries missing from the optional gitignore snippet.

The public update added the Chinese and English docs and the MIT license copies. Its checks covered the new links, JSON, required resources, license copies, and the upload allowlist.

The documentation update on 2026-10-05 changed 37 Chinese and English pages. All 169 relative links were checked, and all eight tutorials in each language are present. Programs, tests, configuration, binding Skill instructions, and licenses still match the original baseline. The offline tests above were not rerun for this update.

## Not verified yet

- Installing through Codex's `$skill-installer` on a fresh machine (the anonymous clone check doesn't stand in for this)
- An independent friend working through the tutorial
- Real calls on Linux/WSL
- The native-Windows execution layer
- GitHub CI
- A full upgrade and removal run
- Personal runtime setup: there's no one-step tool yet, so follow [first-time setup](../../skills/claude-bridge/references/en/01-setup.md) by hand

Visibility and remote-file checks are publication checks. They don't count as the runtime verification above.
