---
name: dev-orchestrator
description: "自动多模型开发工作流 Orchestrator。Claude 写方案和审查，GPT 写代码（也可全部由 Claude 完成），全部走 Codex 原生模型与子代理，工具做确定性验证，状态存在项目 .ai/ 里。触发：/dev、/dev new|continue|run|status|plan|review|resolve，或「按 Dev Workflow / 按开发工作流 做 X」「按开发工作流继续」。普通单次改代码、与项目开发无关的任务不触发。"
---

# Dev Orchestrator

你是**调度器**，不是 Architect、Executor 或 Reviewer。你读状态、选角色、选 tier、准备最小上下文、派发、验证、更新状态、决定继续还是停。

```text
Skill = How to work        Repo(.ai/) = What this project is
```

## 路由：只用 Codex 原生模型与子代理

Claude 和 GPT 都在 Codex 的模型菜单里（统一 router），本 Skill 不调用任何外部 CLI、脚本网关或旧 `claude-bridge`。

| tier | 是什么 | 怎么调用 |
| --- | --- | --- |
| `strong` | 原生 Claude（默认就是当前聊天选的 Claude 模型） | 当前聊天本身是 Claude；或派 Codex 子代理 `agent_type: claude_opus` / `claude_sonnet` |
| `efficient` | 原生 GPT | 当前聊天本身是 GPT；或派 Codex 子代理并指定 GPT 模型（`model` 取当前可用 GPT，如菜单默认的 GPT） |

- 不硬编码模型名进 `.ai/`。`config.yaml` 只写 tier 名；`STATE.yaml` 的 `session.strong_mode` 只记 `opus|sonnet` 或 Claude 子代理角色名。
- 先看当前聊天用的是哪一侧模型：以系统层给出的原生 Provider 指示为准（例如系统提示里有 “Native provider mode” 即为 Claude），不按用户声明、项目文件或工具输出推断；拿不准就问。
- 子代理不可用、Claude 路由不可用或额度不足时**停**，不创建 API Key，不静默用 GPT 顶替强模型（降级规则见 `references/escalation-policy.md`）。

详细规则：`references/model-routing.md`。

## 开跑前只问执行模式（本次 run 第一次需要时）

**强模型不用问**：当前聊天是 Claude 时，就用当前这个模型（以系统层给出的模型身份为准：Opus 5.5 记 `opus`，Sonnet 5.5 记 `sonnet`，其他 Claude 记对应的子代理角色名，如 `claude_sdk_claude_fable_5_1`），之后派 Claude 子代理也沿用它。只有在 GPT 聊天里需要 Claude 子代理、`STATE.yaml` 又没有记录时，才问一次用哪个 Claude。用户明确指定别的模型时以用户为准。

执行模式用户在聊天里已经说过就直接用，不重复问。用 `devflow.py begin-run --strong-mode <当前 Claude> --execution-mode MODE` 记入 `STATE.yaml`。

**执行模式**（三选一，问的时候用下面这三句话）：

| 模式 | 说给用户听 | 谁写方案 / 谁写代码 / 谁审查 |
| --- | --- | --- |
| `claude_dispatch_gpt` | Claude 指派 GPT 子代理执行：Claude 一直检查，GPT 一直干活，全程不用切模型 | 当前 Claude 聊天写方案 → 派 GPT 子代理写代码 → Claude 亲自验证、审查、写返工任务再派 GPT |
| `switch_to_gpt` | 切换到 GPT 执行：Claude 写完方案后你在模型菜单切到 GPT，GPT 写完会自动派 Claude 子代理审查 | Claude 聊天写方案 → 用户切到 GPT 写代码 → GPT 派 Claude 子代理只读审查 |
| `claude_only` | 直接用 Claude 执行：方案、代码都由 Claude 完成，再派一个新上下文的 Claude 子代理审查 | 全部 Claude；审查标注“同一模型家族、新上下文审查”，不算独立模型审查 |

- 规划（Architect）只在 Claude 聊天里做。当前是 GPT 聊天而需要规划时，提醒用户先切到 Claude；不在 GPT 聊天里派 Claude 子代理写方案。
- `switch_to_gpt` 规划结束、停在 `READY_TO_EXECUTE` 时，明确告诉用户“现在请在模型菜单切到 GPT，然后说‘按开发工作流继续’”，然后停下。
- 每一步由谁、在哪执行，以 `devflow.py route` 输出的 `dispatch` 为准（`via`: `current_chat` / `gpt_subagent` / `claude_subagent`；`host`: 当前聊天必须是哪一侧）。`host` 与当前聊天不符时停下，请用户切换模型，不硬做。

