# Contributing

[简体中文](CONTRIBUTING.md) · [English](CONTRIBUTING.en.md)

This is a public preview. Describe the goal, trigger, actual behavior, and validation evidence when proposing a change. For newly imported source or documentation, include its author, original repository, version, and applicable license, and retain existing notices.

Run the offline tests:

```text
python3 -m unittest discover -s skills/claude-bridge/tests -p 'test_*.py'
python3 -m unittest discover -s skills/dev-orchestrator/tests -p 'test_*.py'
```

The tests use a fake CLI and need no real subscription. Real-model tests require the local user's explicit authorization. Do not put personal subscription accounts or credentials in CI.

Do not submit personal runtime files, author-specific installation manifests, project `.ai/` state, native sessions, business material, or secrets. Report the actual tested platform and CLI version; mock success is not proof of real compatibility. Keep Chinese and English explanations aligned when changing user-visible behavior.
