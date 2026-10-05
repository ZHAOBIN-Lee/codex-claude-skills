# 文档修改与开发交接

[简体中文](04-dev-handoff.md) · [English](en/04-dev-handoff.md)

Bridge 有两条路径。只讨论，用 `consult`：这次调用禁用 Claude CLI 的内置工具和 MCP 工具，只分析你提供的材料。要改文件、跑工具或验证代码，用默认的 `--workflow standard`。

## 把目标说具体

```text
在当前项目中，让 Claude 先规划这个问题的修复范围。
由 Codex 实现并运行项目已有的相关测试，再交给 Claude 审查。
保留现有未提交工作，完成后给我 diff、测试结果和每次 Claude 调用的回执。
```

也可以只让 Claude 审查：“检查这份 diff，先不要修改。”审查不等于授权顺手修复范围外的问题。已经授权的步骤不用反复确认；项目、目标、修改范围不清楚，或者要求之间有冲突，Codex 应该先问。

讨论到一半，你明确说“现在把这些修改写到文件里”，就转入标准流程。当前聊天选的 Claude 模型不会因为任务类型变了而取消，但之前那句“只讨论”也不算改文件的授权。

## 建议的开发顺序

1. 读适用的 `AGENTS.md`、`CLAUDE.md`、必要的 `.ai/` 材料和相关代码，核对真实的 Git HEAD、status 和 diff。
2. Claude 为已授权的任务做规划，写明执行边界和还需要验证的结论。
3. GPT/Codex 在真实文件里改。同一个项目一次只让一个 Agent 改。
4. 跑跟改动有关的确定性检查，独立查看实际文件和 diff。
5. Claude 审查指定范围，GPT 核对审查意见，处理已授权范围内必要的问题。

可选的 `dev-orchestrator` 把这几步串成开发工作流。它不能代替 Bridge 首配、任务授权或你自己的验收，日常问答也不用装它。模型说“成功”不等于需求满足了，文字里写的“测试通过”也要有独立执行的记录对得上。

## `.ai/` 里的文件

| 文件 | 用途 |
| --- | --- |
| `PROJECT_CONTEXT.md` | 项目目标、约束、必要的结构和常用命令 |
| `DECISIONS.md` | 已验证的决定、依据和待确认事项 |
| `HANDOFF.md` | 当前工作、请求和结果的交接；Bridge 备份后追加 |
| `sessions.json` | 项目的 Claude 会话元数据 |
| `consult.json` | 连续咨询的会话和指纹基线 |
| `requests/` | 可选的私有 UTF-8 任务文件 |
| `logs/`、`backups/` | 本地运行记录和修改前备份 |

Bridge 自己的状态和日志，Claude 不手工重写，你也别手改。GPT 独立核对之后再补人工交接，并分清哪些是模型自己报告的、哪些是已经验证的。模板里的 Unknown 或待填项，保持“不确定”，别写成已经验收。

`.gitignore` 忽略了某个文件，不代表里面的内容就安全。提交项目前，检查 `.ai/` 里准备提交的摘要、决定和交接文件，有没有个人资料、完整任务、业务秘密或凭据。私有状态、任务文件、日志和备份，不该进公开仓库。

## 标准路径的参数写法

占位符要换成你本机的实际路径。这不是能直接粘贴执行的命令：

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow standard --mode sonnet --task-file .ai/requests/current.txt --effort medium --effort-source user --effort-reason "用户指定开发阶段强度" --timeout 180
```

任务文件必须是这个授权项目里的普通 UTF-8 文件，不接受符号链接，也不接受项目外的路径。目录和文件用私有权限，长文本别直接拼进 shell 命令。`--task` 和 `--task-file` 二选一。

标准流程保留正常的权限检查，不用 `--dangerously-skip-permissions`，也不把授权放宽到全局通配。某个精确操作已经获得授权，就按现有规则处理。改鉴权、权限、部署配置时，按它实际的影响来验证。commit、push、发布、部署、费用和对外消息，以你已有的授权为准，默认不会自动做。
