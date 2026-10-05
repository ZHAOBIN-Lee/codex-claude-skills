# Model routing

## 原则
- **复用现有机制，不建第二套 Router**。本 Skill 只产出 tier 决策，由已有机制执行。
- 现有机制：`claude-bridge`（Codex → 官方 Claude Code CLI，订阅登录，串行）。它的 `--mode` 就是现有 alias：`default | sonnet | opus | review`。
- 环境里**没有** strong/efficient 之类的现成 tier；这两个 tier 名是本 Skill 引入的**逻辑名**，只映射到上面已有的东西：
  - `strong` → Claude 侧（bridge），具体 `opus|sonnet|default` 开跑前向用户确认，存 `STATE.session.strong_mode`。
  - `efficient` → 宿主当前聊天的 GPT 原生模型，不指定、不记录模型名。
- 项目可在 `.ai/config.yaml` 覆盖 `routing`（如把某类 Task 固定走 strong），仍只写 tier 名。

## 角色默认
Architect → strong；Executor → efficient；Reviewer → strong。

## Executor 升级规则（`devflow.py route` 实现，优先级自上而下）
1. 用户强制（`--force`）→ 用户指定的 tier。
2. `risk: high` → strong。
3. `complexity >= 8` → strong。
4. 命中敏感领域 → strong：`domains` 标签，或 title/Objective 的保守关键词（auth、permission、payment、encrypt、migration、delete data、concurren、deploy……）。关键词只会多升不会少升，误判成本只是强模型额度。
5. Task 里 Architect 写了 `executor_tier: strong` → strong（只认升级，不认降级）。
6. 否则 efficient。complexity 6-7 默认 efficient，命中第 4 条才升。

判断依据是**决策复杂度 + 风险**，不是"写代码 = 弱模型"。难以用自动测试验证的行为也应由 Architect 标 `domains` 或 `risk: high`。

## 强度（effort，仅 strong 调用）
bridge 要求每次传 `--effort`、`--effort-source`、`--effort-reason`。`route` 给建议值：

- Architect → `high`；Reviewer/strong Executor → `high`（risk=high、complexity≥7 或敏感领域）否则 `medium`。
- 自动选择只用 `medium|high`（bridge 规则，不用 xhigh/max）；用户明确指定则 `--effort-source user`。
- `--effort-reason` ≤160 字符、单行，不抄任务全文。
- 请求值不是模型内部真实强度；`CLAUDE_CODE_EFFORT_LEVEL` 非空会让 bridge BLOCKED，只报变量名，不改用户设置。

## 调用前必须告知用户
一句话：本次用 Claude <Opus|Sonnet|默认>，请求强度 <x>，原因。efficient 不用特别告知，状态汇报里带一句"Executor: 当前 GPT 模型"。

## 平台差异
- 本 Skill 以 Codex（GPT）为宿主。Claude Code 宿主不是本版目标：它无法"调用 GPT"，只能用自身子 Agent 切 Claude 各档；若要支持需单独设计 tier 映射。
- bridge 不是并行的：一次只一个 Agent 改项目，所以 V1 没有并行 Executor。
