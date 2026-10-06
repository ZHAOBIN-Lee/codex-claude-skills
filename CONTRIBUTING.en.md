# Contributing

[简体中文](CONTRIBUTING.md) · [English](CONTRIBUTING.en.md)

This is a public preview, and issues and patches are welcome. When you propose a change, say what you want to fix, how to trigger it, what you actually saw, and how you checked it.

If a change brings in new external source or documentation, include its author, original repository, version, and license, and keep the existing notices. If you change something users can see, update the Chinese and English docs together.

## Run the tests

From the repository root:

```text
python3 -m unittest discover -s skills/dev-orchestrator/tests -p 'test_*.py'
```

The dispatcher tests check task lifecycle, dispatch decisions and deterministic behavior. They call no real model and need no subscription. Real-model tests are up to the person running them on their own machine; keep personal subscription accounts and login credentials out of CI.

## Before you submit

Check that you haven't included:

- a runtime config or the author's installation manifest
- anything from a project's `.ai/` directory, or native session records
- business material, keys, or tokens

When you report results, name the platform and CLI version you actually ran on. A passing mock test shows the offline logic works. It doesn't tell you the real CLI or another platform works.
