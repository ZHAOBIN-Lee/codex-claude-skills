# 外部依赖与产品说明

[简体中文](THIRD_PARTY_NOTICES.md) · [English](THIRD_PARTY_NOTICES.en.md)

这里列的是本项目会用到的外部产品和工具。它们是运行依赖，不是项目的代码来源。

- **codex-claude-models-plugin**：让 Claude 出现在 Codex 模型菜单里的 Provider，需另行安装，见[仓库](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin)。它基于 Reidond/codex-claude-models-plugin 修改，许可和署名在该仓库。它通过你本机的官方 Claude Code 和你自己的订阅登录调用 Claude，本仓库不分发官方二进制、账户或凭据。
- **Codex Skills**：使用 Codex 提供的 Skill 能力。仓库里没有转存官方系统 Skill、其他插件，或你装的其他 Skills。见[官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)。
- **Python 标准库与 Git**：运行和测试要用到，二进制不随仓库打包。

文档里提到这些产品，是为了说明兼容对象，不代表它们的官方认可。本项目与 Anthropic、OpenAI 没有隶属关系，各产品名称和商标归各自权利人。
