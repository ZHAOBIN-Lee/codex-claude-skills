# Review policy

## 顺序
Executor 实现 → **确定性验证**（build/test/lint/typecheck/format/静态分析/针对性集成测试）→ Reviewer 语义审查。命令能发现的问题不留给 Reviewer。

## Validator（Orchestrator 亲自执行）
- 运行 Task `# Validation` 里的命令，记录命令、退出码、结果摘要到 `VALIDATION.md`。
- 不采信 Executor 报告的"测试通过"。
- 环境跑不起来（依赖缺失、服务未启动）→ 记录原因并停止，不要把"没跑"写成"通过"。
- 验证命令不覆盖 Acceptance Criteria 时，在 `VALIDATION.md` 标明缺口，交给 Reviewer 判断。

## Reviewer 维度
- **Correctness**：Objective 是否真实现、边界、错误处理、并发、状态正确性。
- **Scope**：越权、夹带重构、改变未授权行为、公开 API 形状。
- **Architecture**：是否符合 ARCHITECTURE，是否违反 ADR。
- **Maintainability**：重复、过度复杂、可读性。
- **Testing**：覆盖关键路径与失败路径；是否 mock 掉核心逻辑凑通过。
- **Security**：按 Task 相关度（输入校验、鉴权、注入、秘密、权限提升）。
- **Validation 可信度**：命令是否真的覆盖了 Acceptance Criteria。

## 输出结论
| 结论 | 含义 | Orchestrator 动作 |
| --- | --- | --- |
| PASS | 全部满足 | REVIEWING → 下一个 Task / DONE |
| PASS_WITH_NOTES | 满足，有不阻塞备注 | 备注写 PROGRESS，同 PASS |
| REWORK | 有必须修的问题 | 创建 Rework Task → REWORK_REQUIRED |
| BLOCKED | 需要架构/用户决定 | → BLOCKED |

## 反偏执规则（防返工循环）
- 问题必须有证据，且对应 Acceptance Criteria、Scope、ADR 或确定的缺陷；偏好类意见只能是 NOTES。
- 第二次及以后的 Review 只验证上一轮列出的问题是否解决，以及改动是否引入新回归；不得追加首轮没提的新标准（除非它是新引入的缺陷）。
- 同一问题连续两轮未解决 → 返回 BLOCKED 并给出根因判断，不再返工。

## Checkpoint review
连续完成 `checkpoint_every_n_tasks` 个 Task 后，对合并 diff 额外跑一次 strong Reviewer，重点看跨 Task 一致性和累积的架构漂移。

## DONE 的条件
必需 Task 全部完成、Validation 通过、Reviewer PASS、无未解决 blocker、MASTER_PLAN/PROGRESS/HANDOFF 已更新、无未记录的 Major Deviation。
