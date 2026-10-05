# 文档修改与开发交接

[简体中文](04-dev-handoff.md) · [English](en/04-dev-handoff.md)

Bridge 有纯咨询与标准任务两条路径。需要改文件、执行工具或验证代码时，用默认的 `--workflow standard`。纯讨论用 `consult`，它禁用本次 Claude CLI 的内置工具和 MCP 工具，只分析已提供材料。

## 把目标说具体

```text
在当前项目中，让 Claude 先规划这个问题的修复范围。
由 Codex 实现并运行项目已有的相关测试，再交给 Claude 审查。
保留现有未提交工作，完成后给我 diff、测试结果与每次 Claude 调用回执。
```

也可以只让 Claude 审查：“检查这份 diff，先不要修改。” 审查请求不单独授权范围外修复。已有明确授权足以继续的步骤无需重复询问；缺少项目、目标、修改范围或有冲突时，应先问清楚。

持续讨论中明确要求“现在把这些修改写到文件里”，可按新请求转入标准流程。任务类型变化不会自动取消当前聊天的模型选择，但原来“只讨论”的指令不能充当实际修改授权。

## 建议的开发交接顺序

1. 读取适用 `AGENTS.md`、`CLAUDE.md`、必要 `.ai/` 材料和相关代码，核对真实 Git HEAD、status、diff。
2. Claude 对已授权任务给出规划；明确待验证结论和执行边界。
3. GPT/Codex 在真实文件中执行修改，一次只允许一个 Agent 修改同一项目。
4. 运行与改动相关的确定性检查，独立核对实际文件及 diff。
5. Claude 审查指定范围；GPT 核对审查结论，处理已授权的必要问题。

可选 `dev-orchestrator` 把上述阶段组织成开发工作流。它不代替 Bridge 首配、任务授权或实际验收；无需为了普通问答安装它。模型返回成功不代表业务需求已经满足，文字中的“测试通过”也要与独立执行证据对应。

## `.ai/` 各文件的用途

| 文件 | 用途 |
| --- | --- |
| `PROJECT_CONTEXT.md` | 项目目标、约束、必要结构和常用命令 |
| `DECISIONS.md` | 已验证决策、依据和待确认事项 |
| `HANDOFF.md` | 当前工作、请求与结果交接；Bridge 备份后追加 |
| `sessions.json` | 项目 Claude 会话元数据 |
| `consult.json` | 连续咨询会话与指纹基线 |
| `requests/` | 可选私有 UTF-8 任务文件 |
| `logs/`、`backups/` | 本地运行证据及修改前备份 |

Bridge 自有状态和日志不由 Claude 手工重写。GPT 在独立核对后补充人工交接，并区分模型报告与已验证事实。现有模板中的 Unknown 或待填写内容应保留不确定性，不能写成验收完成。

Git 忽略项不能自动使内容安全。提交项目前仍检查 `.ai/` 中可提交的摘要、决定和交接文件是否含个人资料、完整任务、业务秘密或凭据；私有状态、任务文件、日志和备份不应作为公开仓库内容。

## 标准路径参数示意

以下占位符须替换为本机实际路径；不是直接可执行的安装命令：

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow standard --mode sonnet --task-file .ai/requests/current.txt --effort medium --effort-source user --effort-reason "用户指定开发阶段强度" --timeout 180
```

任务文件必须是该授权项目内的普通 UTF-8 文件，不接受符号链接或项目外路径。目录和任务文件应使用私有权限，避免把长用户文本拼进 shell 代码。`--task` 与 `--task-file` 只能选其一。

标准流程保留正常权限机制，不使用 `--dangerously-skip-permissions`。精确操作已经授权时可按现有规则处理权限；不扩大到全局通配允许。鉴权、权限、部署配置等修改按其实际影响核验。commit、push、发布、部署、费用与外发消息以已有用户授权判断，默认不自动执行。
