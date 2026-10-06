# Privacy and issue reporting

[简体中文](SECURITY.md) · [English](SECURITY.en.md)

## What not to post

The repository doesn't collect OAuth tokens, cookies, API keys, passwords, or official-account authentication files. Please keep them out of issues, screenshots, public logs, and test output.

## Reporting an install or runtime problem

Include:

- the Skill version and your OS
- the Python, Codex, and codex-claude-models-plugin versions
- what kind of operation you were doing
- the error code, plus the minimum redacted detail needed to reproduce it

Leave out complete tasks, model responses, business source code, and official Claude session records.

## If the report involves sensitive content

The repository is public and there's no dedicated private-reporting channel yet. If a problem involves secrets or sensitive project content, contact the maintainer first and agree on a private way to share it. Don't post it in a public issue.

## A rule for porting

Normal permissions, explicit project scope, model routing, and sub-agent permissions are part of how the workflow works today. When you port or adapt it, don't skip them to get something running, and don't quietly swap models.
