# 平台兼容

[简体中文](COMPATIBILITY.md) · [English](en/COMPATIBILITY.md)

`dev-orchestrator` 分两层：Skill 说明和角色规范是纯文字，各平台都能用；`scripts/devflow.py` 只用 Python 标准库，自带 YAML 子集解析，运行时不需要 PyYAML，最低 Python 3.9。模型调用全部交给 Codex 原生模型和子代理，所以能不能用，主要取决于 [codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin) 在你的系统上能不能跑。

| | macOS | Linux / WSL | Windows 原生 |
| --- | --- | --- | --- |
| Skill 说明和角色规范 | 可用 | 可用 | 可用 |
| `devflow.py` 离线测试 | 维护者实测通过 | 待验证 | 待验证 |
| 原生 Provider（Claude 进模型菜单） | 维护者日常使用 | 未测试 | 未测试 |
| Codex 子代理派发 | 维护者实测 | 取决于 Provider | 取决于 Provider |

这张表是现状，不是承诺。离线测试通过只说明调度逻辑在该平台上能跑；真实模型和子代理要在装好 Provider 的机器上另外验证。

## 验证步骤

1. 在目标平台运行 `python3 -m unittest discover -s skills/dev-orchestrator/tests -p 'test_*.py'`。
2. 按 Provider 仓库的说明安装，确认模型菜单里同时有 GPT 和 Claude。
3. 在一个练习项目里用三种执行模式各跑一次 `/dev`，记录实际模型和结果。
4. 在全新聊天里问“这个工作流怎么用”，确认能走到说明，不直接开始开发。
