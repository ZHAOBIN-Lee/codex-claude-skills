<!-- Snippet the ORCHESTRATOR appends to .ai/HANDOFF.md after each role finishes.
     claude-bridge appends its own run record; Claude never edits this file. -->
## Role handoff — <TASK-ID> — <YYYY-MM-DD HH:mm Australia/Melbourne>

- Role / tier / dispatch: <architect|executor|reviewer> / <strong|efficient> / <claude-bridge:mode | native>
- Requested effort (strong only): <medium|high> (source: auto|user)
- Result: <one or two sentences; what actually happened>
- Files changed (from git diff, not from the model): -
- Validation (commands the Orchestrator ran): <command: PASS|FAIL>
- Deviations: none | minor: <what> | major: see BLOCKERS.md
- Open questions: none
- Recommended next role: <architect|executor|reviewer|none>
- Recommended context: <TASK file, git diff, VALIDATION.md, ARCHITECTURE.md#section, DECISIONS.md#ADR-NNN>
