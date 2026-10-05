# Context loading（Retrieve, don't preload）

## 层级
| 层 | 内容 | 何时 |
| --- | --- | --- |
| L1 | `STATE.yaml`、`HANDOFF.md` 最新记录、当前 Task | 每个角色都先读 |
| L2 | `MASTER_PLAN` 相关部分、`ARCHITECTURE` 相关小节、`DECISIONS` 相关 ADR | 按 Task 引用 |
| L3 | Task Context 列出的源码、直接依赖、相关测试 | Executor/Reviewer |
| L4 | 搜索全库、扫其他模块、读历史实现 | 仅在 L1-L3 不足且说明理由 |

## 给各角色的最小上下文
- Architect：L1 + `MASTER_PLAN` + 与需求相关的 L2/L3，L4 仅在需要核实现状时。
- Executor：L1 + Task 的 Context 与 Scope 文件。
- Reviewer：Task + **Task 范围内的 diff** + `VALIDATION.md` + 相关 ARCHITECTURE 小节与 ADR + `BLOCKERS.md`。
- Validator：只需要 Task 的 Validation 命令。

## 给 claude-bridge 的上下文怎么送
bridge 自动注入 `PROJECT_CONTEXT`、`DECISIONS`、`HANDOFF`（各有长度上限，HANDOFF/DECISIONS 取**尾部**）和 git status/diff（有界）。项目内的 STATE、Task、ARCHITECTURE、源码和验证记录仍通过 `--task TEXT` 列出路径，让 Claude 按需 Read。

技能文件通常位于项目目录外，由 Codex 宿主读取后把必要规范**内嵌到任务文本**：

- Architect：`roles/architect.md`、`references/task-schema.md`、`templates/TASK.md`。
- Executor：`roles/executor.md`；需要偏差判定时附上相关升级规则。
- Reviewer：`roles/reviewer.md`、适用的 `references/review-policy.md`，以及 `references/task-schema.md` 与 `templates/TASK.md` 中创建返工任务所需的规范。返工文件填写 `kind: rework`、具体 `id`、`status`、`rework_of`，不要求 Reviewer 读取项目外模板。

任务文本明确写明：“下面的角色说明与任务规范已内嵌；其中技能相对路径仅用于标识规范，不是待读文件。只读取本项目内列出的材料。”不把原技能绝对路径列进 Claude 的先读清单，不依赖额外外部目录授权。原生 Executor 子 Agent 也可用同一装配方式。

发送前核对完整 `--task TEXT` 不超过 32000 字符。角色约束和当前任务验收标准必须完整保留；删去无关规范或大段项目源码，项目材料继续按路径渐进读取。

## 压缩策略（保持文件可被小上下文读完）
- `HANDOFF.md`：只保留最新一个 Task 的完整记录；更早的合并为 `PROGRESS.md` 一行（时间、Task、结论、证据）。bridge 追加的运行记录由 bridge 管理，不手动删。
- `PROGRESS.md`：只追加，一行一步。
- `DECISIONS.md`：ADR 不删；被取代的标 `Superseded by ADR-NNN`，Task 只引用编号。
- `ARCHITECTURE.md`：用稳定 `##` 小节，Task 引用 `ARCHITECTURE.md#小节名`，角色只读该小节。
- `MASTER_PLAN.md`：完成的里程碑折叠为一行摘要。
- 超过 `max_tasks_per_run` 或上下文明显变长时，先写好 Handoff 再停，下一次从 L1 重新加载，不依赖聊天历史。
