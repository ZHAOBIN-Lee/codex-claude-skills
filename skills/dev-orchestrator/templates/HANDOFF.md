<!-- Snippet the ORCHESTRATOR appends to .ai/HANDOFF.md after each role finishes.
     Sub-agents never edit this file. -->
## Role handoff — <TASK-ID> — <YYYY-MM-DD HH:mm Australia/Melbourne>

- Role / tier / dispatch: <architect|executor|reviewer> / <strong|efficient> / <current_chat | gpt_subagent | claude_subagent>
- Execution mode: <claude_dispatch_gpt | switch_to_gpt | claude_only>
- Actual model / sub-agent session: <from the sub-agent session or receipt; "not captured" if unavailable>
- Review independence (reviewer only): <independent_model | same_model_family_fresh_context>
- Result: <one or two sentences; what actually happened>
- Files changed (from git diff, not from the model): -
- Validation (commands the Orchestrator ran): <command: PASS|FAIL>
- Deviations: none | minor: <what> | major: see BLOCKERS.md
- Open questions: none
- Recommended next role: <architect|executor|reviewer|none>
- Recommended context: <TASK file, git diff, VALIDATION.md, ARCHITECTURE.md#section, DECISIONS.md#ADR-NNN>
