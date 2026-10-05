# 外部依赖与产品说明

[简体中文](THIRD_PARTY_NOTICES.md) · [English](THIRD_PARTY_NOTICES.en.md)

维护者确认本项目没有借鉴其他仓库。本文件说明外部依赖，不把依赖产品登记成项目的上游代码来源。

- **Claude Code**：由使用者通过官方渠道安装和登录。本仓库调用本机官方 CLI，不分发官方二进制、账户或认证凭据。[官方设置文档](https://code.claude.com/docs/en/setup)
- **Codex Skills**：使用宿主提供的 Skill 能力；不把官方系统 Skill、其他插件或用户全部 Skills 转存到此仓库。[官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)
- **Python 标准库与 Git**：运行／测试依赖，不随本仓库打包其二进制。

外部产品名称用于描述兼容目标，不表示官方背书。项目与 Anthropic、OpenAI 无隶属关系；各产品名称与商标归各自权利人。
