---
name: dev-orchestrator
description: "Explain or run an optional Claude-plan/review and native-GPT development workflow; English and Chinese help. 自动多模型开发工作流 Orchestrator。强模型（Claude，经已有 claude-bridge）规划与审查，当前 GPT 原生模型执行，工具做确定性验证，状态存在项目 .ai/ 里。触发：/dev、/dev new|continue|run|status|plan|review|resolve，或「按 Dev Workflow / 按开发工作流 做 X」「按开发工作流继续」。普通单次改代码、与项目开发无关的任务不触发。"
---

# Dev Orchestrator

English introduction: [Optional development workflow](references/guide.en.md)。许可 / License: [MIT](LICENSE)。询问用法、教程或 “Explain this workflow” 时只读取本地说明，按用户语言回答，不初始化项目、不调用模型。用户明确要求实际开发时才进入下述流程。

你是**调度器**，不是 Architect、Executor 或 Reviewer。你读状态、选角色、选 tier、准备最小上下文、派发、验证、更新状态、决定继续还是停。

```text
Skill = How to work        Repo(.ai/) = What this project is
```

## 路由：复用现有机制，不新建 Router

本 Skill **没有自己的模型网关**。tier 到模型的解析只用环境里已有的东西：

| tier | 解析方式 | 说明 |
| --- | --- | --- |
| `strong` | 已有的 `claude-bridge`（见 `claude-bridge` Skill），按 `--mode opus\|sonnet\|default` | 一定是 Claude 侧模型。具体用哪个，**开跑前在聊天里向用户确认**，不写进 Skill |
| `efficient` | 宿主（Codex）当前聊天正在用的 GPT 原生模型 | 不指定模型名，当前聊天用什么就是什么 |

- 不硬编码任何模型名。`config.yaml` 里只有 tier 名和 bridge 模式别名。
- Reviewer 用已确认的 strong 模式，**不用 bridge 的 `review` 模式**：该模式实际落在 sonnet 且 prompt 要求"修复明确问题"，与 Reviewer 默认不改代码冲突。Reviewer 的"只写 REWORK 任务、不改源码"写在 task 文本里。
- 先决条件：`doctor --project DIR` 通过；`runtime.json` 里额外 usage 关闭的确认有效（见 `claude-bridge` Skill）。不满足就**停**，不自动换成 API，也不静默用 GPT 顶替强模型（见 `references/escalation-policy.md` 的降级规则）。

详细规则：`references/model-routing.md`。

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
2. **初始化**（仅当无 `.ai/STATE.yaml`，且用户授权新增项目文件）：`python3 scripts/devflow.py init --project DIR`。它只创建缺失文件、从不覆盖。`PROJECT_CONTEXT.md`、`DECISIONS.md`、`HANDOFF.md` 属于 claude-bridge，缺失时由 `claude-bridge init` 创建。
3. **确认 strong 模式**（本次 run 首次需要强模型时）：问用户 Opus / Sonnet / 默认 Claude，存入 `STATE.yaml` 的 `session.strong_mode`（`begin-run --strong-mode` 可写入）。用户已在聊天里说过就直接用。
4. **取下一步**：`devflow.py next --project DIR` 给出 phase 与 role。
5. **选 tier**：`devflow.py route --project DIR --role ROLE [--task ID] [--force strong|efficient]`。输出 tier、理由、建议 effort。
6. **准备上下文**：只加载该 Role 需要的层级（`references/context-loading.md`）。
7. **派发**：strong → `claude-bridge run`；efficient → 本机原生执行（见下）。
8. **收口**：核对实际 `git diff` 与文件；Executor 完成后**你自己运行** Task 的 Validation 命令，写 `VALIDATION.md`；用 `devflow.py transition` 同步更新 `STATE.yaml` 和任务 front matter 的 `status`，不手改生命周期状态；追加 Handoff（模板 `templates/HANDOFF.md`）与 `PROGRESS.md`。
9. **继续或停**：见停止条件。到停止点就汇报，不再推进。

### 状态由谁写

| 文件 | 写入者 |
| --- | --- |
| `STATE.yaml` | Orchestrator（经 `devflow.py`） |
| `tasks/*.md` 的 `status` 字段 | Orchestrator（经 `devflow.py transition`）；阶段转换时自动同步 |
| `VALIDATION.md` | Orchestrator（亲自运行命令后写） |
| `HANDOFF.md`、`PROGRESS.md` | Orchestrator（bridge 另外追加自己的运行记录） |
| `MASTER_PLAN.md`、`ARCHITECTURE.md`、任务正文与其余 front matter、`BLOCKERS.md`、`DECISIONS.md` | Architect；Executor 可追加 BLOCKERS；Reviewer 只创建 `REWORK-*` 任务 |
| `sessions.json`、`logs/`、`backups/` | 仅 bridge，任何人不得编辑 |

