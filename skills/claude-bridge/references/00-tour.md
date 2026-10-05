# 从这里开始

[简体中文](00-tour.md) · [English](en/00-tour.md)

Claude Bridge 让 Codex 按你的请求调用本机官方 Claude Code，再把结果带回当前聊天。Codex 主模型负责调度和核对；Claude 处理明确交给它的部分。

安装后，你可以直接问：

```text
$claude-bridge 先教我怎么用，不要实际调用 Claude。
```

这是普通帮助请求。Codex 应按需读取本目录教程，解释用法；不会仅为了回答“怎么用”而调用 Claude。尚未安装、尚未配置或尚未验证的部分应说清楚。

## 常见用法

| 你想做什么 | 可以怎么说 | 接下来发生什么 |
| --- | --- | --- |
| 先了解配置 | “检查我还缺什么，先不要实际调用。” | 读取安装信息，必要时用 `doctor` 检查环境；不会产生成功模型回执 |
| 请 Claude 回答一个问题 | “在这个项目里，用 Claude Sonnet、medium，分析这份方案；只讨论。” | 提供必要材料，走 `consult`，返回建议和本轮回执 |
| 连续讨论 | “在当前项目、这个话题里，接下来一直用 Claude Sonnet、medium，直到我说切回 Codex。” | 当前聊天中的相关追问沿用选择；项目 Claude 会话可恢复 |
| 执行开发任务 | “让 Claude 规划这个修改，再由 Codex 实现和测试，最后交给 Claude 审查。” | 按实际授权进入标准开发交接；可选配 `dev-orchestrator` |

这里的 Sonnet、medium 是便于入门的参数建议，不是自动建立的持续授权。你可以明确选择其他支持的模型和强度。

## 推荐的第一轮

先选一个允许创建 `.ai/` 的测试项目，告诉 Codex：

```text
$claude-bridge 帮我完成这个测试项目的首次配置。
可以在该项目创建必要的 .ai/ 交接文件。
先检查官方 Claude Code 和我的订阅登录；不要读取或保存账号秘密。
准备好后，用 Claude Sonnet、medium 回答一个短问题，并给我实际模型回执。
```

如果项目路径、发送材料或账号费用设置不清楚，Codex 应先询问缺失信息。首配后，可在同一项目连续追问；正常使用不需要每轮重新安装、初始化或运行 `doctor`。

## 按需阅读

- 首次安装与本机配置：[01-setup.md](01-setup.md)
- 连续对话与会话恢复：[02-conversation.md](02-conversation.md)
- 模型、强度、实际调用回执：[03-models-effort-receipt.md](03-models-effort-receipt.md)
- 文档修改与开发交接：[04-dev-handoff.md](04-dev-handoff.md)
- 调用失败与等待时间：[05-troubleshooting.md](05-troubleshooting.md)
- 升级、备份与卸载：[06-update-uninstall.md](06-update-uninstall.md)
- 支持范围与限制：[07-limits.md](07-limits.md)

这份仓库是发布草稿。现有 Bridge 在作者的 macOS 环境做过真实调用验证；新机器安装、Linux、WSL 和 Windows 原生路线需分别验收。Skill 规则可以移植，不等于附带程序已经在所有系统实测。
