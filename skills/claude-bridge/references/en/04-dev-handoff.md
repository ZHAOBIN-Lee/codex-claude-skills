# File changes and development handoffs

[简体中文](../04-dev-handoff.md) · [English](04-dev-handoff.md)

The Bridge has two paths. For discussion only, use `consult`: for that call the Claude CLI's built-in tools and MCP tools are off, and Claude analyzes just the material you supply. To edit files, run tools, or validate code, use the default `--workflow standard`.

## Be specific about the goal

```text
In this project, ask Claude to plan the scope of the fix.
Have Codex implement it and run the relevant existing tests, then ask Claude to review it.
Keep my existing uncommitted work, and when you're done give me the diff, the test results, and a receipt for each Claude call.
```

You can also ask for review only: "Check this diff; don't modify anything yet." A review isn't permission to fix out-of-scope problems on the side. Steps you've already authorized don't need to be confirmed again. If the project, goal, or scope of changes is unclear, or your requests conflict, Codex should ask first.

If, partway through a discussion, you say "now write these changes into the files," the task moves into the standard workflow. Your chosen Claude model isn't dropped just because the task type changed, but the earlier "discussion only" doesn't count as permission to edit.

## A suggested order

1. Read the applicable `AGENTS.md`, `CLAUDE.md`, the necessary `.ai/` material, and the relevant code. Check the actual Git HEAD, status, and diff.
2. Claude plans the authorized task and states the boundaries and any conclusions that still need verifying.
3. GPT/Codex edits the real files. Only one agent edits a project at a time.
4. Run the deterministic checks related to the change, and look at the actual files and diff yourself.
5. Claude reviews the scope you named. GPT checks the review's findings and handles the necessary issues that are within what you authorized.

The optional `dev-orchestrator` strings these steps into a workflow. It doesn't replace Bridge setup, task authorization, or your own acceptance, and ordinary questions don't need it. A model saying "success" doesn't mean the requirement is met, and a "tests passed" in the text should match a record of an independent run.

## What the `.ai/` files are for

| File | Purpose |
| --- | --- |
| `PROJECT_CONTEXT.md` | Project goals, constraints, relevant structure, common commands |
| `DECISIONS.md` | Verified decisions, their basis, and open questions |
| `HANDOFF.md` | Current work and request/result handoffs; the Bridge backs it up and appends |
| `sessions.json` | The project's Claude session metadata |
| `consult.json` | The continued-consultation session and fingerprint baseline |
| `requests/` | Optional private UTF-8 task files |
| `logs/`, `backups/` | Local run records and pre-change backups |

Claude doesn't hand-rewrite the Bridge's own state and logs, and you shouldn't either. GPT adds human handoff notes after checking things independently, and separates what a model reported from what was verified. Unknown or to-be-filled fields in the templates stay unknown. Don't write them up as accepted.

A file being in `.gitignore` doesn't make its contents safe. Before you commit a project, check the summaries, decisions, and handoff files in `.ai/` that you plan to commit for personal data, full task text, business secrets, and credentials. Private state, task files, logs, and backups don't belong in a public repo.

## What a standard-path call looks like

Replace the placeholders with your real local paths. This isn't a command to paste and run as written:

```text
python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow standard --mode sonnet --task-file .ai/requests/current.txt --effort medium --effort-source user --effort-reason "User-selected development effort" --timeout 180
```

The task file must be a regular UTF-8 file inside the authorized project. Symlinks and paths outside the project are rejected. Use private permissions for the directory and file, and don't paste long text straight into a shell command. Use either `--task` or `--task-file`.

The standard workflow keeps normal permission checks. It doesn't use `--dangerously-skip-permissions`, and it doesn't widen authorization to global wildcards. If an exact operation is already authorized, it follows the existing rules. When you change authentication, permissions, or deployment configuration, verify it according to its real impact. Commits, pushes, releases, deployments, spending, and outgoing messages depend on authorization you've already given, and none of them happens by default.
