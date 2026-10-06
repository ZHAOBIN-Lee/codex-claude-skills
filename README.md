# Codex Claude Skills

[简体中文](README.md) · [English](README.en.md)

让 Claude 写方案、GPT 写代码、Claude 再检查。`dev-orchestrator` 把一个开发任务拆成几步交给不同模型，状态记在项目的 `.ai/` 目录里，验证命令由调度器亲自运行，不采信模型自己说的“通过”。

它只用 Codex 原生的模型和子代理，所以需要 Claude 和 GPT 出现在同一个 Codex 模型菜单里。这一步由 [codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin) 完成，请先装好它。

这是社区项目，与 Anthropic、OpenAI 没有隶属关系，采用 [MIT 许可](LICENSE)。

> **0.2.0 公开预览。** 目前只在维护者的 macOS 上用过。旧版 `claude-bridge`（通过 Claude Code CLI 转发）已停止维护，最后的版本保留在 [`legacy-claude-bridge`](https://github.com/ZHAOBIN-Lee/codex-claude-skills/tree/legacy-claude-bridge) tag。

## 快速开始

你需要：

- 已经装好 [codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin)，模型菜单里能同时选 GPT 和 Claude。
- Codex 已开启多代理（`config.toml` 里 `[features]` 的 `multi_agent = true`），并有 `claude_opus`、`claude_sonnet` 这类 Claude 子代理角色（Provider 安装时会生成）。
- Python 3.9 或更新版本。

在 Codex 里发送这句话安装：

```text
$skill-installer 从 https://github.com/ZHAOBIN-Lee/codex-claude-skills 安装 skills/dev-orchestrator。若已安装同名 Skill，先比较并备份。
```

装完先问它怎么用，这一句不会开始任何开发：

```text
$dev-orchestrator 这个工作流怎么用？先不要开始。
```

## 一个真实请求

在模型菜单选 Claude，然后说：

```text
在 /path/to/project 里，按开发工作流实现“导出 CSV”功能。保留现有的未提交改动。
```

强模型就是当前聊天选的 Claude，不会再问你。开跑前只问一件事：用哪种执行模式。

| 模式 | 写方案 | 写代码 | 检查 |
| --- | --- | --- | --- |
| Claude 指派 GPT 子代理 | 当前 Claude 聊天 | GPT 子代理 | Claude 自己验证和审查，有问题写返工任务，再派 GPT 去改 |
| 切换到 GPT 执行 | Claude | 你在模型菜单切到 GPT，由 GPT 写 | GPT 写完派 Claude 子代理只读审查 |
| 直接用 Claude 执行 | Claude | Claude | 派一个新上下文的 Claude 子代理审查，汇报里写明“同一模型家族审查” |

第一种适合连续开发：Claude 一直检查，GPT 一直干活，全程不用切模型。写方案只在 Claude 聊天里做；当前聊天的模型和下一步需要的不一致时，工作流会停下来提醒你切换。

之后回来接着做，说“按开发工作流继续”。只想看进度，说 `/dev status`，这一步不调用模型。

## 常用说法

| 说法 | 作用 |
| --- | --- |
| `按开发工作流实现 <需求>` / `/dev new` | 新需求：写方案、拆任务，然后自动推进到停止点 |
| `按开发工作流继续` / `/dev continue` | 只做下一步 |
| `/dev run` | 在次数上限内连续推进 |
| `/dev status` | 只读进度，不调用模型 |
| `/dev plan` | 只写方案，不执行 |
| `/dev review` | 直接审查当前任务或 diff |
| `/dev resolve` | 任务卡住时，让 Claude 找根因 |

## 什么时候会停

缺少业务决策、需求和仓库现状矛盾、工作区有处理不了的冲突、模型或子代理不可用、当前聊天模型不对、验证命令跑不起来、任务或返工次数到上限，或者你说停。高风险或不可逆的操作按你实际授权的范围判断，不会为了继续推进而绕过权限检查，也不会悄悄用 GPT 顶替 Claude 那一步。

## 验证状态

- 调度脚本 `devflow.py` 54 项离线测试通过（`python3 -m unittest discover -s skills/dev-orchestrator/tests`）。
- 子代理已实测：Claude 聊天派出的 GPT 子代理、GPT 聊天派出的 Claude 子代理，各执行了一条命令，实际模型与请求一致。
- 还没有在独立用户的机器上验证，也没有覆盖 Linux 和 Windows。改造后的完整多任务流程还没有在真实项目里跑过。

逐项记录见[本地检查记录](docs/LOCAL_VERIFICATION.md)。

## 文档

- [Skill 说明](skills/dev-orchestrator/SKILL.md)（中文，约束性规则）与[英文指南](skills/dev-orchestrator/references/guide.en.md)
- [兼容方案](docs/COMPATIBILITY.md)、[本地检查记录](docs/LOCAL_VERIFICATION.md)、[发布清单](docs/RELEASE_CHECKLIST.md)
- [许可](LICENSING.md)、[来源说明](docs/PROVENANCE.md)、[外部依赖](THIRD_PARTY_NOTICES.md)
- [贡献说明](CONTRIBUTING.md)、[隐私与问题报告](SECURITY.md)、[变更记录](CHANGELOG.md)
