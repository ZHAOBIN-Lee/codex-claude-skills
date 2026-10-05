# 模型、强度与调用回执

[简体中文](03-models-effort-receipt.md) · [English](en/03-models-effort-receipt.md)

你可以直接说：“用 Claude Sonnet、medium 处理这一步”，或者“用 Claude Opus、high 评估这个问题”。Codex 应在调用前简短说明请求模型和强度，返回后给出可核对的实际调用回执。

## 模型参数

| `--mode` | 请求行为 | 需要注意 |
| --- | --- | --- |
| `sonnet` | 显式请求 Sonnet | 当前账户与 CLI 是否允许，以实际响应为准 |
| `opus` | 显式请求 Opus | 不保证每个套餐、每次请求都可用 |
| `default` | 不显式传 `--model` | 恢复会话可能沿用旧会话模型，不保证回到账户默认模型 |
| `review` | 使用 Sonnet 的审查任务模式 | 它是任务模式；已固定 Opus 时用 `opus` 并在任务中写审查要求 |

`@claude`、`@claude-sonnet`、`@claude-opus` 是自然语言约定，由 Skill 理解；不是 Codex 原生模型菜单、专用命令解析器或新的 Provider。明确调用这份 Skill 的名字是 `$claude-bridge`。

## 强度怎样决定

用户明确指定的强度优先，标记为 `--effort-source user`。没有指定时，Codex 根据实际复杂度选择 `medium` 或 `high`，标记为 `auto`；自动选择不使用 `xhigh` 或 `max`。

常规整理和边界清楚的局部任务通常可选 medium；跨模块问题或高影响判断通常选 high。这是任务判断，不是关键词匹配。用户指定值若不被当前模型或 CLI 支持，应报告限制并澄清，不悄悄换值。

Skill 每次显式传入 `--effort`、`--effort-source`、`--effort-reason`。原因是最多 160 字符的单行说明，不复制任务正文或隐藏推理。日志中的 requested effort 是请求值，effective effort 仍为 `unknown`；已有 cap 可能限制请求，不能由参数推断内部实际强度。Claude effort 参数也不修改 Codex 原生强度。

## 怎样确认真的调用了 Claude

每次真实调用的答复应附上：

```text
Claude 回执：实际模型 <本轮 actual_models>｜会话 <本轮完整 session_id>｜状态 <本轮 status>｜凭证 <本轮证据链接>
```

这里的尖括号是字段占位符，示例本身不是一次调用证据。

- **实际模型**来自本轮 Bridge 返回的 `actual_models`，其来源是官方 CLI `modelUsage`。不能用请求的 mode、模型自我介绍或历史记录代替；缺失时写“未取到实际模型证据”。
- **会话 ID**使用本轮返回的完整 `session_id`。缺失时写“未返回”，不能用请求恢复的旧 ID 冒充。
- **状态**结合本轮 `status`、`reason` 与官方结果判断。`inference: true` 单独不能证明任务已处理；失败、拒绝或超时不能报完成。
- **凭证**与本轮时间、会话及运行元数据唯一匹配。不能仅取最新日志或拿别轮成功记录替代；定位不唯一时如实说明。

项目 `.ai/logs/*.json` 是 Bridge 必要运行元数据。Codex 可链接到本轮对应日志，或按当前输出目录规则保存不含任务正文、完整回复或秘密的必要元数据摘录。摘录须注明本轮返回来源和原始日志位置，不改写 Bridge 自有日志。公开教程不附带个人项目日志或真实账号会话 ID。

本地保存失败要同时解释推理和保存结果。例如 `state_update_failed` 应保留 `inference_status` 与 `session_saved`；模型可能已完成，但本地状态写入未全部成功。没有落盘日志时，不得伪造一条成功日志。

## 多阶段与未调用场景

同一轮规划、审查等多次 Claude 调用逐次附回执，可合并成表格，并区分 GPT 执行部分。`init`、`doctor`、`--dry-run` 或调用前被阻断，应明确“未实际调用 Claude”；fake CLI 测试应标为离线验证。普通 GPT 帮助无需 Claude 回执。

日常回执复用本轮结果和对应日志。只有用户要求进一步核验、信息缺失或记录矛盾时才核查官方本地会话元数据；不要为了附回执额外调用 Claude 或读取完整会话正文。
