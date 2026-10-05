# Support and limits

[简体中文](../07-limits.md) · [English](07-limits.md)

The Skill defines how Codex calls Claude and checks the result. The bundled Python Bridge handles running things locally, the checks, session metadata, and handoffs. The text instructions work on any system. The program has requirements for the OS, the official CLI, authentication, and the Codex host's tools.

## What's been validated

| Scope | Status |
| --- | --- |
| The maintainer's existing macOS environment | Real consultations, continued sessions, and development handoffs have been run; the current receipt rules also have real-call records. Official CLI 2.1.285. Existing offline baseline: Bridge 84/84 (fake CLI), dispatcher 48/48 (task lifecycle and deterministic behavior) |
| A fresh macOS install | There's a tutorial and a packaging plan, but install, login, and routing haven't been validated on a fresh machine |
| Linux, WSL | The design is POSIX-based and should adapt, but install, permissions, paths, and real calls all still need validation |
| Native Windows | The Bridge currently uses POSIX features, so both the code and the install need adapting. Native support isn't finished |
| Help and tutorials | Codex reads the local reference files as needed and doesn't call Claude just to help. Discovery after a fresh install still needs validation |
| Team/Enterprise, API, or third-party authentication | Not supported by the current subscription checks, and there's no automatic fallback |

Claude Code supporting a platform doesn't mean this Bridge runs there. When this table is updated later, it should be backed by reproducible tests for that platform, and it should keep offline tests, real CLI calls, desktop routing, and recovery after closing the app apart.

## Models and accounts

You need your own official Claude Code login and a claude.ai Pro or Max subscription that the current Bridge checks accept. Installing the Skill doesn't give you an account, allowance, or model access. Whether Sonnet or Opus works depends on what your official CLI and account actually return.

The Bridge doesn't set up an API provider, create an API key, buy extra usage, or turn on Billing, and it won't switch to a paid API when your allowance runs out or a call fails. The record that extra usage is off comes from your own confirmation. The script doesn't read your account's Billing directly.

## Permissions and material

Installing the Skill doesn't authorize it to scan arbitrary projects, initialize `.ai/`, or send project contents. Each time it needs a clear project, task, material scope, and authorization you've already given. If any is missing, Codex asks first.

`consult` turns off built-in tools and MCP for that call and analyzes only the material you supply. For tools or file edits, use `standard`. Normal startup hooks and similar environment behavior aren't among the things switched off.

The official permission mechanism stays as it is. There's no permission-skipping flag and no global wildcard authorization. Private task files and Bridge logs stay out of public deliverables. The logs record only necessary run metadata, but that doesn't guarantee that any sensitive input is fine to publish. The official CLI manages its own native session records, separately from the Bridge's metadata logs.

## Continued use

Standing authorization comes only from your explicit statement in the current chat, and covers only the same project and topic. A cache is not authorization. Switching back to Codex, changing projects, or starting a new chat means reassessing. Two Codex chats may end up using the same project's Claude session. If you need them isolated, explicitly ask for a new session.

Resuming a session doesn't share all context. The incremental baseline covers only the defined project summaries, rules, and Git snapshot, and it doesn't read all your business files. A model saying "I remember" doesn't replace checking that the session and the actual content carried over.

## Latency and acceptance

The Skill can reduce repeated preparation once Codex starts handling a message. It can't intercept native input in the desktop app, change Codex's own effort setting, guarantee a response time, or remove the overhead of a long chat. Keep CLI wall time and end-to-end waiting apart. This version has no streaming first-token measurement.

Test results from the maintainer's machine don't show that your account, system, and install will pass as-is. After installing, the minimum check is: the Skill is discovered, the environment check passes, one real call returns a receipt, and, if you'll use continued conversations, a session-continuation test. Output that looks right also doesn't mean a release, deployment, or payment has happened.

## Provenance and license

The maintainer confirmed that the source contains no borrowed external code, so there's no code upstream to credit. This Skill is under the [MIT License](../../LICENSE), and the copyright notice is included in each installation unit. Official products such as Claude Code and Codex are covered by their own terms, and the Skill doesn't distribute accounts or official clients.
