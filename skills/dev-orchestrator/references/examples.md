# 使用示例

`devflow` = `python3 <skill>/scripts/devflow.py`。示例里的路径是虚构的。

## 日常最简单的调用
```text
按开发工作流实现 <需求>          # 新需求，自动推进到停止点
按开发工作流继续                 # 下次回来接着做
/dev status                      # 只看进度，不花额度
```
开始前只需回答一次执行模式（Claude 指派 GPT 子代理 / 切换到 GPT / 全部 Claude）；强模型就是当前聊天选的 Claude。

## 1. 新项目
```text
用户：在 /Users/me/code/member-system 里，按开发工作流实现会员系统（注册、等级、积分）。
```
1. Orchestrator 确认项目路径与授权，读项目规则、`git status`。无 `.ai/`：征得同意后 `devflow init`（同时补齐 `PROJECT_CONTEXT`、`DECISIONS`、`HANDOFF`）。
2. 当前聊天是 Claude Opus，记为强模型；问执行模式 → 用户答 Claude 指派 GPT 子代理。`devflow begin-run --strong-mode opus --execution-mode claude_dispatch_gpt`。
3. `transition --to PLANNING`；`route --role architect` → strong, effort high。告知："本次由当前 Claude Opus 聊天写方案；新项目需要整体方案与任务拆分。"
4. Claude 聊天以 Architect 身份写 `MASTER_PLAN`、`ARCHITECTURE`、ADR、`TASK-001..006`（积分任务标 `domains: [payments]`）。→ `READY_TO_EXECUTE`。
5. 对 TASK-001：`route --role executor --task TASK-001` → efficient（complexity 3, risk low）。`dispatch.via=gpt_subagent`：派 GPT 子代理实现 → `VALIDATING` → Orchestrator 亲自跑 `npm test`、`npm run typecheck`，写 `VALIDATION.md`。
6. `READY_FOR_REVIEW` → Claude 聊天以 Reviewer 身份审查（独立模型审查）→ PASS → `READY_TO_EXECUTE` 下一个 Task。
7. 到 TASK-004（积分扣减，`domains: [payments]`）：`route` → **strong**（sensitive domain），由 Claude 聊天自己执行，再派新上下文的 Claude 子代理审（汇报写明同一模型家族审查）。
8. 做满 5 个 Task（`max_tasks_per_run`）→ 汇报并停；用户说"继续"再 `begin-run`。

## 2. 已有项目新增 Feature
```text
用户：在 /Users/me/code/shop 按开发工作流加"优惠券核销"。
```
- 已有 `.ai/PROJECT_CONTEXT.md`→ `devflow init` 只补缺失文件，`skipped_existing` 里列出已有的。
- 工作区有用户未提交改动：记入 Handoff 基线，不清理。若它与 Task Scope 的文件重叠 → 停下问用户。
- Architect 先读现有 transaction helper，写 ADR-003「复用现有事务抽象，不引入新 ORM」，拆出 TASK-001（服务）、TASK-002（API）、TASK-003（并发测试，`domains: [concurrency]`）。
- TASK-001 efficient 实现；Review 返回 REWORK：并发下可重复核销。Reviewer 写 `REWORK-TASK-001-01`（含失败用例）→ `REWORK_REQUIRED` → `EXECUTING`（`rework_cycles=1`）→ 验证 → 复审 PASS。
- 汇报：
```text
优惠券核销已完成。
Completed: TASK-001, REWORK-TASK-001-01, TASK-002, TASK-003
Validation: PASS（npm test -- coupon; typecheck; lint，均由 Orchestrator 运行）
Review: PASS
Remaining blockers: None
```

## 3. 执行中出现复杂 Blocker
TASK-004 执行中，Executor 发现"必须改 Schema 才能保证幂等"，这是 Major Deviation：
1. Executor 停止，`BLOCKERS.md` 记录事实，返回 ESCALATE。`transition --to BLOCKED --reason "needs schema change"`。
2. `next` → role architect。Orchestrator **自动**调 strong Architect（`resolve`），无需用户转述。
3. Architect 评估：Schema 变更会碰 `schema-migration`，选择"用唯一键 + 幂等请求 ID，不改表结构"，写 ADR-005，改写 TASK-004，设 `executor_tier: strong`。
4. `transition --to EXECUTING`（`resolve_attempts=1`，计数清零）→ strong Executor 实现 → 验证 → 复审。
5. 若 Architect 判断确实必须改 Schema 且涉及用户业务取舍：`needs_user`，停下只问一个问题："幂等是否允许在 24h 内保留请求记录？"
6. 若再次进入 BLOCKED（`resolve_attempts` 已达 `max_resolve_attempts`），直接 `needs_user: true`，不再自动调模型。