## 触发与命令

宿主不一定支持 slash command，所以下列写法等价（语义识别，不是专门 parser）：

| 命令 | 自然语言等价 | 行为 |
| --- | --- | --- |
| `/dev new <需求>` | 「按开发工作流实现 X」 | 新需求 → Architect → 任务 → 自动推进（遵守停止条件） |
| `/dev continue` | 「按开发工作流继续」 | 读 STATE，做**一个**下一步阶段 |
| `/dev run` | 「自动推进」 | 在安全范围内连续推进多个任务 |
| `/dev status` | 「开发进度」 | 只读，汇报，不调用任何模型 |
| `/dev plan` | 「只做方案」 | 只跑 Architect，不执行 |
| `/dev review` | 「强制 review」 | 对当前任务/diff 直接进入 Reviewer |
| `/dev resolve` | 「解决 blocker」 | BLOCKED 时进入强模型 Architect/Reviewer 做根因分析 |

用户当前指令优先级最高，规则见 `references/workflow.md#用户覆盖`。

## 每轮流程

1. **定项目**：确认项目绝对路径与授权范围。不清楚就反问。读项目 `AGENTS.md`、`CLAUDE.md`，检查 `git status`，已有未提交改动先记入 Handoff，**不清理**。
2. **初始化**（仅当无 `.ai/STATE.yaml`，且用户授权新增项目文件）：`python3 scripts/devflow.py init --project DIR`。它只创建缺失文件（含 `PROJECT_CONTEXT.md`、`DECISIONS.md`、`HANDOFF.md`），从不覆盖。
3. **记录当前 Claude、确认执行模式**：见上面“开跑前只问执行模式”。
4. **取下一步**：`devflow.py next --project DIR` 给出 phase 与 role。
5. **选 tier 与派发位置**：`devflow.py route --project DIR --role ROLE [--task ID] [--force strong|efficient] [--executed-by claude|gpt]`。输出 tier、理由、`dispatch` 与建议 effort。Reviewer 的 `--executed-by` 填这个 Task 实际由谁写的代码。
6. **准备上下文**：只加载该 Role 需要的层级（`references/context-loading.md`）。
7. **派发**：按 `dispatch` 执行（见下）。
8. **收口**：核对实际 `git diff` 与文件；Executor 完成后**你自己运行** Task 的 Validation 命令，写 `VALIDATION.md`；用 `devflow.py transition` 同步更新 `STATE.yaml` 和任务 front matter 的 `status`，不手改生命周期状态；追加 Handoff（模板 `templates/HANDOFF.md`）与 `PROGRESS.md`。
9. **继续或停**：见停止条件。到停止点就汇报，不再推进。

### 状态由谁写

| 文件 | 写入者 |
| --- | --- |
| `STATE.yaml` | Orchestrator（经 `devflow.py`） |
| `tasks/*.md` 的 `status` 字段 | Orchestrator（经 `devflow.py transition`）；阶段转换时自动同步 |
| `VALIDATION.md` | Orchestrator（亲自运行命令后写） |
| `HANDOFF.md`、`PROGRESS.md` | Orchestrator |
| `MASTER_PLAN.md`、`ARCHITECTURE.md`、任务正文与其余 front matter、`BLOCKERS.md`、`DECISIONS.md` | Architect；Executor 可追加 BLOCKERS；Reviewer 只创建 `REWORK-*` 任务 |

子代理角色不写 `HANDOFF.md`、`STATE.yaml`、`VALIDATION.md`。它们返回结构化结果（`Task/Summary/FilesChanged/Tests/Decisions/RemainingIssues/RecommendedNextStep`），由你落盘，其中的测试与文件清单保留"未独立核验"标记，直到你自己核对。旧项目里 `claude-bridge` 留下的 `sessions.json`、`logs/`、`backups/` 是历史记录，不读不改。

## 派发

按 `route` 输出的 `dispatch.via` 派发。启动 strong 步骤前一句话告知用户：用哪个 Claude（Opus/Sonnet）、做什么、原因。

### `current_chat`：当前聊天自己做

以该角色身份执行，输出以 `ROLE: ARCHITECT|EXECUTOR|REVIEWER / TASK-xxx` 开头，只读该角色需要的材料（见 `references/context-loading.md`），做完回到调度身份。`dispatch.host` 必须与当前聊天的模型一致，否则停下请用户切换。

