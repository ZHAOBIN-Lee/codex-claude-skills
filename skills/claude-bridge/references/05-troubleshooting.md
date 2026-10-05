# 调用失败与等待时间

[简体中文](05-troubleshooting.md) · [English](en/05-troubleshooting.md)

出问题了，可以这样问：

```text
$claude-bridge 帮我解释这次失败。先检查本轮状态和必要元数据，不要自动重试，不要读取账号秘密。
```

排查从这次的结果看起，只取需要的字段。公开 issue 里不要贴完整的认证配置、任务正文、会话内容或环境变量的值。

## 常见情况

| 现象 | 先确认什么 | 怎么处理 |
| --- | --- | --- |
| Codex 找不到 Skill | 目录和文件是否完整，Skill 格式校验，当前的发现状态 | 对照[首次设置](01-setup.md)的安装部分；新机器的路由要实际试过才算数 |
| CLI 路径或哈希不匹配 | runtime 指向的官方文件还在不在，是不是升级过 | 核对官方安装和版本，再更新你自己的固定配置，不要绕过校验 |
| `subscription_usage_credits_status_unconfirmed` | 你有没有确认自己账号的额外 usage credits 状态 | 去检查费用设置，按真实情况记录。作者的确认不能继承 |
| `consult_usage_credits_user_confirmation_required` | 确认的来源和日期是否有效 | 补上你本人的真实确认，不要编日期和来源 |
| 非订阅或 Provider 路线被拦 | 认证状态，以及返回的变量名、字段名 | 自己处理官方登录。不打印变量的值，也不改走 API |
| effort 环境变量覆盖被拦 | 有没有非空的 `CLAUDE_CODE_EFFORT_LEVEL` | Codex 会说出变量名和冲突，设置怎么改由你决定，它不会自动删或绕过 |
| 模型不可用，或额度用完 | 这次 CLI 的返回和账号的实际额度 | 如实报告，回到已授权的 GPT 任务。不买额外额度，不自动换模型 |
| 权限被拒（`needs_permission`） | `permission_denials_status` 和被拒的具体操作在不在已有授权内 | 先查实际文件。已有授权覆盖该精确操作时，补上精确规则再另行发起新调用；不放宽通配规则。见[权限与失败处理](08-permissions-and-failures.md) |
| `declared_output_edit_permission_unconfirmed` | 每个 `--output` 的预检结论：`missing_rule`、`deny_or_ask_may_apply` 还是 `unknown` | 推理没有发生。适用的 deny/ask 是保护，要遵守，不要删除或绕过。若是已授权且不冲突的范围，可以检查并补上精确的 `Edit(/路径)`（`Write(路径)` 和裸 `Edit` 都不算精确授权）；真要改保护性策略，需要用户本人按现有权限来决定。见[权限与失败处理](08-permissions-and-failures.md) |
| `max_turns_out_of_bounds`、`timeout_out_of_bounds` | 返回里的 `allowed_range`（max-turns 1..20，timeout 大于 0 且不超过 3600） | 改成范围内的值。调用没有发生 |
| `claude_stream_malformed_frame`、`claude_stream_final_result_unavailable` | 流里有无法解析的行，或没有最终结果 | 当作未完成，先看实际文件。没有最终结果就没有模型和会话证据 |
| 项目忙，或有锁 | 同一项目是不是还有调用在跑 | 等它，或者看看实际进程。别直接删锁，也别并发修改 |
| `state_update_failed` | 推理完成没有，会话存了没有，哪些本地写入失败 | 结果和保存状态分开说，留好证据。别假定后面还能增量接续 |
| 超时 | 是只有等待结束了，还是确实没完成 | 标明完成情况未知，先查实际文件和必要的元数据。不要静默重发，免得任务重复；确要再做，说明范围另行发起 |

第一次诊断、程序有变化、或者检查失败时，可以跑 Bridge 的 `doctor`。平时连续咨询，`run` 自己已经带了检查，不用每问一次就跑。Bridge 的 `doctor` 和官方 CLI 的 `claude doctor` 是两个不同的工具。

## Claude 好像忘了背景

先看这次返回的 `session_id`、`resumed_session`、`context_delivery`，以及变更和截断的元数据。新会话、换了模式、基线失效，都会让 Bridge 重发完整上下文。光凭 `.ai/consult.json` 存在，不能认定会话已经恢复。

咨询只会带上规定范围内的摘要、规则和 Git 快照。新增的资料、没被跟踪的文件、被截断的部分，要你明确提供。`truncated_context_names`、`unavailable_context_names` 里列出的，如实告诉你。指纹只能发现变化，证明不了 Claude 读完了整份内容。适用的规则超出允许的总量时，应该直接阻止，不能悄悄截断。

## 为什么还是觉得慢

等待分三段：Codex 生成调用之前、Bridge 和 Claude 执行中、Codex 收到结果之后。Bridge 的检查耗时和 `cli_wall_ms` 只覆盖脚本里的那部分，整个聊天花了多久，它们量不出来。

连续咨询靠固定的项目会话、增量材料、一次 `run` 和按需核对，减少重复步骤。聊天太长、Codex 原生强度、回答篇幅和网络，仍然会影响等待。Claude 的 effort 参数，不会改 Codex 的强度。

官方结果里自报的时长，可能是整个会话的累计值。别拿 `duration_api_ms` 去减当轮的 wall time 来估启动开销。想看当轮 CLI 执行用了多久，看 Bridge 的单调时钟字段；想看你实际等了多久，看聊天里的事件时间。`--progress` 只输出阶段元数据，不是首个 token 的流式计时。

维护者在 macOS 上用真实 Sonnet 调用验证过现行回执规则。其中一次长方案咨询，CLI wall 大约 176.5 秒，脚本检查大约 350 毫秒。这只是那一次的观测，不是速度承诺，也说明不了其他机器的安装路线。

## 报 issue 时写什么

请提供：操作系统、Python 版本、Bridge 版本或 commit、官方 CLI 版本、运行模式、脱敏后的 status/reason、必要的计时字段和复现步骤。日志里的绝对路径、完整会话 ID 和项目元数据可能涉及隐私，先检查再公开。不要上传 runtime、认证文件、API Key、Token、Cookie、完整会话或业务资料。
