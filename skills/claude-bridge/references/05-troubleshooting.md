# 调用失败与等待时间

[简体中文](05-troubleshooting.md) · [English](en/05-troubleshooting.md)

可以问：

```text
$claude-bridge 帮我解释这次失败。先检查本轮状态和必要元数据，不要自动重试，不要读取账号秘密。
```

排查从当前结果开始。只取需要的字段，不把完整认证配置、任务正文、会话内容或环境变量值贴进公开 issue。

## 常见情况

| 现象 | 先确认什么 | 处理方式 |
| --- | --- | --- |
| Codex 找不到 Skill | 目录、完整文件、Skill 校验与当前发现状态 | 对照本机安装说明；新机路由要实测 |
| CLI 路径或哈希不匹配 | runtime 指向的本机官方文件是否存在，是否升级过 | 核对官方安装及版本后更新自己的固定配置，不绕过校验 |
| `subscription_usage_credits_status_unconfirmed` | 使用者是否已确认自己的额外 usage credits 状态 | 用户检查费用设置，按真实确认记录；不继承作者确认 |
| `consult_usage_credits_user_confirmation_required` | 确认来源和日期是否有效 | 补充本人真实确认，不伪造日期或来源 |
| 非订阅或 Provider 路线被阻止 | 安全认证状态与返回的变量/字段名 | 用户自行处理官方登录；不打印变量值，不改走 API |
| effort 环境覆盖被阻止 | 是否存在非空 `CLAUDE_CODE_EFFORT_LEVEL` | 说明变量名与冲突，由用户决定自己的设置；不自动删除或绕过 |
| 模型不可用或达到限额 | 本轮 CLI 返回与实际账号额度 | 如实报告，回到已授权的 GPT 任务；不购买额外额度，不自动换模型 |
| 权限拒绝 | 本轮拒绝的精确操作是否在已有授权内 | 对应操作获得授权后再按正常权限处理，不扩大通配规则 |
| 项目忙或锁存在 | 是否还有同项目调用正在运行 | 等待或检查实际进程；不直接删锁，不并发修改 |
| `state_update_failed` | 推理是否完成、session 是否保存、哪些本地写入失败 | 分开汇报结果与保存状态，保留证据，不能假设继续增量成功 |
| 超时 | 是否只有等待结束，完成状态是否未知 | 标明未知，先检查必要元数据；不自动再发一遍导致重复任务 |

首次诊断、程序变化或检查失败可运行 Bridge `doctor`。正常连续咨询的 `run` 已包含检查，无需每一问额外跑它。Bridge `doctor` 与官方 CLI 的 `claude doctor` 是不同检查工具。

## Claude 好像忘了背景

先看本轮返回的 `session_id`、`resumed_session`、`context_delivery`、变更及截断元数据。新会话、模式改变或失效基线可导致 full 发送；不能仅凭 `.ai/consult.json` 存在认定已经恢复。

咨询只读取规定范围的摘要、规则与 Git 快照。新增资料、未跟踪文件或摘要被截断的部分需要明确提供。`truncated_context_names`、`unavailable_context_names` 应如实说明；指纹是变化检测，不是完整阅读证明。适用规则超出允许总量时应阻止，不静默截断。

## 为什么感觉还慢

等待分成三段：Codex 生成调用前、Bridge/Claude 执行、Codex 收到结果后。Bridge 的检查和 `cli_wall_ms` 只覆盖脚本内部分，不能证明整个聊天只花这些时间。

连续咨询通过固定项目会话、增量材料、单次 `run` 和按需核对减少重复步骤。长聊天、Codex 原生强度、模型回答长度及网络仍会影响等待。Claude 的 effort 参数不会更改 Codex 原生强度。

官方结果自报时长可能是会话累计口径。不要把 `duration_api_ms` 与当轮 wall time 相减估算启动开销；比较当轮 CLI 执行用 Bridge 的单调时钟字段，比较用户等待用聊天事件。`--progress` 只显示阶段元数据，不是流式首 token 测量。

真实验证包含短咨询与长方案。新版回执规则已有一次真实 Sonnet 调用验证；其中一次长方案 CLI wall 约 176.5 秒、脚本检查约 350 毫秒。这是该次结果，不代表固定速度，也不验收所有新机器安装路线。

## 报 issue 可提供什么

提供操作系统、Python 版本、Bridge 版本或 commit、官方 CLI 版本、运行模式、匿名化状态/reason、必要计时字段与复现步骤。日志里的绝对路径、完整会话 ID 及项目元数据可能涉及隐私；先检查再公开。不要上传 runtime、认证文件、API Key、Token、Cookie、完整会话或业务资料。
