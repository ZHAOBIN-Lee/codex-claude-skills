# State machine

状态存 `.ai/STATE.yaml`（schema 见 `templates/STATE.yaml`），由 `scripts/devflow.py transition` 修改。脚本同时维护相关任务文件顶层 front matter 的 `status`；任务正文与其他字段保持原样。非法转移或无效任务引用会被拒绝。

## 任务状态同步

| 实际阶段 | 当前任务 `status` |
| --- | --- |
| READY_TO_EXECUTE | ready |
| EXECUTING | executing |
| VALIDATING | validating |
| READY_FOR_REVIEW | ready_for_review |
| REVIEWING | reviewing |
| REWORK_REQUIRED | rework_required |
| BLOCKED | blocked |
| DONE | done |

Architect/Reviewer 创建任务时填写初始状态，之后由 Orchestrator 调用 `transition` 维护，不由模型手改已有任务的生命周期状态。尚未选中任务的规划阶段不需要任务文件。

审查通过并执行 `transition --to READY_TO_EXECUTE --task NEW` 时，旧任务变为 `done`，新任务变为 `ready`；旧任务存在时必须明确指定不同的新任务。返工任务完成审查后，其 `rework_of` 父任务也完成。脚本先验证所有涉及的任务文件，再落盘；普通写入失败时不返回成功，并回退已写入的任务状态。多文件更新不宣称在进程崩溃时具有原子性。

## 合法转移

| 从 | 到 | 条件 |
| --- | --- | --- |
| UNINITIALIZED | PLANNING | 建好 `.ai/`，有需求 |
| PLANNING | READY_TO_EXECUTE | Architect 产出 Task 与计划 |
| PLANNING | BLOCKED | 需求含糊/矛盾，需要用户 |
| READY_TO_EXECUTE | EXECUTING | route 选好 Executor tier |
| READY_TO_EXECUTE | PLANNING | 用户新增/变更需求 |
| EXECUTING | VALIDATING | Executor 返回 VALIDATE |
| EXECUTING | BLOCKED | Executor 返回 ESCALATE（Major Deviation） |
| VALIDATING | READY_FOR_REVIEW | 你亲自跑的验证命令全部通过（重置 `executor_retries`） |
| VALIDATING | EXECUTING | 验证失败，`executor_retries`+1，超限自动转 BLOCKED |
| READY_FOR_REVIEW | REVIEWING | — |
| READY_FOR_REVIEW | READY_TO_EXECUTE / DONE | **跳过 Review**：仅当用户显式覆盖（`--user-override`）或 `config.review.required: false`，否则脚本拒绝；须在 HANDOFF 与 PROGRESS 记录 |
| REVIEWING | READY_TO_EXECUTE | PASS / PASS_WITH_NOTES 且还有 Task（`tasks_this_run`+1） |
| REVIEWING | DONE | PASS 且无剩余必需 Task |
| REVIEWING | REWORK_REQUIRED | REWORK，已创建 Rework Task |
| REVIEWING | BLOCKED | Reviewer 返回 BLOCKED |
| REWORK_REQUIRED | EXECUTING | `rework_cycles`+1，超过 `max_rework_cycles` 自动转 BLOCKED |
| BLOCKED | PLANNING / READY_TO_EXECUTE / EXECUTING | 强模型根因分析后；`resolve_attempts`+1 并清零 rework/retry 计数 |
| DONE | PLANNING | 新需求 |

`NEEDS_ARCHITECT` 不是独立状态：它是 BLOCKED + `blocked_reason`，Orchestrator 看到后自动调 strong Architect。

## 计数器与循环上界

| 计数器 | 增加 | 上限（config） | 到上限 |
| --- | --- | --- | --- |
| `rework_cycles` | REWORK_REQUIRED→EXECUTING | `max_rework_cycles`=3 | → BLOCKED |
| `executor_retries` | VALIDATING→EXECUTING | `max_executor_retries`=2 | → BLOCKED |
| `resolve_attempts` | 离开 BLOCKED | `max_resolve_attempts`=1 | 再次 BLOCKED 时 `needs_user: true`，不再自动调模型 |
| `tasks_this_run` | REVIEWING→下一 Task/DONE | `max_tasks_per_run`=5 | 返回 `stop_run`，不继续 |
| `tasks_since_checkpoint` | 同上 | `checkpoint_every_n_tasks`=3 | 返回提示：先对合并 diff 跑一次 strong Reviewer |

单个 Task 内的最大循环次数有限：`(max_rework_cycles+1) × (max_resolve_attempts+1)` 轮 Executor 尝试，之后必然 `needs_user`。切换到新 Task（`transition --to READY_TO_EXECUTE --task NEW`）时计数器重置。

## 阶段 → 角色
UNINITIALIZED/PLANNING/BLOCKED → architect；READY_TO_EXECUTE/EXECUTING/REWORK_REQUIRED → executor；VALIDATING → 工具（你运行命令）；READY_FOR_REVIEW/REVIEWING → reviewer；DONE → 汇报。

## 崩溃恢复
STATE 只在一个角色**收口完成后**才转移。若中途中断：`status` 看 phase，EXECUTING/REVIEWING 阶段的工作视为未完成，先看 `git status/diff` 再重新派发同一阶段，不要跳阶段。
