<!-- BEGIN CODEX_CLAUDE_BRIDGE -->
## Codex / Claude 项目交接

保留此项目原有 `CLAUDE.md` 全部内容；下列导入仅在已授权的项目中增量加入。

@.ai/PROJECT_CONTEXT.md
@.ai/DECISIONS.md
@.ai/HANDOFF.md

先阅读本项目 `AGENTS.md` 和以上交接文件，核对实际 Git HEAD、status、diff 及当前任务文件。如果对用户提出的问题或者方案有任何疑问或不清楚的地方，及时反问，不要直接开始。

仅执行本轮明确授权范围。保留用户现有变更和官方权限，不自动 commit/push/部署，不使用破坏性 Git 操作，不升级软件或重启正在工作的桌面应用。

GPT 和 Claude 串行修改项目。不要自行编辑 `.ai/HANDOFF.md`、`.ai/sessions.json`、`.ai/logs/` 或 `.ai/backups/`；这些文件由 Bridge 管理。完成后返回结构化状态，由 Bridge 先备份再记录 Handoff，GPT 独立核验实际文件和测试后补充结论。不得保存秘密或隐藏推理。

向 Codex 返回：Task、Summary、FilesChanged、Tests、Decisions、RemainingIssues、RecommendedNextStep。列出实际变更、测试命令和结果、决策、未验证事项、权限拒绝和下一步；说明实际成功与未完成部分，不因某个步骤成功就声称整个任务完成。
<!-- END CODEX_CLAUDE_BRIDGE -->
