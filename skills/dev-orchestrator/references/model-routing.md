# Model routing

## 原则
- **只用 Codex 原生模型与子代理**。Claude 和 GPT 都在 Codex 模型菜单里（统一 router），本 Skill 不调用外部 CLI、脚本网关或旧 `claude-bridge`。
- 两个 tier 是逻辑名：
  - `strong` → 原生 Claude，默认用当前聊天选的 Claude 模型，存 `STATE.session.strong_mode`（`opus|sonnet` 或 Claude 子代理角色名）；只有 GPT 聊天需要 Claude 子代理且没有记录时才问。
  - `efficient` → 原生 GPT，用当前可用的 GPT 模型，不写进 `.ai/`。
- 每次 run 还要选**执行模式**（`STATE.session.execution_mode`），决定每一步在当前聊天做还是派子代理。见 `SKILL.md`“开跑前只问执行模式”。
- 项目可在 `.ai/config.yaml` 覆盖 `routing`（如把某类 Task 固定走 strong），仍只写 tier 名。

## 角色默认
Architect → strong；Executor → efficient；Reviewer → strong。

## 派发位置（`devflow.py route` 的 `dispatch`）

| 执行模式 | Architect | Executor（efficient） | Executor（升级为 strong） | Reviewer |
| --- | --- | --- | --- | --- |
| `claude_dispatch_gpt` | Claude 聊天自己做 | 派 GPT 子代理 | Claude 聊天自己做 | GPT 写的：Claude 聊天自己审；Claude 写的：派 Claude 子代理新上下文审 |
| `switch_to_gpt` | Claude 聊天自己做 | 用户切到 GPT 后，GPT 聊天自己做 | GPT 聊天派 Claude 子代理 | GPT 写的：派 Claude 子代理审；Claude 写的：派 Claude 子代理新上下文审 |
| `claude_only` | Claude 聊天自己做 | Claude 聊天自己做 | Claude 聊天自己做 | 派 Claude 子代理新上下文审（同一模型家族） |

- `dispatch.host` 是当前聊天必须是哪一侧。与当前聊天不符时停下，请用户在模型菜单切换。
- Claude 子代理用 `agent_type` = 记录的 Claude（`claude_opus`、`claude_sonnet` 或其他 Claude 角色）；GPT 子代理用 `spawn_agent` 的 `model` 指定 GPT。均 `fork_turns: "none"`，任务文本自包含。
- Architect 不在 GPT 聊天里派 Claude 子代理去做：规划只在 Claude 聊天里进行。

## Executor 升级规则（`devflow.py route` 实现，优先级自上而下）
1. 用户强制（`--force`）→ 用户指定的 tier。
2. `risk: high` → strong。
3. `complexity >= 8` → strong。
4. 命中敏感领域 → strong：`domains` 标签，或 title/Objective 的保守关键词（auth、permission、payment、encrypt、migration、delete data、concurren、deploy……）。关键词只会多升不会少升。
5. Task 里 Architect 写了 `executor_tier: strong` → strong（只认升级，不认降级）。
6. 否则 efficient。complexity 6-7 默认 efficient，命中第 4 条才升。

判断依据是**决策复杂度 + 风险**，不是"写代码 = 弱模型"。

## 强度（effort）
`route` 对 strong 步骤给出建议值：Architect → `high`；Reviewer/strong Executor → `high`（risk=high、complexity≥7 或敏感领域）否则 `medium`。Claude 子代理角色自带固定强度（当前为 medium），建议值只用于告知用户和在当前聊天做时参考；不为此改全局配置。

## 调用前告知用户
一句话：本次用 Claude <Opus|Sonnet>、在当前聊天还是子代理、做什么。efficient 不用特别告知，状态汇报里带一句"Executor: GPT"。

## 并行
V1 一次只一个 Executor 改项目，子代理串行派发、等待返回后再派下一个。
