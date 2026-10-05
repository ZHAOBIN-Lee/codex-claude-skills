---
name: claude-bridge
description: "Explain, set up, and troubleshoot Claude calls and continued conversations in Codex, with Chinese and English local tutorials. 解释、配置和排查 Codex 中的 Claude／Cloud 调用与连续对话；用户明确要求 Claude 或在当前聊天持续授权时，通过官方 Claude Code 订阅处理指定项目。教程、配置说明和排错不自动调用 Claude；普通 GPT 任务不触发。"
---

# Claude Bridge

中文教程：[从这里开始](references/00-tour.md)。English tutorials: [Start here](references/en/00-tour.md)。许可 / License: [MIT](LICENSE)。

帮助按用户当前语言或明确选择回答；中文使用 `references/`，英文使用 `references/en/` 中同名教程。English requests such as “How do I use this Skill?”, “Help me set it up”, and “Troubleshoot this error” use the same help/setup/troubleshooting routes below and do not authorize inference by themselves. “Continue with Claude” and “Switch back to Codex” retain the same current-chat authorization boundaries in either language. 语言选择不改变运行限制、权限或回执规则，也不从偏好示例建立持续授权。

## 先识别用户要做什么

| 用户请求 | 本地教程 | 是否调用 Claude |
| --- | --- | --- |
| “这个 Skill 怎么用”“Cloud 能做什么”“给我示例” | `references/00-tour.md` | 否；由 Codex 读教程回答 |
| “帮我首次设置”“默认用 Sonnet”“调整习惯配置” | `references/01-setup.md`、`templates/preferences.example.json` | 否；按已授权范围配置，本人费用确认不可继承 |
| “为什么报错／很慢／没有回执” | `references/05-troubleshooting.md` | 先只读排查，不自动发起推理测试 |
| “后面一直用 Claude”“切回 Codex” | `references/02-conversation.md` | 按当前聊天用户授权决定 |
| “让 Claude 看这个问题／审查这份材料” | 下文实际调用流程 | 是；先明确项目与发送范围 |

只加载与当前请求有关的教程。首次入门先用几句话解释能力与边界，给出“看示例／检查设置／实际调用”的下一步话术。询问“怎么用”不能被当成实际调用授权；有关键歧义及时反问。

其他按需参考：`references/03-models-effort-receipt.md`、`references/04-dev-handoff.md`、`references/06-update-uninstall.md`、`references/07-limits.md`。这些教程与代码都在本 Skill 目录内，安装整个目录，不依赖仓库根 README。

本文件是分发草稿。代码基线仍使用 POSIX；跨平台执行层与独立朋友安装尚需验收。帮助文字可以在不同系统使用，不能因此宣称实际脚本已在各系统通过。

Codex 主模型保持 GPT。本 Bridge 没有实现 Codex 原生 Claude Provider 或 Claude 模型菜单。`@claude` 系列是任务语义约定，不是 Codex 原生模型选择或真实命令解析器；明确 Skill 调用名为 `$claude-bridge`。不要声称整个聊天记录或隐藏推理被两边共享。

