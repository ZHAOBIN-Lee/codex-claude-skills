# Codex Claude Skills

[简体中文](README.md) · [English](README.en.md)

让 Codex 在同一项目中调用官方 Claude Code，支持连续咨询、开发交接和可核对的模型回执。

Community draft for calling the official Claude Code CLI from Codex. This is not an official Anthropic or OpenAI project.

**当前状态：0.1.0-draft 公开预览草稿，采用 [MIT 许可](LICENSE)，尚未发布稳定版。维护者已确认本项目未借鉴其他仓库。**

仓库：[ZHAOBIN-Lee/codex-claude-skills](https://github.com/ZHAOBIN-Lee/codex-claude-skills)。当前已完成 macOS 离线检查；新机器首配和跨平台真实调用仍需验证。

## 安装后直接问怎么用

核心可安装单元是 `skills/claude-bridge/`。它包含说明、运行脚本、模板和教程，不依赖作者电脑的目录，也不依赖仓库根目录中的文档。

安装后可以在 Codex 中说：

```text
$claude-bridge 这个 Skill 怎么用？先给我入门教程。
$claude-bridge 帮我检查首次设置需要什么，先不调用 Claude。
$claude-bridge 我想连续用 Claude 讨论一个项目，怎么开始和切回 Codex？
```

帮助模式读取随 Skill 安装的教程，不调用 Claude。Codex 本身仍有正常用量，不能把这描述成所有模型都免费。

## 它能做什么

| 场景 | 用法 | 说明 |
| --- | --- | --- |
| 一次咨询 | “让 Claude Sonnet 看这个问题” | 纯分析用 consult，明确项目和材料范围 |
| 连续对话 | “这个项目接下来用 Claude Sonnet，medium，直到我说切回 Codex” | 当前聊天的明确授权；后续恢复同一项目的 Claude 会话 |
| 核对真实模型 | “附实际模型和调用凭证” | 每次调用默认给实际模型、完整会话 ID、状态及对应证据 |
| 文件修改与审查 | “让 Claude 检查这个项目的 diff” | 用 standard，保留正常权限，Codex 独立核对结果 |
| 开发工作流 | 可选安装 `dev-orchestrator` | 实验组件：Claude 规划／审查，原生 GPT 执行，工具验证 |

Codex 聊天仍使用其原生模型。这里没有把 Claude 接入原生模型菜单，也不共享两边的隐藏推理。`@claude` 等写法是 Skill 理解的语义约定。

## 获取与安装

**当前可安装的是公开预览草稿，请先阅读平台与验证状态。**

在 Codex 中发送：

```text
$skill-installer 从 https://github.com/ZHAOBIN-Lee/codex-claude-skills 安装 skills/claude-bridge，使用 main 分支的预览草稿。若已安装同名 Skill，先比较并备份。
```

安装整个 Skill 目录，不能只下载 `SKILL.md`。安装器若提示重新启动 Codex 才能发现新 Skill，按提示操作；安装之后先询问入门教程和首次设置，不直接开始真实调用。当前没有稳定版 tag；未来正式版本应固定 tag 或提交，避免默认追随变动中的 main。

本地预览只需打开 [Skill 说明](skills/claude-bridge/SKILL.md) 和 [5 分钟导览](skills/claude-bridge/references/00-tour.md)。若要在另一环境安装，先按 [首配说明](skills/claude-bridge/references/01-setup.md) 完成独立配置；遇到已安装的同名 Skill，先比较与备份，不覆盖作者当前正在使用的版本。

朋友需要自行安装并登录官方 Claude Code，配置自己的 CLI 路径、版本和完整性证据，并确认自己账户的费用设置。仓库不包含 Claude 二进制、账号、密钥、作者费用确认或运行状态。官方安装方式见 [Claude Code 设置文档](https://code.claude.com/docs/en/setup)。

## 配置与状态

- 共享偏好示例：[preferences.example.json](skills/claude-bridge/templates/preferences.example.json)。默认建议是 Sonnet、medium，具体任务和用户明确选择优先。
- 本机运行配置示例：[runtime.example.json](skills/claude-bridge/templates/runtime.example.json)。初始费用状态为未确认，不能直接用于真实调用。
- 用户配置放在 Skill 安装目录之外；每次调用显式传 `--runtime`。升级 Skill 时保留个人配置。
- 项目 `.ai/` 管理交接、会话、增量基线与日志。安装 Skill、配置默认值或缓存存在，都不等于授权调用模型。

这些偏好目前由 Skill 读取并遵循，不是 Bridge 自动解析的一套新参数，也不能改变 Codex 原生模型或强度。

## 平台与验证状态

| 部分 | macOS | Linux／WSL | Windows 原生 |
| --- | --- | --- | --- |
| Skill 文字与教程 | 可共用 | 可共用 | 可共用 |
| 当前桥接代码基线 | 原作者环境实测 | 需独立验证 | POSIX 锁／进程等尚需适配 |
| 这份重新打包的草稿 | 见本轮本地验收记录 | 尚未实测 | 尚未实测，不声称可运行 |

目标是同一套 Skill 和教程、按系统适配执行层。官方 Claude Code 支持多个系统，不代表这段桥接脚本已自动兼容所有系统。平台适配清单见 [兼容方案](docs/COMPATIBILITY.md)。

## 教程

教程随 Skill 一起安装，Codex 可以按需读取：

每篇提供中文与英文版本；英文目录位于 [references/en/](skills/claude-bridge/references/en/00-tour.md)。可以直接要求 Codex 用中文或英文介绍。

1. [5 分钟导览](skills/claude-bridge/references/00-tour.md)
2. [首次设置](skills/claude-bridge/references/01-setup.md)
3. [连续对话与切回](skills/claude-bridge/references/02-conversation.md)
4. [模型、强度和回执](skills/claude-bridge/references/03-models-effort-receipt.md)
5. [开发交接](skills/claude-bridge/references/04-dev-handoff.md)
6. [失败排查](skills/claude-bridge/references/05-troubleshooting.md)
7. [升级与卸载](skills/claude-bridge/references/06-update-uninstall.md)
8. [已知限制](skills/claude-bridge/references/07-limits.md)

## 维护与发布

- [来源与许可核查](docs/PROVENANCE.md)
- [第三方声明](THIRD_PARTY_NOTICES.md)
- [许可状态](LICENSING.md)
- [发布与朋友试用清单](docs/RELEASE_CHECKLIST.md)
- [本轮本地检查记录](docs/LOCAL_VERIFICATION.md)
- [贡献说明](CONTRIBUTING.md)
- [隐私与问题报告](SECURITY.md)

当前仓库按维护者授权直接公开为预览草稿，未发布稳定版、未完成独立朋友或跨平台验收。公开包仅包含审查过的源码、离线测试、通用模板和教程。后续提交仍需核查文件、Git 历史及 Actions 日志；公开后的 fork 和已有副本不会因改回私有而自动收回。[GitHub 可见性说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
