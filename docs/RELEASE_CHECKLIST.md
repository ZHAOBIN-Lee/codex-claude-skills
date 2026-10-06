# 发布清单

[简体中文](RELEASE_CHECKLIST.md) · [English](en/RELEASE_CHECKLIST.md)

维护者在 2026-10-05 授权公开仓库，选择了 MIT。现在是 0.2.0 公开预览，还没有稳定版。没勾的就是没做。

## 源码与文档

- [x] 维护者确认源码没有借用外部代码；依赖的 Provider 是另一个仓库，署名在那里。
- [x] 采用 MIT，署名 ZHAOBIN-Lee；`skills/dev-orchestrator/` 里带许可副本。
- [x] 公开文件限定为经过审查的源码、离线测试、模板、说明和许可。
- [x] 不含作者本机路径、登录资料、真实会话、任务正文、日志和备份（维护者的公开署名除外）。
- [x] 旧版 `claude-bridge` 已移出主分支，保留在 `legacy-claude-bridge` tag。
- [ ] 各平台验证后更新兼容表。

## 运行验收

- [x] `devflow.py` 54/54 离线测试通过。
- [x] Claude 聊天派 GPT 子代理、GPT 聊天派 Claude 子代理各实测一次。
- [ ] 在练习项目里用三种执行模式各跑一次完整 `/dev`（方案 → 代码 → 验证 → 审查 → 返工）。
- [ ] 全新 clone 后用 Skill 安装器安装，资源齐全。
- [ ] 全新聊天里问“怎么用”，只给说明，不开始开发。
- [ ] 独立朋友照说明完成安装和第一次 `/dev`。

## GitHub

仓库：[ZHAOBIN-Lee/codex-claude-skills](https://github.com/ZHAOBIN-Lee/codex-claude-skills)。以后公开新内容前，复核文件、Git 历史、Actions 日志和附件。如果加 CI，只跑离线测试，不放个人账户或订阅凭据，第三方 Action 固定到核对过的提交，权限设为 `contents: read`。

公开后，已有的 fork 和副本改回私有也收不回来。见 [GitHub 官方说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)。
