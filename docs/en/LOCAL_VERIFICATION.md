# Verification record

[简体中文](../LOCAL_VERIFICATION.md) · [English](LOCAL_VERIFICATION.md)

What has been verified so far, and what hasn't.

## 2026-10-07: 0.2.0, `dev-orchestrator` on native models and sub-agents

Environment: the maintainer's macOS arm64, Codex 0.160.1, [codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin) 0.3.0, Python 3.9.

| Check | Result |
| --- | --- |
| `devflow.py` offline tests | 54/54 passed, no model calls |
| Dispatch decisions for the three execution modes | Unit tests cover whether each step runs in the current chat or a sub-agent, which model the chat must be on, and whether review is by an independent model |
| Claude chat spawning a GPT sub-agent | Tested with `codex exec`: the sub-agent ran one command and returned its output; its session's actual model was `gpt-6.1-sol` |
| GPT chat spawning a Claude sub-agent (`claude_sonnet`) | Same test; the provider receipt recorded `claude-sonnet-5-5` |
| Dependencies on the old bridge in the docs | Removed; the Skill no longer calls an external CLI |

## Not yet verified

- The full rewritten flow (plan → code → validate → review → rework) in a real project.
- An independent user going from install to a first `/dev` run on a fresh machine.
- Linux, WSL, and native Windows.
- GitHub CI.

Passing offline tests shows the dispatch logic is sound. It doesn't show that real models, sub-agents, or the desktop app behave as expected in every case.

## Legacy record

0.1.0-draft and the 2026-10-06 permission and timeout repair were for the old `claude-bridge` (relaying through the official Claude Code CLI 2.1.285). At the time the Bridge passed 136/136 offline tests and the orchestrator 48/48, with small real-subscription tests. Those records and the code are kept at the [`legacy-claude-bridge`](https://github.com/ZHAOBIN-Lee/codex-claude-skills/tree/legacy-claude-bridge) tag and don't apply to the current version.