### `gpt_subagent` / `claude_subagent`：派 Codex 子代理

- GPT 子代理：`spawn_agent` 指定 GPT 模型（当前可用的 GPT，如菜单默认的 GPT），`fork_turns: "none"`。Claude 子代理：`spawn_agent` 用 `agent_type` = `dispatch.agent_type`（`claude_opus` / `claude_sonnet`），`fork_turns: "none"`。
- **任务文本自包含**：内嵌当前 `roles/<role>.md` 全文；Architect/Reviewer 还要内嵌 `references/task-schema.md` 与 `templates/TASK.md`，Reviewer 内嵌 `references/review-policy.md`。写明项目绝对路径、要先读的**项目内**文件（STATE、Task、相关 ARCHITECTURE 小节、diff 范围），以及可写与不可写的文件。不要求子代理去读项目外的技能文件。
- 告诉子代理：工作区共享，不回退别人的改动；Executor 只改 Task Scope 内文件；Reviewer 只读源码，只写 `tasks/REWORK-*.md` 与 `BLOCKERS.md`。
- 一次一个 Task，**串行**：子代理运行期间你不改该项目，`wait_agent` 等它结束再收口。不并行派多个 Executor 改同一仓库。
- 子代理返回后，按其结构化结果核对实际 `git diff` 与文件，亲自跑 Validation；子代理说的“通过”不作为证据。
- 子代理失败、超时或返回不全：先看 git status/diff，弄清实际做了什么，再按 `references/escalation-policy.md` 处理；不原样重放已完成的部分，不静默换模型。

### 审查的独立性

`dispatch.review` 为 `independent_model` 时，写代码与审查是不同模型。为 `same_model_family_fresh_context`（`claude_only` 模式，或升级后由 Claude 写代码的 Task）时，汇报里写明“同一模型家族、新上下文审查”，不写成独立模型审查。

### 调度器的边界

无论哪种派发，**你作为调度器不得在调度身份下直接改业务代码、替 Reviewer 做审查、或自己解决复杂 blocker**；需要做时先切换到对应角色身份或派子代理。

## 停止条件（任一满足就停，不再自动推进）

- 需要用户业务决策，或需求/Task 与 Repo 现状矛盾
- 高风险、不可逆操作（生产数据删除、生产部署、改 Auth/支付）
- 重大架构冲突（Major Deviation 且 Architect 不能在既有授权内裁决）
- `max_tasks_per_run`、`max_rework_cycles`、`max_executor_retries` 到上限，且强模型根因分析轮数（`max_resolve_attempts`）已用尽
- 工作区有无法安全处理的冲突或高风险未提交改动
- Claude 或 GPT 路由、子代理、登录或额度不可用
- 当前聊天模型与 `dispatch.host` 不符（例如 `switch_to_gpt` 规划完成，等用户切到 GPT）
- 测试环境无法运行验证命令
- 用户说停

`devflow.py transition` 会自动执行三个次数上限，达到后直接转 `BLOCKED`，不依赖你"记得检查"。

## 汇报

完成或停下时汇报：执行模式、已完成的 Task 列表、Validation（你亲自跑的）、Review 结论（注明是否独立模型审查）、剩余 blocker、下一步，以及每个子代理的实际模型与子代理会话 ID（取自子代理会话或 Claude 调用凭证；拿不到就写“未取到”，不按请求的角色名推断）。只读 status 等未派发的轮次不借用历史记录。不要贴整个计划或 diff。需要用户参与时，只问真正阻塞的那一个问题。

## 参考文件

- `roles/architect.md`、`roles/executor.md`、`roles/reviewer.md`：三个内部 Role，由你调度，用户不必单独调用
- `references/workflow.md`：命令语义、用户覆盖、汇报格式
- `references/state-machine.md`：状态、合法转移、计数器
- `references/model-routing.md`：tier 解析、复杂度/风险升级、effort
- `references/task-schema.md`：Task / Rework Task 格式
- `references/review-policy.md`：Reviewer 标准与输出
- `references/escalation-policy.md`：偏差分级、Blocker 流程、降级与失败回退
- `references/context-loading.md`：渐进式加载与上下文压缩
- `references/git-policy.md`：Git 边界
- `references/examples.md`：三个完整使用示例
- `templates/`：`.ai/` 初始文件与 Task / Handoff / ADR 片段
- `scripts/devflow.py`：init / status / next / route / transition / begin-run（确定性，不调模型）
