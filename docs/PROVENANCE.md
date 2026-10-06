# 项目来源

[简体中文](PROVENANCE.md) · [English](en/PROVENANCE.md)

维护者在 2026-10-05 确认，本仓库的源码没有借用其他仓库的代码，因此没有代码上游需要登记。

当前仓库只包含 `dev-orchestrator`，从维护者自己的实现按白名单导出，再加上分发结构、说明和兼容方案。旧版 `claude-bridge` 也是维护者自己写的，保留在 `legacy-claude-bridge` tag。

`dev-orchestrator` 依赖的 [codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin) 是另一个仓库：它基于 Andrii Shafar 的 [Reidond/codex-claude-models-plugin](https://github.com/Reidond/codex-claude-models-plugin)（MIT）修改而来，署名和许可在那个仓库里。本仓库不包含它的代码，只在说明里要求先安装它。

文档的介绍方式和示例安排参考了 [Anthropic Skills](https://github.com/anthropics/skills)、[Vercel Agent Skills](https://github.com/vercel-labs/agent-skills)、[Superpowers](https://github.com/obra/superpowers) 和[宝玉 Skills](https://github.com/JimLiu/baoyu-skills)。只借鉴写法，没有复制它们的原文。

外部依赖见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)，许可见 [LICENSING.md](../LICENSING.md)。
