# 写文件的权限与失败后怎么办

[简体中文](08-permissions-and-failures.md) · [English](en/08-permissions-and-failures.md)

这一页讲标准路径下让 Claude 写文件时的权限、返回的状态字段，以及出问题后的处理。只讨论、不改文件的咨询（`consult`）不用看这里。

## 怎么用

让 Claude 写 `docs/plan.md`，宿主要做三件事：

1. 声明这个输出文件：`--output docs/plan.md`。要写几个文件就重复几次，一次最多 20 个。
2. 确认项目本地设置里有对应的精确规则，例如 `.claude/settings.local.json` 里：

   ```json
   {"permissions": {"allow": ["Edit(/docs/plan.md)"]}}
   ```

3. 调用时带上 `--stream-events`：

   ```text
   python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow standard --stream-events --mode sonnet --task-file .ai/requests/current.txt --output docs/plan.md --effort medium --effort-source user --effort-reason "用户指定强度" --max-turns 5 --timeout 600
   ```

占位符换成你本机的实际路径。`--max-turns` 取 1 到 20（默认 3），`--timeout` 是大于 0、不超过 3600 的有限秒数（默认 120）。超出范围会在调用前被拒绝。只读审查可以不写 `--output`。

## 输出文件和权限规则

- 路径必须是项目内的相对路径，不能含 `..`、符号链接，不能在 `.git`、`.claude` 下，也不能是 `.ai/` 里 Bridge 或宿主自己管的文件（HANDOFF、STATE、VALIDATION、PROGRESS、sessions.json、consult.json、日志、备份、锁）。
- `Write(路径)` 不算授权，要用精确的 `Edit(路径)`。不带路径的 `Edit` 是宽泛授权，单独存在时预检会报 `unknown`；已有精确规则仍可提供覆盖。项目设置里以 `/` 开头的路径，从这次会话的工作目录（项目或 worktree）算起；用户设置里的 `/` 则是从 `~/.claude` 算起。`//路径` 是文件系统绝对路径，`~/路径` 是用户目录。
- Git worktree 的本地设置可能在主检出里，Bridge 也会去看。上级目录里的 allow 规则、用户的 `settings.local.json` 不算数。
- 不放宽成通配规则，不写全局规则，不删 deny 保护，不绕过权限。已有授权覆盖这个精确文件时，宿主可以只合并这一条 allow，其他设置原样保留，不用再问一遍；新的范围或说不清的地方，先问。

Bridge 在推理前读本地设置做一次静态预检，每个输出文件给出一个结论：

| 结论 | 意思 |
| --- | --- |
| `static_covered` | 找到精确的 Edit 授权，没发现冲突的 deny 或 ask |
| `missing_rule` | 没有精确授权。调用会在推理前被拦下，`inference` 为 false |
| `deny_or_ask_may_apply` | 有 deny 或 ask（含 Read）可能适用，同样被拦下 |
| `unknown` | 规则太复杂、含通配或格式不对，无法确定，如实报告，不当作通过 |

`static_covered` 只是本地文件的静态元数据，不等于 CLI 一定放行，也不是沙箱。工作区信任、托管设置、远程和会话策略仍由 Claude Code 自己判断。Bridge 对声明的输出文件只在前后各记一次存在、字节数和哈希，不存正文，也不阻止覆盖已有文件；已有的输出文件可以被有意修改。

## 一次一批

一次只交一个可以检查的成果，或一小批范围明确的任务。内容很长的文档拆成几部分，各写各的文件。没有固定的批数。每批返回后，宿主先看真实的文件、diff 和需要的测试，再决定下一批。

按计划进入下一批，和重复一次失败的调用不是一回事：前者是正常推进，后者要先查清实际状态，并把新调用的范围说出来。同一个项目的连续批次不加 `--new-session`。

## 返回的状态

| 字段 | 看什么 |
| --- | --- |
| `status` | `complete`、`needs_permission`、`failed`、`timeout`、`blocked`、`state_update_failed`。`complete` 只表示 CLI 跑完了，不是业务验收 |
| `permission_denials_status` | `listed`：有被拒的工具；`none_reported`：最终结果明确没有；`unavailable`：没有取到。`unavailable`（`permission_denials` 为 null）不等于没有拒绝 |
| `session_id` | 只来自官方最终结果，失败时只要最终结果带了有效 ID 也会报告。保存为续接指针的只有 `complete`，看 `session_saved` |
| `actual_models` | 只来自最终结果的 `modelUsage`。早停没有最终结果，就是 `unavailable`，不能用请求或恢复的模型代替 |
| `result_complete`、`truncated_result_fields` | 结果字符串最多 8000 字符，列表最多 100 项，超出会截断并标 `result_complete` 为 false。长文档要写成文件，别塞进结构化字段 |
| `stream_events` | 各类事件的数量和是否见到最终结果，不含事件文本 |

`--stream-events` 下，Claude Code 报出运行时的 `permission_denied` 事件，Bridge 立即结束这一批，状态是 `needs_permission`，完成情况标为 incomplete。普通工具报错（`is_error`）不算权限拒绝，不会中止。超时后完成情况仍是未知。失败时保存的会话指针不变，但这不保证 Claude 原生会话记录里没有这次失败的尝试。

## 失败后怎么办

`blocked`、`needs_permission`、`failed`、`timeout`、`state_update_failed` 之后都不静默重试。先看真实的文件、`git status`、diff 和返回的元数据，弄清做到了哪一步，再决定。已有授权仍然覆盖的话，把范围说清楚，另行发起新的调用；不要把已经完成的批次原样重放，也不要覆盖已有的草稿。授权不够、范围不清楚，或者登录、额度、项目锁这类问题，停下来问用户。

## 限制

- 只在 macOS 上、用官方 CLI 2.1.285 做过真实验证。Linux 和 Windows 没验证过。
- 流里出现无法解析的行，这一批会按失败处理，因为那一行可能就是拒绝事件或最终结果。
- 固定的读取上限：流模式单个事件 4 MiB、总量 64 MiB，普通 JSON 输出 10 MiB，超过就终止并报失败。stderr 只数字节，不保存内容。
- 一次最小测试里，缺精确规则在约 0.2 秒内被拦下，运行时拒绝约 4.6 秒后停止（含启动、生成和清理）。这只是小测试的观察，不是长任务的耗时承诺。