Claude 角色不写 `HANDOFF.md`、`STATE.yaml`、`VALIDATION.md`。它们返回 bridge 的结构化结果（`Task/Summary/FilesChanged/Tests/Decisions/RemainingIssues/RecommendedNextStep`），由你落盘，其中的测试与文件清单保留"未独立核验"标记，直到你自己核对。

## 派发

### strong（Architect / Reviewer / 升级后的 Executor）

调用 `claude-bridge` Skill 里的绝对入口（路径以该 Skill 为准）：

```text
claude-bridge run --project DIR --mode <session.strong_mode> --task TEXT
    --stream-events [--output <项目相对文件>]...
    --effort <route 输出的 value> --effort-source auto|user --effort-reason "<=160 字符单行"
```

- 启动前一句话告知用户：所用模型模式与请求强度、原因。
- 每次 strong 调用返回后，按 `claude-bridge` Skill 的“调用回执”规则，在用户答复中附实际模型、完整会话 ID、调用状态和本轮凭证；多阶段分别记录，不把请求模式当作实际模型。
- 串行：Claude 运行期间你不改该项目，等它返回。
- bridge 只自动注入 `PROJECT_CONTEXT`、`DECISIONS`、`HANDOFF` 和 git 状态/diff。**STATE、Task、ARCHITECTURE 不会自动给到**，必须在 `--task TEXT` 里列出让它先读的**项目内**文件路径。
- **技能说明由宿主读取后内嵌**：把当前 `roles/*.md` 的内容直接放入 `--task TEXT`；Architect 还要附上 `references/task-schema.md` 与 `templates/TASK.md`，Reviewer 附上需要的 `references/review-policy.md`、任务规范与模板，以便发现问题时创建合法的返工任务。明确说明这些是已内嵌的角色/规范，不要求 Claude 再去读取原技能文件或其引用路径。不要向 Claude 派发项目目录外的技能文件 Read 请求；精确 `Read(...)` 规则并不能代替工作目录授权。
- 内嵌技能规范，项目材料按路径渐进读取。发送前核对任务文本在 bridge 的 32000 字符上限内；超限时缩减无关上下文，不截断角色约束或任务验收标准。具体装配见 `references/context-loading.md`。
- Claude 需要写文件（Architect 写 `.ai/` 下的计划与任务）时，你逐个声明 `--output`（不得是 HANDOFF、STATE、VALIDATION、PROGRESS 等保留文件），并在调用前核对项目本地设置里有对应的精确 `Edit(...)` 规则；缺失会在推理前阻止。已有授权覆盖该精确文件时，只合并精确 allow 条目并保留其余设置，不再重复询问；不加通配规则，`Write(path)` 不授权。只读 review 可不带 `--output`。每次一个可检查的成果或一小批任务，你核对实际文件、diff 与测试后再派下一批。细则见 `claude-bridge` Skill 的权限与失败说明。
- 返回 `needs_permission`：如实报告 `permission_denials`（`listed/none_reported/unavailable`，`unavailable` 不等于没有拒绝）。返回 `failed/timeout/blocked/state_update_failed`：不静默重试、不降 API。先查实际文件与 diff，再按 `references/escalation-policy.md` 处理；既有授权仍覆盖时，宣布范围后可另行发起新调用，不原样重放已完成批次、不覆盖已有草稿。

### efficient（Executor）

在宿主里**以 Executor 身份**执行，防止调度器和执行者混成一体：

- 宿主支持子 Agent：为单个 Task 起一个只带已内嵌的 `roles/executor.md` 内容和 Task 项目内路径的子 Agent。
- 不支持：同一对话里显式切换，输出以 `ROLE: EXECUTOR / TASK-xxx` 开头，只读 `roles/executor.md`、Task 及其 Context 列出的文件，Scope 外一律不碰，做完后回到调度身份。
- 无论哪种，**你作为调度器不得直接改业务代码、替 Reviewer 做审查、或自己解决复杂 blocker**。

## 停止条件（任一满足就停，不再自动推进）

- 需要用户业务决策，或需求/Task 与 Repo 现状矛盾
- 高风险、不可逆操作（生产数据删除、生产部署、改 Auth/支付）
- 重大架构冲突（Major Deviation 且 Architect 不能在既有授权内裁决）
- `max_tasks_per_run`、`max_rework_cycles`、`max_executor_retries` 到上限，且强模型根因分析轮数（`max_resolve_attempts`）已用尽
- 工作区有无法安全处理的冲突或高风险未提交改动
- Router / `claude-bridge` / 登录 / 额度 / 额外 usage 确认不可用
- 测试环境无法运行验证命令
- 用户说停

`devflow.py transition` 会自动执行三个次数上限，达到后直接转 `BLOCKED`，不依赖你"记得检查"。

## 汇报

完成或停下时汇报：已完成的 Task 列表、Validation（你亲自跑的）、Review 结论、剩余 blocker、下一步，以及本轮每次 Claude 调用的简短回执。只读 status 等未调用 Claude 的轮次不借用历史成功回执。不要贴整个计划或 diff。需要用户参与时，只问真正阻塞的那一个问题。

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
