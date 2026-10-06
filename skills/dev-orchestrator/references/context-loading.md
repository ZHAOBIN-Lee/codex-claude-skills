# Context loading（Retrieve, don't preload）

## 层级
| 层 | 内容 | 何时 |
| --- | --- | --- |
| L1 | `STATE.yaml`、`HANDOFF.md` 最新记录、当前 Task | 每个角色都先读 |
| L2 | `MASTER_PLAN` 相关部分、`ARCHITECTURE` 相关小节、`DECISIONS` 相关 ADR | 按 Task 引用 |
| L3 | Task Context 列出的源码、直接依赖、相关测试 | Executor/Reviewer |
| L4 | 搜索全库、扫其他模块、读历史实现 | 仅在 L1-L3 不足且说明理由 |

## 给各角色的最小上下文
- Architect：L1 + `PROJECT_CONTEXT` + `MASTER_PLAN` + 与需求相关的 L2/L3，L4 仅在需要核实现状时。
- Executor：L1 + Task 的 Context 与 Scope 文件。
- Reviewer：Task + **Task 范围内的 diff** + `VALIDATION.md` + 相关 ARCHITECTURE 小节与 ADR + `BLOCKERS.md`。
- Validator：只需要 Task 的 Validation 命令。

## 派子代理时任务文本怎么写
子代理用 `fork_turns: "none"` 启动，看不到当前聊天，任务文本必须自包含：

- 项目绝对路径；要先读的**项目内**文件路径（STATE、当前 Task、相关 ARCHITECTURE 小节、需要审查的 diff 范围或基线）。子代理用 Codex 工具自己读，不要把大段源码贴进任务文本。
- 内嵌技能规范（技能文件在项目外，由调度器读取后放进任务文本）：
  - Architect：`roles/architect.md`、`references/task-schema.md`、`templates/TASK.md`。
  - Executor：`roles/executor.md`；需要偏差判定时附上相关升级规则。
  - Reviewer：`roles/reviewer.md`、`references/review-policy.md`，以及创建返工任务所需的 `references/task-schema.md` 与 `templates/TASK.md`。
- 写明“下面的角色说明与任务规范已内嵌；其中技能相对路径仅用于标识，不是待读文件。只读取本项目内列出的材料。”
- 写明可写与不可写的文件，以及“工作区共享，不回退别人的改动”。
- 要求按角色文件的“返回”格式给出结构化结果。

在当前聊天自己做某个角色时，同样只读该角色需要的材料，不把整个聊天历史当成上下文依据。

## 压缩策略（保持文件可被小上下文读完）
- `HANDOFF.md`：只保留最新一个 Task 的完整记录；更早的合并为 `PROGRESS.md` 一行（时间、Task、结论、证据）。
- `PROGRESS.md`：只追加，一行一步。
- `DECISIONS.md`：ADR 不删；被取代的标 `Superseded by ADR-NNN`，Task 只引用编号。
- `ARCHITECTURE.md`：用稳定 `##` 小节，Task 引用 `ARCHITECTURE.md#小节名`，角色只读该小节。
- `MASTER_PLAN.md`：完成的里程碑折叠为一行摘要。
- 超过 `max_tasks_per_run` 或上下文明显变长时，先写好 Handoff 再停，下一次从 L1 重新加载，不依赖聊天历史。
