# Git policy

- **先看再动**：每轮开始 `git status`，区分用户原有未提交改动与本轮改动，记入 Handoff。
- **不清理用户工作**：禁止 `reset --hard`、`clean`、`checkout --`/`restore` 覆盖、force-push、rebase、丢弃 stash，除非用户针对该操作明确授权。
- **不自动 commit/push/部署/建 PR**：用户明确要求才做（遵循项目 CLAUDE.md）。
- **Task 范围内的 diff 是 Reviewer 的输入**。因为不自动 commit，Orchestrator 在派发 Executor 前记录 `git status`/`git diff --stat` 基线，收口时只把相对基线新增的、位于 Task Scope 内的改动交给 Reviewer；基线里已有的用户改动明确标注、不审查。
- **Scope 之外的改动**：收口时对比 `git status` 与 Task Scope，发现越界改动 → 不得带入 Review 当作成果：先让 Executor 说明；无法说明就作为 Rework 项，不悄悄回滚。
- **Rework 不混入无关修改**：Rework Task 的 Scope 只含问题涉及的文件。
- **并行写同一仓库**：V1 禁止。同一时间只允许一个 Executor（当前聊天或一个子代理）修改项目。
- 工作区存在无法安全处理的冲突（合并冲突标记、与 Task Scope 重叠的用户未提交改动）→ 停止并询问。
