# 变更记录

[简体中文](CHANGELOG.md) · [English](CHANGELOG.en.md)

## 未发布 — 本地权限与超时修复

这是对公开提交 567dd9d 的本地修复，不是新的 GitHub 发布，也没有新版本号。

- 新增 `--output PATH`：宿主逐个声明输出文件，Bridge 在推理前做静态的精确 Edit 规则预检，缺少授权时直接拦下；输出文件前后各记一次存在、字节数和哈希。
- 新增 `--stream-events`：标准流程可选，遇到官方 `permission_denied` 事件立即结束这一批，只保存事件计数，不保存事件文本。
- 有界读取 stdout/stderr，超时时终止整个进程组，不再因后代进程持有管道而挂住。
- 新增 `permission_denials_status`（listed/none_reported/unavailable）；没有取到的证据不再当作“没有拒绝”。最终结果带有效会话 ID 时，失败也如实报告，但只有 complete 才保存。
- 结构化结果被截断时标 `result_complete` 为 false；`--max-turns` 限 1..20，`--timeout` 必须是有限秒数，0<seconds<=3600（0 无效）。
- 新增[权限与失败处理](skills/claude-bridge/references/08-permissions-and-failures.md)教程，并修正 `dev-orchestrator` 里“失败一律询问用户”的冲突。
- 验证范围：离线测试，以及在 macOS 上用官方 CLI 2.1.285 的真实订阅小测试。Linux 和 Windows 没有验证。

## 0.1.0-draft — 2026-10-05

- 将 Claude 调用相关资源整理为自包含 Skill 的公开预览草稿。
- 增加安装后可询问的本地教程入口、连续对话约定、偏好示例和实际模型回执说明。
- 排除作者本机运行配置、安装清单、官方 CLI、会话、日志和备份。
- 将 dev-orchestrator 保留为可选实验组件。
- 记录维护者对项目来源的确认，增加许可选择与跨平台适配清单。
- 增加中英文 README、使用教程与维护说明。
- 按维护者选择采用 MIT，署名 ZHAOBIN-Lee；许可副本随各 Skill 安装目录保留。
- 改写中英文 README、教程和维护文档，首页先讲用途、安装和第一个请求，细节移到对应教程。

公开仓库为 ZHAOBIN-Lee/codex-claude-skills，尚未发布稳定版或版本 tag。许可状态见 LICENSING.md；干净环境安装与各平台真实验证仍需完成。
