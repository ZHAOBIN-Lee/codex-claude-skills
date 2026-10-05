# Task schema

文件：`.ai/tasks/TASK-NNN.md`（返工：`REWORK-TASK-NNN-MM.md`）。模板：`templates/TASK.md`。

## Front matter（`devflow.py` 解析的子集：标量与标量列表）
| 字段 | 取值 | 说明 |
| --- | --- | --- |
| `id` | `TASK-004` / `REWORK-TASK-004-01` | 与文件名一致 |
| `title` | 字符串 | 祈使句 |
| `kind` | `task` \| `rework` | |
| `status` | pending, ready, executing, validating, ready_for_review, reviewing, rework_required, blocked, done | 创建时由 Architect/Reviewer填写；之后由 Orchestrator 经 `devflow.py transition` 与实际阶段同步 |
| `risk` | low \| medium \| high | |
| `complexity` | 1-10 | |
| `domains` | 列表 | 敏感领域标签，须与 `risk.force_strong_for` 同名才触发升级 |
| `executor_tier` / `reviewer_tier` | efficient \| strong | Architect 提示，route 可进一步升级，不会降级 |
| `auto_execute` | bool | false 时 run 在该 Task 前停下问用户 |
| `rework_of` | 父 Task id 或 null | |
| `dependencies` | 列表 | 依赖未 done 不得开始 |

## 正文必备小节（`# 标题`）
Objective、Context、Scope（允许修改/新增）、Non-Scope、Requirements、Implementation Guidance、Acceptance Criteria、Validation（可直接运行的命令）、Escalation Conditions。

## 质量门槛（Architect 自检）
- Scope 是具体路径，不是"相关文件"。
- Acceptance Criteria 能被命令或明确检查判定。
- Validation 命令在当前仓库真实存在（脚本名、测试路径已核对）。
- 一个 Task 一个 Executor 在一次会话里能完成；做不完就拆。
- 命中敏感领域必须有 `domains`。

## 生命周期状态

`transition` 维护任务的顶层 `status`，不重写任务正文或其他 front matter。Executor 与 Reviewer 不手改已有任务的状态。任务执行、验证、审查和阻塞状态与实际阶段一致；审查通过后为 `done`。审查完成并切换任务时，先完成旧任务，再将指定的新任务设为 `ready`，不得将新任务误标为完成。

## Rework Task
Reviewer 创建。只含 Reviewer 找到的问题：每条给 文件、问题、证据、期望行为。Scope 只列涉及的文件，Acceptance Criteria 写"以上每条问题已解决且原 Task 的 Validation 仍通过"。`rework_of` 指向父 Task。
