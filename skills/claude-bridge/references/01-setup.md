# 首次安装与本机配置

[简体中文](01-setup.md) · [English](en/01-setup.md)

先问 Codex：

```text
$claude-bridge 教我首次配置。先确认我的系统、安装目录和测试项目；不要实际调用 Claude。
```

## 安装前需要什么

- 能加载 Skill 的 Codex 环境。
- 本机 Python ≥3.9 和附带 Bridge 程序需要的运行环境；当前代码使用 POSIX 能力，其他系统适配见 [限制说明](07-limits.md)。
- 本机官方 Claude Code CLI，使用你自己的 Claude.ai 订阅登录。
- 一个明确允许传给 Claude 的项目目录和任务；项目权限不由全局安装自动建立。

官方 Claude Code 的安装和登录方法以[官方安装说明](https://code.claude.com/docs/en/setup)与[官方认证说明](https://code.claude.com/docs/en/authentication)为准。用户自己完成网页登录，不向 Codex 提供密码、Cookie、Token 或验证码。官方 CLI 的系统支持范围，与这份 Bridge 的实际支持范围应分开判断。

当前 Bridge 的订阅认证判断只接受 `authMethod: claude.ai` 且 `subscriptionType: pro|max`。官方产品还有其他账户路线，但这份草稿尚未适配所有路线；Team、Enterprise、Console 和第三方 Provider 不应被宣传为已支持。不要为通过检查而伪造认证结果。

## 把 Skill 安装到哪里

安装单元应是完整的 `skills/claude-bridge/` 目录，包含 `SKILL.md`、`lib/bridge.py`、配置模板和 `references/` 教程。只复制 `SKILL.md` 会缺少程序和帮助文件。

安装目标以当前 Codex 实际使用的 Skill 目录为准；不要覆盖同名已修改版本。先备份、比较差异，再决定替换还是保留。可让 Codex 的宿主安装器安装整个目录：

```text
$skill-installer 从 https://github.com/ZHAOBIN-Lee/codex-claude-skills 安装 skills/claude-bridge，使用 main 分支的预览草稿。若已安装同名 Skill，先比较并备份。
```

这是宿主 Skill 安装器的用法；本仓库没有另附自动首配工具，尚无稳定版 tag。未实现的自定义安装命令不能当作可运行命令推荐。

在 Codex 中明确调用 `$claude-bridge`，让它确认能找到这份 Skill 和教程。若未发现，先检查目录和 Skill 校验结果，再按当前 Codex 的发现机制处理；不要默认每台机器都必须重启，也不要声称新安装一定即时生效。

## 为自己的机器建立 runtime

`runtime.json` 是本机配置，不能复制作者账号的运行配置。按安装后的配置模板填写自己的官方 CLI 绝对路径、已核实的版本和 SHA-256 哈希，并保留官方来源证据。给任意 PATH 程序算哈希不能证明它来自官方；不能留空版本或哈希来绕过原有检查。

费用确认必须来自这台机器的使用者：用户检查自己的账号费用设置，确认额外 usage credits 已关闭后，才能据此记录 `subscription_usage_credits_disabled: true` 和 `usage_credits_confirmation` 的用户来源、确认日期。该记录不是脚本直接读取 Billing 的证据；不能从示例、作者确认或另一个账号继承。

字段未确认时保持未确认状态，让真实调用被阻止。更换账号或改变费用设置时更新确认；同一事实已确认且仍适用时无需反复询问。不要把凭据或认证文件放入仓库或 runtime。

## 第一次项目检查

下面只展示已有 Bridge 参数结构。`<SKILL_DIR>`、`<RUNTIME_JSON>`、`<PROJECT_DIR>` 都是占位符，必须换成本机实际绝对路径；这些示例不是自动安装器。

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> doctor --project <PROJECT_DIR>
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> init --project <PROJECT_DIR>
```

`doctor` 只检查，不调用模型。`init` 仅在用户已授权的项目内增量建立 `.ai/`，保留已有交接内容，不创建或改写根目录 `AGENTS.md`、`CLAUDE.md`。已有 `.ai/` 项目也应先读取现状。

下面是可选的真实验证步骤，普通“教我怎么用”请求不会执行它。使用者已明确要求真实验证且准备完成后，可做一次短咨询。它会使用你的 Claude 订阅额度；`--dry-run` 只能验证准备行为，不能证明 Claude 被实际调用。

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow consult --mode sonnet --task "给出这个测试任务的一句话建议" --effort medium --effort-source user --effort-reason "用户指定首次验证强度" --timeout 180
```

Codex 应使用独立参数或正确的 shell 引号传入本机路径和用户文本。成功后核对本轮实际模型、会话 ID、状态和唯一对应凭证，再用 [连续对话教程](02-conversation.md) 验证接续。不要把模板创建、登录成功或 `doctor` 通过当作端到端安装验收。
