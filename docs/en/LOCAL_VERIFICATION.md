# Local preview checks

[简体中文](../LOCAL_VERIFICATION.md) · [English](LOCAL_VERIFICATION.md)

Date: 2026-10-05. These are local packaging and instruction checks, not proof of a fresh desktop installation or cross-platform acceptance.

| Check | Result | Boundary |
| --- | --- | --- |
| Repackaged Bridge offline tests | 84/84 passed, 49.465 seconds | Fake CLI, no actual model calls |
| Optional orchestrator offline tests | 48/48 passed, 0.447 seconds | Task lifecycle and deterministic behavior |
| Two Skill-format checks | Passed | Frontmatter and naming |
| Core Skill copied alone | Passed | Not installed into a global Skill directory |
| Independent Python entry and init | Passed; init `inference=false` | Resources located; no inference |
| Eight Chinese tutorials and relative links | Present; links checked | Fresh-chat automatic routing not claimed |
| Personal-path and runtime-material review | Passed | No author paths, real sessions, personal runtime, installation records, logs, or backups |
| Six help/setup/call scenarios | Independent instruction review passed | Not desktop routing tests |
| Real Claude planning consultation | Completed, official result Sonnet 5.5 | Existing Bridge used; not a fresh-machine setup of this preview |

Source was exported after removing personal configuration and state. The existing installation was preserved. Distribution instructions add help routing and portable-entry guidance; example cost settings begin unconfirmed.

Earlier documentation issues were corrected: stale upstream-investigation wording, Python minimum, and missing consultation-state ignore entries. The publication update adds Chinese and English documentation and MIT notices. The Python implementations and offline test files retain the hashes of the tested baseline, so the earlier test results are not represented as a newly repeated run. Publication checks validate new links, JSON, required resources, license copies, and the upload allowlist.

Still pending: actual GitHub Skill-installer acceptance, native-Windows execution, Linux/WSL real calls, a complete executable personal-runtime setup utility, full upgrade/removal acceptance, independent-friend testing, and GitHub CI. Public visibility and uploaded-file checks are publication checks, not those runtime acceptance tests.
