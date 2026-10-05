# 模型、强度与调用回执

[简体中文](03-models-effort-receipt.md) · [English](en/03-models-effort-receipt.md)

直接说就行：“用 Claude Sonnet、medium 处理这一步”，或者“用 Claude Opus、high 评估这个问题”。调用前 Codex 会简短说明请求的模型和强度，调用后附一条能核对的回执。

默认偏好是 Sonnet、medium。这是 Skill 遵循的偏好，不是 Bridge 新增的解析参数，也不会改桌面端的模型菜单。你指定了别的，就按你的来。

## 模型参数

| `--mode` | 做什么 | 注意 |
| --- | --- | --- |
| `sonnet` | 明确请求 Sonnet | 你的账号和 CLI 允许不允许，看实际返回 |
| `opus` | 明确请求 Opus | 不保证每个套餐、每次请求都能用 |
| `default` | 不传 `--model` | 恢复旧会话时，可能沿用那个会话的模型，不一定回到账号默认模型 |
| `review` | 用 Sonnet 做审查任务 | 这是任务模式，不是另一个模型。已经固定用 Opus 的话，用 `opus`，在任务里写明审查要求 |

`@claude`、`@claude-sonnet`、`@claude-opus` 是写给 Skill 看的自然语言写法，Codex 原生模型菜单里没有它们，也没有专门的命令解析器。明确调用这个 Skill，用 `$claude-bridge`。

## 强度怎么定

你说了强度，就用你的，记作 `--effort-source user`。没说，Codex 按任务实际难度选 `medium` 或 `high`，记作 `auto`，自动选择不会用 `xhigh` 或 `max`。

常规整理、边界清楚的局部任务，一般选 medium；跨模块的问题、影响面大的判断，一般选 high。这是按任务判断的，不是看关键词。你指定的值如果当前模型或 CLI 不支持，Codex 会告诉你并跟你确认，不会悄悄换一个。

每次调用，Skill 都会显式传 `--effort`、`--effort-source`、`--effort-reason`。原因是一行不超过 160 字符的说明，不放任务正文，也不放隐藏推理。日志里的 requested effort 是你请求的值，effective effort 一直记作 `unknown`：已有的上限可能压低请求，所以不能从参数反推 Claude 内部实际用了多少。Claude 的强度参数也改不了 Codex 自己的强度。

## 怎么确认 Claude 真的被调用了

每次真实调用后，Codex 的回答里应该有这样一行：

```text
Claude 回执：实际模型 <本次 actual_models>｜会话 <本次完整 session_id>｜状态 <本次 status>｜凭证 <本次证据链接>
```

尖括号是字段占位符，这行示例本身不是一次调用的证据。

- **实际模型**取自这次 Bridge 返回的 `actual_models`，来源是官方 CLI 的 `modelUsage`。请求的 mode、模型的自我介绍、历史记录都代替不了它。没取到，就写“未取到实际模型证据”。
- **会话 ID**用这次返回的完整 `session_id`。没返回，就写“未返回”，不能拿请求恢复的旧 ID 顶替。
- **状态**要结合这次的 `status`、`reason` 和官方结果来判断。单看 `inference: true` 说明不了任务处理完了。失败、被拒绝、超时，都不能报成完成。
- **凭证**要和这次的时间、会话、运行元数据唯一对上。别只挑最新的日志，也别拿别次成功的记录凑数。对应不唯一，就如实说。

项目里的 `.ai/logs/*.json` 是 Bridge 必需的运行元数据。Codex 可以直接链接这次对应的日志，也可以按当前任务的输出目录规则，另存一份不含任务正文、完整回复和秘密的元数据摘录。摘录要注明来自这次返回，并写清原始日志位置。Bridge 自己的日志不要改。公开教程里不放个人项目的日志，也不放真实账号的会话 ID。

本地保存出问题时，推理结果和保存结果要分开说。比如 `state_update_failed`，要同时给出 `inference_status` 和 `session_saved`：模型可能已经答完了，只是本地状态没全写成。没有落盘日志，就不要凭空造一条成功日志。

## 多次调用，和没调用的情况

同一轮里规划、审查等多次 Claude 调用，每次都附回执，可以合成一张表，并把 GPT 执行的部分分开写。`init`、`doctor`、`--dry-run`，或者调用前就被拦下的操作，要明说“未实际调用 Claude”。fake CLI 测试标成离线验证。普通的 GPT 帮助不需要 Claude 回执。

日常的回执，用这次的返回结果和对应日志就够了。只有你要求进一步核对、信息缺失或记录互相矛盾时，才去查官方本地会话元数据。不要为了补一张回执，再去调用一次 Claude，或者读完整的会话正文。
