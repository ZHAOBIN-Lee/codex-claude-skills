# 首次安装与本机配置

[简体中文](01-setup.md) · [English](en/01-setup.md)

不确定从哪开始，就问 Codex：

```text
$claude-bridge 教我首次配置。先确认我的系统、安装目录和测试项目；不要实际调用 Claude。
```

## 先准备好这些

- 能加载 Skill 的 Codex。
- Python 3.9 或更新版本。附带的 Bridge 目前用到 POSIX 能力（`fcntl` 文件锁、进程组、私有文件权限），其他系统见[限制说明](07-limits.md)。
- 本机的官方 Claude Code CLI，用你自己的 claude.ai 订阅登录。
- 一个你愿意发给 Claude 的项目目录和任务。装 Skill 不会自动授权任何项目。

Claude Code 的安装和登录照[官方安装说明](https://code.claude.com/docs/en/setup)和[官方认证说明](https://code.claude.com/docs/en/authentication)做，网页登录自己完成，不要把密码、Cookie、Token 或验证码发给 Codex。官方 CLI 支持哪些系统，和这个 Bridge 在哪些系统上验证过，是两回事。

Bridge 目前只认 `authMethod: claude.ai` 且 `subscriptionType: pro|max` 的登录。Team、Enterprise、Console API 和第三方 Provider 还没有适配。也别为了过检查去改认证结果。

## 把 Skill 装好

要装的是整个 `skills/claude-bridge/` 目录：`SKILL.md`、`lib/bridge.py`、配置模板和 `references/` 教程都在里面。只拿 `SKILL.md` 会缺程序和帮助文件。

装到当前 Codex 实际读取的 Skill 目录。如果已经有同名 Skill，先备份、比较差异，再决定替换还是保留。可以让 Codex 的 Skill 安装器来装：

```text
$skill-installer 从 https://github.com/ZHAOBIN-Lee/codex-claude-skills 安装 skills/claude-bridge，使用 main 分支的预览草稿。若已安装同名 Skill，先比较并备份。
```

这是 Codex 自带安装器的用法，本仓库没有另外提供一键首配工具，也还没有稳定版 tag。

装完后，在 Codex 里调用一次 `$claude-bridge`，看它能不能找到 Skill 和教程。没找到，先检查目录是否完整、Skill 格式是否通过校验，再按你的 Codex 版本的发现方式处理。不一定要重启，但也别假定装完立刻生效。

## 建自己的 runtime 配置

`runtime.json` 是你这台机器的本机配置，放在 Skill 目录之外。格式参考 [runtime.example.json](../templates/runtime.example.json)，填这几项：

- 官方 CLI 的绝对路径。
- 你核实过的版本。作者现在用的是 2.1.285。
- 这个文件的 SHA-256。这个哈希要在你的机器上自己算，作者机器上的不能抄。
- 官方来源的证据。给 PATH 里随便一个文件算出哈希，只能说明它是那个文件，证明不了它来自官方。

版本和哈希不能留空，也不能靠留空绕过检查。

费用状态也要你自己确认。去检查你账号的费用设置，确认额外 usage credits 已关闭，然后记下 `subscription_usage_credits_disabled: true`，以及 `usage_credits_confirmation` 里你的确认来源和日期。这是你本人的确认，脚本不会去读 Billing。不能沿用示例里的值、作者的确认，或者别的账号的确认。

没确认就保持“未确认”，真实调用会被拦下。换了账号或改了费用设置，再确认一次；同一件事已经确认过、仍然适用，就不用反复问。凭据和认证文件不要放进仓库，也不要放进 runtime。

## 第一次检查项目

下面几条展示 Bridge 已有的参数写法。`<SKILL_DIR>`、`<RUNTIME_JSON>`、`<PROJECT_DIR>` 是占位符，要换成你本机的实际绝对路径。

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> doctor --project <PROJECT_DIR>
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> init --project <PROJECT_DIR>
```

`doctor` 只检查环境，不调用模型。`init` 只在你已授权的项目里补建缺少的 `.ai/` 文件，已有的交接内容保留，也不会创建或改写项目根目录的 `AGENTS.md`、`CLAUDE.md`。项目里已经有 `.ai/` 的话，先读一下现状。

想真实验证一次，可以做一个短咨询。普通的“教我怎么用”不会执行它，它会用掉你的 Claude 订阅额度。`--dry-run` 只检查准备流程，证明不了 Claude 真的被调用过。

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow consult --mode sonnet --task "给出这个测试任务的一句话建议" --effort medium --effort-source user --effort-reason "用户指定首次验证强度" --timeout 180
```

让 Codex 执行时，路径和你的文字要作为独立参数传，或者用正确的 shell 引号。成功后看这几项：这次的实际模型、完整会话 ID、状态，以及唯一对应的凭证。再按[连续对话教程](02-conversation.md)试一次接续。模板建好了、登录成功了、`doctor` 通过了，都还不算装完，真正调用成功才算。
