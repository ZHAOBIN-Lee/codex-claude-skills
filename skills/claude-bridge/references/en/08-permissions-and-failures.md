# Permissions for writing files, and what to do after a failure

[简体中文](../08-permissions-and-failures.md) · [English](08-permissions-and-failures.md)

This page covers permissions when Claude writes files on the standard path, the status fields you get back, and what to do when something goes wrong. A consult (discussion only, no file changes) doesn't need any of this.

## How to use it

To have Claude write `docs/plan.md`, the host does three things:

1. Declares the output file: `--output docs/plan.md`. Repeat it for each file, up to 20 per call.
2. Makes sure the project's local settings have the exact rule, for example in `.claude/settings.local.json`:

   ```json
   {"permissions": {"allow": ["Edit(/docs/plan.md)"]}}
   ```

3. Calls with `--stream-events`:

   ```text
   python3 <SKILL_DIR>/lib/bridge.py --runtime <RUNTIME_JSON> run --project <PROJECT_DIR> --workflow standard --stream-events --mode sonnet --task-file .ai/requests/current.txt --output docs/plan.md --effort medium --effort-source user --effort-reason "User-selected effort" --max-turns 5 --timeout 600
   ```

Replace the placeholders with your real local paths. `--max-turns` is 1 to 20 (default 3). `--timeout` is a finite number of seconds greater than 0 and at most 3600 (default 120). Values outside those ranges are rejected before the call. A read-only review can leave out `--output`.

## Output files and permission rules

- A path must be relative to the project. It can't contain `..` or a symlink, can't be under `.git` or `.claude`, and can't be a file the Bridge or host owns inside `.ai/` (HANDOFF, STATE, VALIDATION, PROGRESS, sessions.json, consult.json, logs, backups, locks).
- `Write(path)` doesn't count as a grant. Use an exact `Edit(path)`. A bare `Edit` is a broad grant: on its own it gives an `unknown` preflight verdict. An existing exact rule can still supply coverage. In project settings a path starting with `/` is measured from the session's working directory (the project or worktree). In user settings the same `/` is measured from `~/.claude`. `//path` is an absolute filesystem path, and `~/path` is under your home directory.
- The local settings of a Git worktree can live in the main checkout, and the Bridge looks there too. Allow rules in parent directories, or in your user `settings.local.json`, don't count.
- No widening into wildcard rules, no global rules, no deleting deny safeguards, no bypassing permissions. If existing authorization already covers this exact file, the host may merge just that one allow entry and leave every other setting as it was, without asking again. For a new scope, or when something is unclear, ask first.

Before inference, the Bridge does a static check of the local settings and gives each output file one verdict:

| Verdict | Meaning |
| --- | --- |
| `static_covered` | An exact Edit grant was found, and no conflicting deny or ask |
| `missing_rule` | No exact grant. The call is stopped before inference, with `inference` false |
| `deny_or_ask_may_apply` | A deny or ask rule (Read included) may apply. Also stopped |
| `unknown` | The rule is too complex, uses a wildcard, or is malformed, so it can't be decided. It's reported as is and not treated as a pass |

`static_covered` is only static metadata from local files. It doesn't mean the CLI will certainly allow the write, and it isn't a sandbox. Workspace trust, managed settings, and remote or session policy are still decided by Claude Code itself. For the declared outputs, the Bridge records existence, byte count, and a hash before and after. It stores no contents and doesn't prevent overwriting an existing file; an existing output file can be edited on purpose.

## One batch at a time

Hand over one deliverable you can check, or a small batch of clearly scoped tasks. A very long document can be split into parts, each written to its own file. There's no fixed number of batches. After each batch, the host looks at the real files, the diff, and the tests that matter before deciding on the next one.

Moving on to the next planned batch is not the same as repeating a failed call. The first is normal progress. The second needs a look at the actual state first, and the new call's scope should be stated. Continued batches in the same project don't use `--new-session`.

## The status you get back

| Field | What to look at |
| --- | --- |
| `status` | `complete`, `needs_permission`, `failed`, `timeout`, `blocked`, `state_update_failed`. `complete` only means the CLI finished. It isn't business acceptance |
| `permission_denials_status` | `listed`: some tools were denied. `none_reported`: the final result says there were none. `unavailable`: not obtained. `unavailable` (with `permission_denials` null) doesn't mean there were no denials |
| `session_id` | Comes only from the official final result, and is reported on failure too if the final result carried a valid one. Only `complete` saves it as the resume pointer; check `session_saved` |
| `actual_models` | Comes only from the final result's `modelUsage`. An early stop has no final result, so it's `unavailable`. A requested or resumed model doesn't stand in for it |
| `result_complete`, `truncated_result_fields` | Result strings are capped at 8000 characters and lists at 100 items. Anything longer is cut and `result_complete` is false. Put long documents in files, not in structured fields |
| `stream_events` | Counts per event type and whether a final result was seen. No event text |

With `--stream-events`, when Claude Code reports a runtime `permission_denied` event, the Bridge ends the batch right away with `needs_permission` and marks completion incomplete. An ordinary tool error (`is_error`) isn't a permission denial and doesn't abort. After a timeout, completion is still unknown. On a failure the saved session pointer doesn't change, but that doesn't guarantee Claude's native session record has no trace of the failed attempt.

## After a failure

After `blocked`, `needs_permission`, `failed`, `timeout`, or `state_update_failed`, nothing is silently retried. Look at the real files, `git status`, the diff, and the returned metadata to see how far it got, then decide. If existing authorization still covers it, state the scope and make a new call. Don't replay a batch that already completed, and don't overwrite an existing draft. If authorization falls short, the scope is unclear, or the problem is login, allowance, or a project lock, stop and ask the user.

## Limits

- Verified for real only on macOS, with the official CLI 2.1.285. Linux and Windows haven't been validated.
- A line in the stream that can't be parsed makes the batch count as failed, because that line might have been the denial event or the final result.
- Fixed read limits: 4 MiB per event and 64 MiB in total in stream mode, 10 MiB for ordinary JSON output. Going over terminates the call as failed. stderr is only counted by bytes, never stored.
- In one minimal test, a missing exact rule was stopped in about 0.2 seconds, and a runtime denial stopped after about 4.6 seconds (startup, generation, and cleanup included). That's an observation from a tiny test, not a promise for how long a long task takes.
