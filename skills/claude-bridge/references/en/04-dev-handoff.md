# File changes and development handoffs

[简体中文](../04-dev-handoff.md) · [English](04-dev-handoff.md)

Use the default `--workflow standard` for file modifications, tool execution, or code validation. Discussion uses `consult`, which disables the Claude CLI's built-in and MCP tools for that call and analyzes supplied material only.

## State a concrete goal

```text
In this project, ask Claude to plan the scope of the fix.
Have Codex implement it and run the relevant existing tests, then ask Claude to review it.
Preserve existing uncommitted work and return the diff, test results, and a receipt for each Claude call.
```

You may request only a review: "Check this diff; do not modify it yet." Review does not independently authorize out-of-scope fixes. Already authorized steps need no repeated permission request. Ask first when the project, goal, change scope, or conflict is unclear.

An explicit request to write changes during an ongoing discussion moves the task into the standard workflow. Task type alone does not cancel the selected model, but "discussion only" is not authorization to edit files.

## Suggested sequence

1. Read applicable `AGENTS.md`, `CLAUDE.md`, necessary `.ai/` material, and relevant code; check actual Git HEAD, status, and diff.
2. Claude plans the authorized task and states implementation boundaries and conclusions needing verification.
3. GPT/Codex edits actual files. Only one agent modifies the same project at a time.
4. Run relevant deterministic checks and independently inspect the files and diff.
5. Claude reviews the specified scope. GPT verifies the review findings and addresses necessary, authorized issues.

The optional `dev-orchestrator` organizes these stages. It does not replace Bridge setup, authorization, or acceptance and is unnecessary for ordinary questions. A successful model response or a written "tests passed" claim must not substitute for independent execution evidence.

## Project `.ai/` files

| File | Purpose |
| --- | --- |
| `PROJECT_CONTEXT.md` | Goals, constraints, relevant structure, common commands |
| `DECISIONS.md` | Verified decisions, evidence, and unresolved questions |
| `HANDOFF.md` | Current work and request/result handoffs; the Bridge backs up and appends |
| `sessions.json` | Project Claude session metadata |
| `consult.json` | Continued-consultation session and fingerprint baseline |
| `requests/` | Optional private UTF-8 task files |
| `logs/`, `backups/` | Local runtime evidence and pre-change backups |

Claude does not rewrite Bridge-owned state or logs manually. GPT adds human handoff notes after verification and distinguishes model reports from verified facts. Unknown template fields remain unknown until acceptance.

Git ignore rules do not make content safe. Before committing project summaries, decisions, or handoffs, check for personal data, complete tasks, business secrets, and credentials. Private state, task files, logs, and backups do not belong in the public package.

## Standard-workflow example

Replace placeholders with actual local paths; this is not an executable installation command:

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow standard --mode sonnet --task-file .ai/requests/current.txt --effort medium --effort-source user --effort-reason "User-selected development effort" --timeout 180
```

The task file must be a regular UTF-8 file inside the authorized project, not a symlink or an outside path. Use private directory/file permissions and correct argument handling rather than inserting long user text into shell code. Choose either `--task` or `--task-file`.

Keep normal permission checks. Do not use `--dangerously-skip-permissions` or broad global allow rules. Handle already authorized exact operations under the normal rules. Verify authentication, permission, and deployment configuration changes according to their actual impact. Commit, push, publication, deployment, cost changes, and external messages depend on existing user authorization and are not automatic defaults.