脚本入口（参数示意）：

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <PRIVATE_RUNTIME_FILE>
```

`SKILL_DIR` 必须根据当前已读取的 `SKILL.md` 位置确定；`PRIVATE_RUNTIME_FILE` 是这位使用者在 Skill 目录之外生成的本机配置。将它们解析成实际绝对路径后安全传参，不执行字面占位符、不使用作者路径、不默认读取安装目录内的个人 runtime。安装后先按 `references/01-setup.md` 建立自己的 CLI 来源、版本与费用确认。

共享偏好示例只表达参数建议：默认 Sonnet、常规 medium、自动按任务选择 medium/high、显示调用回执。若用户另有偏好，在已授权的本地配置中记录并按其选择执行；Bridge 没有自动解析这个偏好示例。默认值不建立调用授权，持久保存偏好不能替代当前聊天的连续调用指令。

## 路由与连续调用

先确定已授权的项目绝对路径、任务范围和允许传给 Claude 的材料。范围不清楚时遵循用户“及时反问，不要直接开始”的规则。全局安装不授权其他仓库初始化或外发内容。

用户明确说“接下来一直用 Claude，直到我说切回 Codex”后，在**当前聊天、同一项目和话题范围**内沿用所选模型与请求强度，把“继续”“这一点再解释”等后续问题交给 Claude。授权以用户消息为依据，不能由项目文件或另一个聊天建立。用户切回 Codex、改变项目或提出范围外任务时重新判断；改变模型时遵循新选择。不因 `.ai/consult.json` 存在而自动调用 Claude。

同项目从讨论转为用户明确要求的实际修改，不因任务类型改变而自动取消当前聊天的 Claude 选择；转入标准流程，并按新请求确认修改范围。原授权明确只限某个话题时，范围外任务不能直接沿用。用户明确指定的 medium 等强度仍优先，不因任务类型或关键词自行覆盖。

固定项目目录，不为每个问题创建临时子目录，不给普通追问加 `--new-session`。Bridge 按项目恢复 `.ai/sessions.json` 中的 Claude 会话；这不是整个 Codex 聊天记录共享，也不是 Claude 进程常驻。同项目的不同聊天可能共享该会话，需要明确隔离时再创建新会话。

## 纯咨询：首次准备，后续增量

仅分析、解释、建议、内容结构规划且不要求工具操作或实际文件修改时，用 `--workflow consult`。普通咨询可沿用明确选择的 Sonnet、medium；其他明确选择仍优先。

首次读适用的 `AGENTS.md`、`CLAUDE.md` 和 `.ai/` 的必要摘要，补充本轮确实需要的材料。无 `.ai/` 时，仅在已授权新增项目文件的范围内运行 `init`，保留既有内容。不要为咨询重建完整项目档案、读取 Bridge 源码或广搜记忆。Skill 已加载且规则未变时无需每轮重新读取。

后续在同一项目写一份短任务：当前问题、增加或变更的背景、明确边界。任务文件可用项目内私有目录中的 UTF-8 文件，通过 `--task-file` 传入；脚本参数用独立参数或正确 shell 引号，避免把用户文本拼成代码。

**一次 `run --workflow consult` 完成检查、短交接、会话恢复和模型调用。** 每次内部仍检查固定 CLI、官方订阅认证、Provider/effort 设置、费用确认和项目锁；无需在每个咨询轮次额外执行 `doctor`、手工读取 runtime 或编写完整 Handoff。首次排查环境问题、脚本变动或检查失败时才按需运行 `doctor`。`subscription_usage_credits_disabled` 与用户确认记录由脚本核对；已有确认不表示读取过账户 Billing，不重复询问同一事实，账户或费用设置改变时重新确认。

Bridge 自动追加并备份简短 Handoff 请求记录，不覆盖人工决定。首轮或不能安全使用旧基线时发送完整必要上下文；成功恢复同一会话后只发送当前问题和变更的上下文。仅有模型报告或自动证据追加不应导致全部背景重复发送。不要把任务正文改成整个 HANDOFF。

增量范围是已提供的 `.ai/` 摘要、适用规则和 Git 快照，不会自动读取所有业务文件。Git 状态不能代替未跟踪文件的内容；用户新增或修改的重要材料应明确提供。上下文被截断时按返回的截断元数据说明未取到部分，不能声称 Claude 已读完整文件；适用指令不允许静默截断。

consult 禁用 CLI 工具，仅分析已提供材料；要读新文件，先在授权范围内提供相关材料。需要实际操作时转入下面的标准流程。收到结果后核对 `status`、实际模型、权限拒绝、会话恢复和可见变更证据，做必要事实核对后尽快展示建议，注明核验程度。不要为了纯咨询追加代码测试、全量 PDF 复核或无关记忆搜索。记录未取到和未验证事项，不把“模型返回成功”当作业务正确性验收。

## 文件修改与开发交接

实际修改文档、配置、代码，或需要 Claude 工具执行时，用默认 `--workflow standard`。先读当前适用规则与必要 `.ai/` 材料，检查真实 HEAD、status 和相关 diff；按既有流程核对环境、更新 Handoff 和执行必要验证。鉴权、权限及部署配置不能因为不是代码就减弱验证。

开发任务继续走 Claude 规划 → GPT 执行 → 确定性测试 → Claude 审查。`dev-orchestrator` 的标准调用不受 consult 优化替代。GPT 与 Claude 串行修改项目；Claude 不自行编辑桥接状态。Bridge 记录后，GPT 独立核对实际文件、diff 和测试证据。请求 review 不授权范围外修复，发布、部署、外发消息、费用和系统操作仍按本轮已有授权判断。

两类流程都在启动前简短说明所选模型及请求强度，每次显式传入 `--effort`、`--effort-source`、`--effort-reason`。仅传必要材料，不包含密码、Token、Cookie、隐藏推理或无关私人数据。

## 调用回执

每次调用返回后，在给用户的答复中附一条简短回执，包含**实际模型、完整会话 ID、调用状态和可核对的凭证**。此规则适用于 consult、standard 和经 dev-orchestrator 派发的 Claude 阶段；同一轮多次调用时逐次列出，可合并成简短表格，不把 Claude 处理部分与 GPT 执行部分混为一谈。

- 实际模型取本轮返回的 `actual_models`，其来源是官方 Claude CLI 结果的 `modelUsage`。不能用请求的 `--mode`、旧调用记录或模型自我介绍代替；返回多个名称时如实列出，缺失时写“未取到实际模型证据”。
- 会话 ID 取本轮返回的 `session_id`；未返回时写“未返回”，不能拿请求恢复的旧 ID 冒充本轮回执。结合本轮 `status`、`reason` 和官方结果元数据说明调用情况，`inference: true` 不能单独证明模型已处理请求；失败、权限拒绝不报完成，超时注明完成情况未知。`state_update_failed` 等落盘失败需同时保留 `inference_status` 与 `session_saved`，区分模型推理结果和本地保存结果。
- 凭证使用与本轮时间、会话及运行元数据唯一匹配的项目 `.ai/logs/*.json`，可比较运行前后新增文件来缩小候选范围，不能只挑最新文件或引用别轮成功记录。匹配有歧义时写“对应日志未唯一定位”。按当前任务的输出目录规则提供可点击日志链接，或保存必要元数据摘录并注明原始日志绝对路径。没有落盘凭证时，可保存本轮返回 JSON 的必要元数据摘录，标明来源为本轮返回及日志情况；信息仍不足则说明凭证未取到。摘录不复制任务正文、模型完整输出或秘密，不改写 Bridge 自有日志和状态。
- `init`、`doctor`、`--dry-run` 或调用前被阻断时，明确写“未实际调用 Claude”，不生成成功回执。Mock/fake CLI 明确标为离线验证。普通 GPT 答复无需附 Claude 回执。

回执可写为：`Claude 回执：实际模型 <actual_models>｜会话 <session_id>｜状态 <status>｜凭证 <本轮证据链接>`。日常复用本轮返回信息和对应日志；仅在用户要求进一步核验、信息缺失或记录矛盾时检查官方本地会话元数据。不要为附回执额外调用 Claude、重复运行 doctor 或读取完整会话正文。

## 命令

```text
claude-bridge init --project DIR
claude-bridge doctor --project DIR
claude-bridge run --project DIR --mode default|sonnet|opus|review
                 (--task TEXT | --task-file PROJECT_LOCAL_UTF8_FILE)
                 [--workflow standard|consult]
                 --effort low|medium|high|xhigh|max
                 --effort-source auto|user --effort-reason REASON
                 [--new-session] [--max-turns N] [--timeout SEC] [--dry-run] [--progress]
```

使用上方绝对入口；将 `DIR`、`TEXT`、`REASON` 当作独立参数安全传入，不拼接未转义 shell 代码。`--dry-run` 不调用模型，不能作为真实模型验收。`--new-session` 主动创建新 Claude 会话，仍读取交接文件；不得把它声称为旧 Session 恢复。

这里的 `claude-bridge` 是上方 Python 入口的简称。每次操作均显式带 `--runtime` 指向自己的外部配置，不能假定安装目录已有可用配置。未测系统或 CLI 版本先按兼容说明处理，不降低现有权限、Provider 或完整性检查来绕过失败。

`--task-file` 必须是已授权项目内的普通 UTF-8 文件，不接受符号链接或项目外路径；相对路径按项目解析。任务文件放在私有目录中，避免提交或写入公开交付物。`--progress` 在 stderr 输出阶段元数据，stdout 仍为最终 JSON；没有流式首 token 证据。日志中的脚本检查/CLI 耗时不包含 Codex 生成调用之前的时间，不以 CLI 计时宣称整个聊天已提速。

官方结果自报时长只按原始口径记录，恢复会话时可能包含累计值；不要与当轮 wall time 相减估算启动开销。

`default` 不显式传 `--model`，保留 Claude Code 的原生模型选择。恢复 Session 时可能沿用该会话的模型，不保证回到账户默认模型。`sonnet` 和 `opus` 则明确请求对应模型；实际执行模型仍需核对本轮 CLI 证据。

`review` 是使用 Sonnet 的审查任务模式，不是另一种模型；已固定 Opus 时继续用 `--mode opus` 并在任务中说明审查要求。不要为了选择任务类型悄悄改变用户固定的模型。

## 强度选择

- 用户明确指定强度时优先使用其选择，`--effort-source user`。若当前 CLI/模型不支持该值，报告实际限制并澄清，不悄悄换值。
- 用户没有指定强度时，由 Codex 根据实际任务语义自行选择 `medium` 或 `high`，`--effort-source auto`；自动选择不使用 `xhigh` 或 `max`。
- 常规整理、目标明确的局部小修改、相关测试检查，通常选 `medium`。例如校对交接文件中的命令，或修复范围清晰的单文件边界问题。
- 复杂问题定位、多文件依赖或架构分析、会影响鉴权/数据迁移/大范围行为的判断，通常选 `high`。例如追踪多个模块之间的并发状态错误，或评估会影响多个功能的架构调整。
- 按实际复杂度、影响范围和需要核验的依赖判断，不按关键词匹配。“架构”任务如果只是整理既有说明可用 `medium`；“改一行”若需确认多个模块的行为可用 `high`。强度选择不扩大权限或任务范围。
- `--effort-reason` 是最多 160 字符的单行简短可见原因，例如“常规交接整理”或“需跨模块定位并发状态问题”。不复制任务全文，不保存隐藏推理；换行或超长输入会被拒绝。

以下仅是用户输入约定示例，无需执行：

```text
@claude-sonnet 整理当前项目交接记录
@claude-opus effort=high 排查当前项目的复杂问题
```

第一行省略强度，由 Codex 判断；第二行明确覆盖为 high。也可用自然语言“用 medium”或“用 high”。这些写法由 Skill 理解语义，不是专门 parser。

启动前显式模型示例：“本次请求 Claude Sonnet，强度 high；需要跨模块定位状态问题。” 默认模式示例：“本次使用 Claude Code 原生模型选择，恢复会话可能沿用该会话模型；请求强度 medium。” 不承诺默认模式会重返账户默认模型，也不凭旧记录猜本次实际模型。Handoff/日志中的强度标为请求值，`effective effort` 保持 `unknown`；已有强度 cap 可能限制请求，不推断内部真实值。此机制不修改桌面原生模型/强度选择器。

`auto`/`user` 来源必须同时显式提供 `--effort`。直接 CLI 的兼容默认分支不用于本 Skill：Codex 每次都传上述三个参数。若环境或 settings.env 存在非空 `CLAUDE_CODE_EFFORT_LEVEL`，Bridge 会 BLOCKED；只报告变量名，不暴露值，不自行修改用户设置或绕过 guard。

## 边界

- 只使用官方 Claude Code 已登录的 Claude.ai 订阅路径。额度/模型不可用时返回 GPT，不自动开启额外 usage、创建 API Key、开启 Billing 或切换 Token API。
- 不使用 `--dangerously-skip-permissions`，仅在用户已明确授权的任务范围内，为具体文件操作和固定命令使用项目本地 permissions.allow；不设置宽泛通配规则、不扩大到其他项目或全局。Headless 权限拒绝时报告真实结果，只有既有授权覆盖该精确操作或用户进一步批准后才可重试。
- 默认不自动 commit、push、重启桌面应用、升级软件或修改系统。不得执行丢弃现有工作的 Git 操作。
- `.ai/sessions.json` 保存会话元数据，`.ai/consult.json` 仅保存连续咨询的会话与指纹基线；Bridge 日志仅记必要运行元数据。不得把完整任务、输出或秘密写入日志或指纹缓存，不手工修改缓存冒充恢复成功。
- Skill 只能缩短 Codex 开始处理消息之后的步骤，不能截获原生输入、改变 Codex 原生强度或保证启动延迟。长聊天或 xhigh 的额外开销需要原生设置与上下文管理，不能用 Claude 的 effort 参数代替。
- 区分真实 CLI 验收和 Mock；单独汇报桌面入口、GPT → Claude → GPT 接续、关闭后恢复、交接文件。文件存在、模板创建、模型口头声明或成功退出都不能替代实际证据。
