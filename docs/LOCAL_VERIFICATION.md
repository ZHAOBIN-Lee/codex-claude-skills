# 验证记录

[简体中文](LOCAL_VERIFICATION.md) · [English](en/LOCAL_VERIFICATION.md)

这页记录目前验证到哪一步，哪些还没做。

## 2026-10-07：0.2.0，`dev-orchestrator` 改走原生模型与子代理

环境：维护者的 macOS arm64，Codex 0.160.1，[codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin) 0.3.0，Python 3.9。

| 检查 | 结果 |
| --- | --- |
| `devflow.py` 离线测试 | 54/54 通过，不调用模型 |
| 三种执行模式的派发判断 | 单元测试覆盖：每一步在当前聊天还是子代理执行、需要哪一侧模型、审查是否为独立模型 |
| Claude 聊天派 GPT 子代理 | 用 `codex exec` 实测，子代理执行一条命令并返回结果，子代理会话的实际模型为 `gpt-6.1-sol` |
| GPT 聊天派 Claude 子代理（`claude_sonnet`） | 同上，Provider 凭证记录的实际模型为 `claude-sonnet-5-5` |
| 文档中的旧桥梁依赖 | 已移除；Skill 不再调用外部 CLI |

## 还没做的验证

- 改造后的完整流程（写方案 → 写代码 → 验证 → 审查 → 返工）还没有在真实项目里跑过。
- 独立用户在新机器上从安装到第一次 `/dev` 的流程。
- Linux、WSL 和 Windows 原生。
- GitHub CI。

离线测试通过只说明调度逻辑没问题，不代表真实模型、子代理或桌面端在所有情况下都能按预期工作。

## 旧版记录

0.1.0-draft 和 2026-10-06 的权限与超时修复都是针对旧版 `claude-bridge`（通过官方 Claude Code CLI 2.1.285 转发）做的，当时 Bridge 离线测试 136/136、调度器 48/48 通过，并用真实订阅做过小范围测试。这些记录和对应代码保留在 [`legacy-claude-bridge`](https://github.com/ZHAOBIN-Lee/codex-claude-skills/tree/legacy-claude-bridge) tag，不适用于当前版本。
