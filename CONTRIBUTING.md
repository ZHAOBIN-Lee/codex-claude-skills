# 贡献说明

[简体中文](CONTRIBUTING.md) · [English](CONTRIBUTING.en.md)

目前是公开预览草稿。提交修改前说明目标、触发方式、实际结果和验证证据。新来源代码／文档必须附作者、原仓库、版本及适用许可，保留既有声明。修改用户可见行为时同步维护中文和英文说明。

运行测试：

```text
python3 -m unittest discover -s skills/claude-bridge/tests -p 'test_*.py'
python3 -m unittest discover -s skills/dev-orchestrator/tests -p 'test_*.py'
```

这些离线测试使用 fake CLI，不需要真实订阅。真实模型测试需本机用户明确授权，不能把个人订阅账户或登录凭据放到 CI。

提交前确认没有 runtime、作者安装清单、项目 .ai、原生会话、业务材料或秘密。报告实际验证的平台和 CLI 版本；Mock 通过不能替代真实兼容结论。
