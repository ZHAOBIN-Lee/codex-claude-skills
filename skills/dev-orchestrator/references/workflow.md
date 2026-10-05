# Workflow

```text
用户 → Orchestrator → Architect(strong) → Tasks → Executor(efficient) → Validator(工具)
                                   ↑                                        ↓
                          Blocker/RCA(strong)  ←  REWORK  ←  Reviewer(strong)  → PASS → 下一个 Task / DONE
```

## 命令语义

- **new**：有新需求即进 Architect，不管当前 phase。若 STATE 非 DONE/UNINITIALIZED，先问用户：并入当前里程碑还是另起（避免覆盖进行中的计划）。DONE → PLANNING 合法。
- **continue**：`next` 给出的**一个**阶段，做完汇报。
- **run**：先 `begin-run`；循环"next → route → 派发 → 收口"，直到停止条件。每个 Task 的 Review 不可跳过（除用户覆盖）。
- **status**：只读 `devflow.py status`，不调模型。汇报：当前里程碑、当前 Task、已完成/待办/阻塞 Task、Validation 状态、当前角色、下一步。
- **plan**：只跑 Architect；结束于 `READY_TO_EXECUTE`，不执行。
- **review**：对当前 Task 或当前 diff 直接 Reviewer。无 Task 时由你先用 Architect 建一个"审查范围"Task，或把范围写进 task 文本，不凭空审全库。
- **resolve**：仅 BLOCKED。`needs_user: true` 时不再调模型，直接汇报用户。

## 用户覆盖
用户的新指令优先于默认流程：

- "先不要执行，只做方案" → 立刻停止自动推进，停在 `READY_TO_EXECUTE`。
- "这个 Task 用强模型" → `route --force strong`；"用 GPT 做" → `--force efficient`。覆盖只对该 Task 生效，记入 Handoff（`source: user`）。
- "不要 Review，直接继续" → 可执行：`transition --user-override`，并在 Handoff 和 PROGRESS 记录"用户显式跳过 Review"。脚本在 `config.review.required: true` 时拒绝没有该标志的跳过（READY_FOR_REVIEW → 下一 Task/DONE）；高风险 Task 仍应提醒一次再执行。
- 用户指定 effort → `--effort-source user`；当前 CLI/模型不支持就报告限制，不悄悄改值。

## 汇报格式
```text
<目标> 已完成 / 已停在 <phase>。
Completed: TASK-001, TASK-002, REWORK-TASK-002-01
Validation: PASS（你亲自运行的命令）
Review: PASS
Claude receipts: <按 claude-bridge 回执规则逐次列出实际模型、完整会话 ID、状态及本轮凭证；未调用时省略>
Remaining blockers: None | <一个需要用户回答的问题>
```
