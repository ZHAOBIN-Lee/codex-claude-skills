# Platform compatibility

[简体中文](../COMPATIBILITY.md) · [English](COMPATIBILITY.md)

`dev-orchestrator` has two layers. The Skill instructions and role definitions are plain text and work anywhere. `scripts/devflow.py` uses only the Python standard library with its own small YAML-subset parser, so it needs no PyYAML at runtime; the minimum is Python 3.9. All model calls go through Codex's native models and sub-agents, so whether it works mainly depends on whether [codex-claude-models-plugin](https://github.com/ZHAOBIN-Lee/codex-claude-models-plugin) runs on your system.

| | macOS | Linux / WSL | Native Windows |
| --- | --- | --- | --- |
| Skill instructions and roles | Works | Works | Works |
| `devflow.py` offline tests | Passed on the maintainer's machine | To verify | To verify |
| Native provider (Claude in the model picker) | Maintainer's daily use | Untested | Untested |
| Codex sub-agent dispatch | Tested by the maintainer | Depends on the provider | Depends on the provider |

This table is the current state, not a promise. Passing offline tests only shows the dispatch logic runs on that platform; real models and sub-agents need a separate check on a machine with the provider installed.

## How to verify

1. On the target platform, run `python3 -m unittest discover -s skills/dev-orchestrator/tests -p 'test_*.py'`.
2. Install the provider following its repository, and confirm GPT and Claude are both in the model picker.
3. In a practice project, run `/dev` once in each execution mode and record the actual models and results.
4. In a fresh chat, ask how the workflow is used and confirm it explains instead of starting work.
