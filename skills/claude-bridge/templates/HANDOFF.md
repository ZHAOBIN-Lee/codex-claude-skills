# AI Handoff

状态：待填写。此模板不是已完成交接，也不表示任何测试已通过。调用前由 GPT 整理当前状态；Claude 返回结构化结果，由 Bridge 备份后追加记录。Claude 不自行编辑本文件。GPT 独立核验后补充结论，不把模型报告当成已验证事实。

## Current Goal

- 用户当前请求：待填写。
- 本轮允许执行的工作与验收标准：待填写。

## Current Status

- 状态：待执行 / 进行中 / 完成且已验证 / 受阻 / 待用户输入。
- 更新时间：YYYY-MM-DD HH:mm:ss Australia/Melbourne。
- 项目绝对路径：待填写。
- Git HEAD：待填写实际值；非 Git 项目明确写“非 Git”。
- 调用前未提交变更：待填写实际 `git status`，并区分原有工作和本轮变更。
- 当前未提交变更：待填写实际 `git status`。

## Last Agent

GPT / Claude；实际模型与 Session 证据如可安全取得再记录。不要把请求模型名当作实际执行模型。

## Work Completed

待填写实际完成的动作及可核对证据；未执行内容不写完成。

## Files Changed

待填写实际文件及修改目的，标注原有变更；由接手 Agent 核对 Git diff。

## Tests and Evidence

| 命令/操作 | 实际结果 | 证据位置 | 未验证内容 |
| --- | --- | --- | --- |
| 待填写 | NOT_TESTED | 无 | 待填写 |

不把模板、Mock、CLI 成功退出或模型完成声明当作真实业务验收。

## Decisions Made

待填写本轮决策，并引用 `.ai/DECISIONS.md`；无新决策写“无”。

## Known Issues and Unknowns

- 已知问题：待填写；无则明确写“无”。
- 尚未取得的证据：待填写，标注“未取到”。
- 需要反问用户的问题：待填写。
- 权限拒绝或失败的实际操作：待填写。

## Forbidden / Approval Boundaries

- 不读取/保存秘密、隐藏推理或无关私人数据。
- 不自动创建 API Key、开启 API Billing、购买额外 usage 或切换 API Provider。
- 不跳过官方 Claude 权限，不自动批准被拒绝操作。
- 不丢弃用户现有 Git 工作，不自动 commit/push/部署。
- 不升级软件、修改系统或重启正在工作的桌面应用，除非用户明确同意。
- 本项目额外限制：待填写。

## Next Recommended Action

待填写具体、可执行且在授权范围内的下一步；先处理需要用户输入或权限批准的阻塞。

## First Read Files

1. 当前项目的 `AGENTS.md`、`CLAUDE.md`（如存在）。
2. `.ai/PROJECT_CONTEXT.md`、`.ai/DECISIONS.md`、本文件。
3. 当前任务相关文件：待填写。

## Receiving Agent Verification

- 读取上述交接与任务文件：NOT_TESTED。
- 核对当前 HEAD、Git status 和 diff：NOT_TESTED。
- 根据交接继续任务并验证结果：NOT_TESTED。

这些状态仅由接手 Agent 的实际操作证据更新。
