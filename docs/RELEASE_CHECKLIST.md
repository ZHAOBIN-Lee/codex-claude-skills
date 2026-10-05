# 发布清单

[简体中文](RELEASE_CHECKLIST.md) · [English](en/RELEASE_CHECKLIST.md)

维护者在 2026-10-05 授权上传并公开仓库，选择了 MIT。现在是 0.1.0-draft 公开预览，还没有稳定版。这份清单把“公开预览已做到的”和“稳定版还要做的”分开；没勾的就是没做。

## 源码与文档

- [x] 维护者确认源码没有借用外部代码，已记录；文档写法参考另列。
- [x] 采用 MIT，署名 ZHAOBIN-Lee；每个可安装单元都带许可副本。
- [x] 公开文件限定为经过审查的源码、离线测试、通用模板、教程和许可。
- [x] 不含作者本机路径、登录账号资料、费用确认、真实会话、任务正文、日志和备份（维护者的公开署名除外）。
- [x] 本地文档引用和教程链接已核对；教程都放在 Skill 目录里，不依赖目录之外的文件。
- [x] 文档里写明个人配置放在安装目录之外；完整的升级保留流程还没实测。
- [ ] 提供可执行的首配流程，把 CLI 来源、版本、能力绑定好（现在靠手动照教程做）。
- [ ] 各平台完成运行层适配，并按验证结果更新支持表。

## 运行验收

- [x] Bridge 84／84、调度器 48／48 的离线测试通过（已有基线的结果）。
- [ ] 在全新 clone 上，通过 Codex 的 Skill 安装器只装核心 Skill，资源全部到位。
- [ ] 全新桌面聊天里问“怎么用”，给出本地教程，不调用 Claude。
- [ ] “帮我设置”“帮我排错”先走对应模式，不被当成推理请求。
- [ ] 首次真实调用、连续追问、切回 Codex，都符合用户的授权。
- [ ] 每次回执里的模型、会话、状态，和那次官方结果一致，凭证唯一对应。
- [ ] 失败、超时、费用未确认、权限拒绝、保存失败，都不会被报成成功。
- [ ] 升级、回滚、卸载后，已有的 CLI、账户历史和项目交接都还在。
- [ ] 独立朋友照着教程完成，不依赖作者电脑上的设置。

## GitHub

预览仓库：[ZHAOBIN-Lee/codex-claude-skills](https://github.com/ZHAOBIN-Lee/codex-claude-skills)。仓库已经公开，匿名 clone 并校验 82 个文件已完成。创建和公开有维护者的直接授权；邀请朋友、跑真实模型测试和发布稳定版，需要另行授权，这份清单不代表已经授权。

以后公开新内容前，要复核文件、Git 历史、Actions 日志和附件。如果加 CI，只跑离线测试，不放个人 Claude 账户或订阅凭据；第三方 Action 固定到核对过的提交，权限设为 `contents: read`，不自动做真实调用。

稳定版要有版本 tag／Release 和变更记录。首版以 claude-bridge 为核心；dev-orchestrator 先保持实验组件，等依赖安装和独立用户流程验证过再纳入稳定支持。

公开后，已有的 fork 和副本，改回私有也收不回来。见 [GitHub 官方说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)。
