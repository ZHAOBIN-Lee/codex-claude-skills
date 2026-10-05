# Escalation, fallback, safety stops

## 偏差分级
**Minor**：只涉及少量相关文件，且不改 Architecture、Schema、公开 API、Auth、关键依赖、业务规则。Executor 自行处理并记录（返回的 `Decisions` → Handoff 的 Deviations）。

**Major**（任一）：改 DB Schema；改公开 API；改 Auth/权限；加重要依赖；改 Architecture；需求逻辑矛盾；Task 与 Repo 实际状态明显不符；安全设计需重判；连续失败超限。

## Major 处理链
```text
Executor 停止 → BLOCKERS.md 写事实 → transition BLOCKED(blocked_reason)
→ Orchestrator 自动调 strong Architect（RCA）→ 更新 ADR/Task → transition 离开 BLOCKED
→ Executor 继续
```
- 用户不必手动把问题转给强模型。
- 离开 BLOCKED 时 `resolve_attempts`+1；`max_resolve_attempts` 用尽后再次 BLOCKED，`needs_user: true`，停止自动调用，向用户汇报**一个**最小的待决问题。
- RCA 结论可以是：调整 Task、升级该 Task 到 strong Executor（`executor_tier: strong`）、需要用户决策。

## 必须停下问用户（不能由 Architect 代决）
业务决策；不可逆/生产数据删除；生产部署；支付/鉴权设计变更涉及真实账户；用户明确要求确认的事项。

## 失败回退
| 失败 | 处理 |
| --- | --- |
| bridge `doctor` 失败 / 未登录 / API 或非预期认证 / 额外 usage 未确认 | 停。不创建 API Key，不自动开额外用量，不读凭据 |
| bridge `failed` / `timeout` | 不自动重试（超时后完成状态未知，先看 git status/diff）。报告原因，询问用户 |
| bridge `needs_permission` | 如实报告被拒操作；只有既有授权覆盖或用户批准才重试 |
| 额度/模型不可用 | 停 strong 阶段，把当前状态写入 Handoff，让用户选择：等待 / 换 Claude 模式 / 明确同意降级 |
| 结构化结果缺失或格式不符 | 视为未完成，核对实际文件，不凭文字推断 |
| 验证命令无法运行 | 记录并停止，不当作通过 |

### 降级（只有用户明确同意才允许）
由 GPT 临时承担 Architect/Reviewer：
- Handoff 与 PROGRESS 标记 `degraded: <role> by efficient tier`；
- 同一个模型既执行又审查**不算独立 Review**，汇报里必须写明，Task 不得标为"Reviewer PASS"，只能"自审通过，待强模型复核"；
- 恢复 bridge 后补做强模型复核。
不得静默降级，也不得因为"方便"跳过。

## 安全停止条件（汇总）
见 `SKILL.md`「停止条件」。其中任何一条触发都优先于 `auto_continue_low_risk`。
