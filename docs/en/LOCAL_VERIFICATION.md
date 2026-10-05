# Verification notes

[简体中文](../LOCAL_VERIFICATION.md) · [English](LOCAL_VERIFICATION.md)

This page records how far verification has got and what hasn't been done.

## Where things stand

The repository is public. An anonymous clone and a check of 82 files were completed after the initial publication. The program repair has its own verification notes below.

On the maintainer's own Mac, with official CLI 2.1.285, real calls, continued sessions, and development handoffs have been run. That is the baseline for the current implementation. A friend's machine, a fresh Codex install, Linux/WSL, native Windows, and GitHub CI have not been verified yet; the to-do list is at the end of this page.

## 2026-10-06: permissions and timeout repair

This update changes the Bridge program and Skills. Its results are recorded separately from the original packaging baseline. Claude made the main code and documentation changes; Codex independently inspected the files and ran tests afterward.

| Check | Result |
| --- | --- |
| Final Bridge offline suite | 136/136 passed, 108.266 seconds; fake CLI, no real model calls |
| Dispatcher offline suite | 48/48 passed, 0.425 seconds |
| Public and active variants of both Skills | Four frontmatter blocks passed YAML parsing, naming and description checks |
| Real subscription: precisely allowed output | Expected file contents; CLI completion with returned model and session evidence |
| Real subscription: missing exact permission | Blocked before inference in about 0.21 seconds; Claude was not called |
| Real subscription: runtime permission denial | Returned needs_permission in about 4.62 seconds; denied file absent and saved resume pointer unchanged |
| Malformed trailing stream data and duplicate results | Offline regressions passed and returned failure; a valid result without a final newline still completes |

Real calls used official CLI 2.1.285 and the Claude.ai subscription. Model evidence for completed calls came from the final result's `modelUsage`. The runtime-denial early stop had no final result: model and session evidence were recorded as unavailable, without substituting the previous resume ID. Tests ran in temporary projects and changed no business project.

These small-test timings do not predict generation time for a long task. Preflight is a static check; the CLI still makes its own permission decisions. PyYAML, needed by the Python Skill checker, was not installed in the test environment. The four frontmatter blocks were checked with macOS's bundled Ruby YAML parser instead; this does not count as a successful run of the Python checker. Relative links, JSON, required resources, matching MIT copies and private material in public files were checked separately. See [permissions and failures](../../skills/claude-bridge/references/en/08-permissions-and-failures.md) for usage.

## Original packaging test baseline

These are the original packaging checks, dated 2026-10-05. At that point, the Python implementation and offline tests matched the tested baseline; the following writing update changed only documentation. These are historical results. The current program repair is covered in the section above.

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
