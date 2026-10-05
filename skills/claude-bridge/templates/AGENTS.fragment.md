<!-- BEGIN CODEX_CLAUDE_BRIDGE -->
## Codex / Claude 项目交接

如果对我提出的问题或者是方案有任何的疑问或者是不清楚的地方，要及时反问我，不要直接开始。

该片段仅增量加入已获用户授权的项目，保留原有 `AGENTS.md` 全部内容。项目原有规则和用户本轮授权继续适用。

- 默认由 Codex / GPT 执行。仅当用户明确请求 `$claude-bridge`、`@claude`、`@claude-sonnet`、`@claude-opus` 或 `@claude-review` 时使用本机 Claude Bridge。
- 这些字符串是 Skill 任务约定，不是原生模型菜单；是否被当前桌面会话发现须实际验证。
- 任务开始和模型交接前先读 `.ai/PROJECT_CONTEXT.md`、`.ai/DECISIONS.md`、`.ai/HANDOFF.md`，核对实际 Git HEAD、status、diff 及任务文件。
- 调用 Claude 前由 GPT 更新 Handoff；GPT 暂停本项目编辑。Claude 返回结构化结果，不自行编辑 Handoff；Bridge 备份后记录本轮结果，GPT 核对实际变更和测试并补充验证结论，再继续任务。
- 只发送本任务必需、已经授权的项目内容。不保存凭据、隐藏推理或无关私人数据。
- 保留官方权限和原生订阅登录；不自动创建 API Key、开启 Billing/额外 usage、扩大工具权限或更换 Provider。
- 未完成或未取得证据写明状态；不要把文件存在、Mock 或模型完成声明当成 PASS。
<!-- END CODEX_CLAUDE_BRIDGE -->
