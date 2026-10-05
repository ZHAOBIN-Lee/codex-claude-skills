# Support and limits

[简体中文](../07-limits.md) · [English](07-limits.md)

The Skill defines how Codex calls and verifies Claude. The Python Bridge handles local execution, checks, session metadata, and handoffs. Text instructions are portable; execution has OS, official-CLI, authentication, and host-tool requirements.

## Current validation scope

| Scope | Status |
| --- | --- |
| Author's existing macOS environment | Real consultation, session continuation, and development-handoff evidence; the current receipt rule also has real-call evidence |
| Fresh macOS installation | Draft tutorial and packaging checks, not acceptance of every machine's login or routing |
| Linux / WSL | POSIX design can be adapted; installation, permissions, paths, and real calls still need validation |
| Native Windows | POSIX features require code and setup adaptation; no completed native support claim |
| Help and tutorials | Codex reads local references as needed without automatically calling Claude; new-install discovery still needs acceptance |
| Team / Enterprise, API, or third-party authentication | Not supported by the current subscription checks; no automatic fallback |

Claude Code's supported platforms do not prove this Bridge runs on each one. Update support with reproducible platform-specific checks and distinguish offline tests, real CLI calls, desktop routing, and recovery after app closure.

## Models and accounts

Each user needs their own official Claude Code login and a Claude.ai Pro/Max subscription accepted by the current Bridge checks. Installing a Skill provides no account, allowance, or model entitlement. Sonnet/Opus availability depends on the actual account and official response.

The Bridge does not create an API provider or key, buy usage credits, enable Billing, or switch to a paid API after limits or failures. Disabled-extra-usage records are user confirmations, not a guarantee of directly reading Billing.

## Permissions and material

A global installation does not authorize scanning arbitrary projects, initializing `.ai/`, or sending project contents. Use explicit project, task, material scope, and existing user authorization; clarify missing information.

Pure `consult` disables built-in and MCP tools for that call and analyzes supplied material. Use `standard` for tools or modifications. Do not claim all normal startup hooks and environment behavior are disabled.

Keep official permission checks. Do not skip permissions or use global wildcard authorization. Private task files and Bridge logs do not belong in public deliverables; log hygiene cannot make arbitrary sensitive inputs safe to publish. Official native sessions are managed by the official CLI, separately from Bridge metadata logs.

## Continued use

Continuing authorization comes from the user in the current chat and is limited to the project and topic. A cache is not permission. Reassess when switching back, changing project, or starting a new chat. Two Codex chats may share the same project's Claude session; request a new session explicitly when isolation is needed.

Resumption does not share all context. Incremental baselines cover prescribed summaries, rules, and Git snapshots, not all business files. A model saying "I remember" does not replace session and content-continuation evidence.

## Latency and acceptance

The Skill can reduce repeated preparation after Codex begins processing. It cannot intercept desktop input, change Codex's native effort, guarantee a response time, or eliminate long-chat overhead. Distinguish CLI wall time from end-to-end waiting. This version provides no streaming first-token measurement.

Results on the author's machine do not prove a friend's account, system, and installation work. Minimal acceptance covers Skill discovery, environment checks, a real-call receipt, and session continuation if needed. Correct output does not prove publication, deployment, payment, or other external acceptance.

## Provenance and license

The maintainer confirmed no borrowed sources. No external upstream citation is required on that basis. This Skill is distributed under the [MIT License](../../LICENSE), with the notice retained in each installation unit. Official Claude Code, Codex, and other dependencies keep their own terms; accounts and official clients are not bundled.
