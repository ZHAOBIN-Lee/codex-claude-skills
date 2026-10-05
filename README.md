# Codex Claude Skills

[简体中文](README.md) · [English](README.en.md)

在 Codex 里遇到一个拿不准的方案、一份要复查的 diff、一个卡了很久的 bug，想让 Claude 也看一眼。常规做法是把材料复制到 Claude 的客户端，等它回答，再把结果贴回 Codex。来回几次，上下文就乱了。

`claude-bridge` 这个 Skill 帮你省掉搬运。你在 Codex 里说一句话，Codex 通过你本机已登录的官方 Claude Code CLI 把问题交给 Claude，再把回答带回当前聊天。想接着聊，直接追问。每次调用都会附一条回执：这次实际用了哪个模型、会话编号是什么、调用成功没有。你不用相信“Claude 说它是 Sonnet”，可以自己对。

Codex 本身还是原生 GPT。Claude 只在你要求的时候被调用。

这是社区项目，与 Anthropic、OpenAI 没有隶属关系，采用 [MIT 许可](LICENSE)。

> **0.1.0-draft 公开预览，尚无稳定版。** 目前在维护者的 macOS 上验证过。其他环境的进展见[平台与验证状态](#平台与验证状态)。

## 快速开始

你需要：

- 能加载 Skill 的 Codex。
- 本机的官方 Claude Code CLI，用你自己的 claude.ai Pro 或 Max 订阅登录。安装和登录见[官方设置文档](https://code.claude.com/docs/en/setup)。
- Python 3.9 或更新版本。

在 Codex 里发送这句话，安装整个 `skills/claude-bridge/` 目录：

```text
$skill-installer 从 https://github.com/ZHAOBIN-Lee/codex-claude-skills 安装 skills/claude-bridge，使用 main 分支的预览草稿。若已安装同名 Skill，先比较并备份。
```

装完（如果安装器提示重启 Codex，就按提示做），先别急着调用 Claude，问一下它怎么用：

```text
$claude-bridge 这个 Skill 怎么用？先给我入门教程。
$claude-bridge 帮我检查首次设置需要什么，先不调用 Claude。
```

这两句只读本地教程，不会调用 Claude。

首次设置要为你自己的官方 CLI 写一份 runtime 配置（CLI 路径、版本、SHA-256，格式参考 [runtime.example.json](skills/claude-bridge/templates/runtime.example.json)），放在 Skill 目录之外，调用时用 `--runtime` 指定。你还要自己检查账号，确认额外 usage credits 已关闭，再记进配置；示例里的费用状态是“未确认”，在你确认之前真实调用会被拦下。这两件事每个人都要自己做，不能照抄作者的。步骤在[首次设置](skills/claude-bridge/references/01-setup.md)，也可以直接让 Codex 带你走。默认偏好见 [preferences.example.json](skills/claude-bridge/templates/preferences.example.json)。

## 一个真实请求

设置好之后，在项目里这样问：

```text
在当前项目里，用 Claude Sonnet、medium，看看 docs/plan.md 这份方案有什么漏洞。只讨论，不改文件。
```

Codex 会先说明用哪个模型和强度，把需要的材料交给 Claude，然后把建议带回来，末尾附上这样一条回执：

```text
Claude 回执：实际模型 <本次 actual_models>｜会话 <完整 session_id>｜状态 <status>｜凭证 <本次日志链接>
```

尖括号是字段占位符，每次调用都由那次的真实返回填入。

想接着讨论，可以一次说清楚：

```text
接下来一直用 Claude Sonnet、medium 讨论这个方案，直到我说切回 Codex。
```

之后在当前聊天里说“继续，把第二点展开”就行。说“切回 Codex”就停。换项目或开新聊天，需要重新说。

## 能做什么

| 场景 | 可以这样说 | 实际走的路径 |
| --- | --- | --- |
| 问一个问题 | “让 Claude Sonnet 看这个问题” | `consult`：只分析你提供的材料，本次不开放工具和 MCP |
| 连续讨论 | “这个项目接下来用 Claude，直到我说切回 Codex” | 请求恢复项目的 Claude 会话；`consult` 成功恢复且基线有效时，只补充变化的内容 |
| 核对模型 | “附实际模型和调用凭证” | 每次调用默认都附 |
| 改文件、审 diff | “让 Claude 检查这个项目的 diff” | `standard`：保留正常权限，Codex 再独立核对结果 |
| 开发工作流（可选） | 安装 `dev-orchestrator` | 实验性：Claude 规划和审查，原生 GPT 执行，脚本检查推进状态 |

默认建议 Sonnet、medium，这是 Skill 遵循的偏好。你点名其他模型或强度，以你的为准。

## 平台与验证状态

| | macOS | Linux / WSL | Windows 原生 |
| --- | --- | --- | --- |
| Skill 文字和教程 | 可共用 | 可共用 | 可共用 |
| 附带的 Bridge 程序 | 维护者环境实测过 | 待验证 | 需要适配（用到 POSIX 锁和进程管理） |

维护者的 macOS 环境用官方 CLI 2.1.285。2026-10-06 的权限与超时修复通过 Bridge 136/136、调度器 48/48 离线测试，也用真实订阅检查了允许写入、缺权限时调用前拦截、运行时拒绝早停。目前没有稳定版 tag 或 Release。

还没做的验证：朋友独立安装、新机器上的 Codex 安装、Linux/WSL 真实调用、Windows 原生、GitHub CI。Team、Enterprise、Console API 和第三方 Provider 没有适配。

逐项清单见[本地检查记录](docs/LOCAL_VERIFICATION.md)和[兼容方案](docs/COMPATIBILITY.md)。

## 教程

教程随 Skill 一起安装，Codex 可以按需读取，也可以直接要求它用中文或英文讲。英文版在 [references/en/](skills/claude-bridge/references/en/00-tour.md)。

1. [5 分钟导览](skills/claude-bridge/references/00-tour.md)
2. [首次设置](skills/claude-bridge/references/01-setup.md)
3. [连续对话与切回](skills/claude-bridge/references/02-conversation.md)
4. [模型、强度和回执](skills/claude-bridge/references/03-models-effort-receipt.md)
5. [开发交接](skills/claude-bridge/references/04-dev-handoff.md)
6. [失败排查](skills/claude-bridge/references/05-troubleshooting.md)
7. [升级与卸载](skills/claude-bridge/references/06-update-uninstall.md)
8. [已知限制](skills/claude-bridge/references/07-limits.md)
9. [写文件的权限与失败处理](skills/claude-bridge/references/08-permissions-and-failures.md)

只想先看看再决定装不装，打开 [Skill 说明](skills/claude-bridge/SKILL.md)和上面的导览就够了。

## 其他文档

- [兼容方案](docs/COMPATIBILITY.md)：各平台还要做什么适配
- [本地检查记录](docs/LOCAL_VERIFICATION.md)
- [发布与朋友试用清单](docs/RELEASE_CHECKLIST.md)
- [许可](LICENSING.md)、[来源说明](docs/PROVENANCE.md)、[外部依赖](THIRD_PARTY_NOTICES.md)
- [贡献说明](CONTRIBUTING.md)、[隐私与问题报告](SECURITY.md)、[变更记录](CHANGELOG.md)

仓库包含源码、离线测试、通用模板和教程。Claude Code 和账号由你自行准备，个人配置与运行状态留在自己的机器上。
