# 朋友试用与发布清单

[简体中文](RELEASE_CHECKLIST.md) · [English](en/RELEASE_CHECKLIST.md)

维护者已于 2026-10-05 明确授权上传并公开仓库。本清单区分公开预览与正式版本验收；没有勾选的事项仍未完成。

## 源码与文档

- [x] 维护者确认没有借鉴外部来源；记录项目来源。
- [x] 选择 MIT 和版权署名 ZHAOBIN-Lee，各安装单元包含许可副本。
- [x] 公开文件限定为白名单源码、离线测试、通用模板和教程。
- [x] 不包含作者本机路径、登录账号资料、费用确认、真实会话、任务正文、日志与备份；维护者公开署名除外。
- [x] 核对本地文档引用及教程链接；不依赖 Skill 安装目录之外的教程。
- [x] 文档约定用户配置放在安装目录之外；完整升级保留流程仍待实测。
- [ ] 完成 CLI 来源／版本／能力绑定的可执行首配流程。
- [ ] 逐平台完成运行层适配并更新支持表。

## 验收

- [x] 桥接 84／84 与调度器 48／48 离线测试分别通过。
- [ ] 从全新 clone 只安装核心 Skill，资源全部到位。
- [ ] “怎么用”给出本地教程且未调用 Claude。
- [ ] “帮我设置／排错”先走对应模式，不误判为推理请求。
- [ ] 首次真实调用、持续追问、切回 Codex 均符合用户授权。
- [ ] 回执的模型／会话／状态与本轮官方结果一致，证据唯一对应。
- [ ] 失败、超时、费用未确认、权限拒绝、保存失败不伪报成功。
- [ ] 升级／回滚／卸载保留既有 CLI、账户历史和项目交接。
- [ ] 独立朋友按教程完成，不依赖作者电脑的设置。

## GitHub

公开预览仓库为 [ZHAOBIN-Lee/codex-claude-skills](https://github.com/ZHAOBIN-Lee/codex-claude-skills)。创建与公开已有维护者直接授权；邀请朋友、真实模型调用及稳定版发布不从本清单推导授权。

公开前复核全文件、Git 历史、Actions 日志与附件。CI 只运行离线测试，不放个人 Claude 账户或订阅凭据；第三方 Action 固定经过核对的提交，权限设为 `contents: read`，不自动做真实调用。

正式发布使用版本 tag／Release 和变更记录。首版核心是 claude-bridge；dev-orchestrator 可保持实验组件，等依赖安装和独立用户流程验证后再纳入稳定支持。

私有转公开会使代码、历史及 Actions 日志可见；公开后已有 fork／副本不能通过改回私有收回。[GitHub 官方说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
