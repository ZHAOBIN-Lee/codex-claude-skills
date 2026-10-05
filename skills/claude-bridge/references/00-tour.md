# 从这里开始

[简体中文](00-tour.md) · [English](en/00-tour.md)

Claude Bridge 让你在 Codex 里直接请 Claude 看问题。Codex 通过你本机的官方 Claude Code 把问题交给 Claude，再把回答带回当前聊天。Codex 还是原生 GPT，负责调度和核对；Claude 只处理你交给它的部分。

装好以后，先问它怎么用：

```text
$claude-bridge 先教我怎么用，不要实际调用 Claude。
```

这是普通的帮助请求，Codex 读本目录的教程来回答，不会调用 Claude。哪些东西还没装、没配、没验证，它也应该直说。

## 常见用法

| 你想做什么 | 可以这样说 | 接下来 |
| --- | --- | --- |
| 看还缺什么 | “检查我还缺什么，先不要实际调用。” | 读安装信息，需要时跑 `doctor`。不会产生模型回执 |
| 问 Claude 一个问题 | “在这个项目里，用 Claude Sonnet、medium，分析这份方案，只讨论。” | 走 `consult`，返回建议和这次的回执 |
| 连续讨论 | “在当前项目、这个话题里，接下来一直用 Claude Sonnet、medium，直到我说切回 Codex。” | 当前聊天里的追问沿用这个选择，并请求恢复项目的 Claude 会话 |
| 做开发任务 | “让 Claude 规划这个修改，Codex 实现并测试，最后交给 Claude 审查。” | 走标准开发交接，可以配合 `dev-orchestrator` |

Sonnet、medium 是方便上手的默认建议，不会自动变成长期授权。你可以随时点名别的模型和强度。

## 第一次试用

找一个允许创建 `.ai/` 的测试项目，对 Codex 说：

```text
$claude-bridge 帮我完成这个测试项目的首次配置。
可以在该项目创建必要的 .ai/ 交接文件。
先检查官方 Claude Code 和我的订阅登录，不要读取或保存账号秘密。
准备好后，用 Claude Sonnet、medium 回答一个短问题，并给我实际模型回执。
```

项目路径、要发送的材料、费用设置有哪项不清楚，Codex 会先问你。首次设置完成后，同一个项目里可以直接追问，不用每次重新安装、初始化或跑 `doctor`。

## 接着看哪篇

- 首次安装和本机配置：[01-setup.md](01-setup.md)
- 连续对话和会话恢复：[02-conversation.md](02-conversation.md)
- 模型、强度和调用回执：[03-models-effort-receipt.md](03-models-effort-receipt.md)
- 改文件和开发交接：[04-dev-handoff.md](04-dev-handoff.md)
- 调用失败和等待时间：[05-troubleshooting.md](05-troubleshooting.md)
- 升级、备份和卸载：[06-update-uninstall.md](06-update-uninstall.md)
- 支持范围和限制：[07-limits.md](07-limits.md)

这是公开预览。附带的 Bridge 在维护者的 macOS 上做过真实调用；新机器安装、Linux、WSL、Windows 原生还没有验证。Skill 的文字说明各系统通用，但附带的程序要分别验证，详见[限制](07-limits.md)。
