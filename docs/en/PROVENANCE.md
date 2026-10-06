# Project provenance

[简体中文](../PROVENANCE.md) · [English](PROVENANCE.md)

On 2026-10-05 the maintainer confirmed that this repository's source contains no code borrowed from other repositories, so there is no code upstream to list.

The repository now ships only `dev-orchestrator`, exported by allowlist from the maintainer's own implementation, plus the distribution layout, docs and compatibility plan. The old `claude-bridge` was also the maintainer's own work and is kept at the `legacy-claude-bridge` tag.

[codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin), which `dev-orchestrator` depends on, is a separate repository. It is a modified version of Andrii Shafar's [Reidond/codex-claude-models-plugin](https://github.com/Reidond/codex-claude-models-plugin) (MIT), with attribution and license in that repository. None of its code is included here; the docs only ask you to install it first.

The documentation's introductions and examples take writing cues from [Anthropic Skills](https://github.com/anthropics/skills), [Vercel Agent Skills](https://github.com/vercel-labs/agent-skills), [Superpowers](https://github.com/obra/superpowers), and [Baoyu Skills](https://github.com/JimLiu/baoyu-skills). No passages were copied from them.

External dependencies are in [third-party notices](../../THIRD_PARTY_NOTICES.en.md), and the license is in [licensing](../../LICENSING.en.md).
