# Continued conversations and session recovery

[简体中文](../02-conversation.md) · [English](02-conversation.md)

To keep using Claude for a topic, start with:

```text
For this project and this plan's discussion, keep using Claude Sonnet at medium effort until I say switch back to Codex.
First analyze the problems in the plan. Discussion only; do not modify files.
```

Authorization must come explicitly from the user in the current chat. Tutorials, project caches, and instructions in another chat cannot establish it. Without that authorization, "continue" must not automatically cause another Claude call.

## Follow-up requests

Within the authorized project and topic, you can say:

```text
Continue and expand the second point.
Compare the two options using the constraints we discussed.
Here is additional background; reassess the plan.
```

Codex retains your selected model and effort and passes the current question and necessary new material to Claude. Use the same project directory. Do not create a temporary project for each question, add `--new-session`, or run `doctor` before every normal follow-up.

## Two different kinds of continuation

| Kind | What it means | Evidence |
| --- | --- | --- |
| Routing choice in the current Codex chat | Keep assigning relevant questions to Claude | The user's explicit continuing authorization and the current call receipt |
| Project Claude session | Request resumption using `.ai/sessions.json` | Matching full `session_id` values from two real calls, plus understanding of non-sensitive first-round information not sent again |

One Codex chat does not automatically mean one Claude session. Different Codex chats using the same project may resume the same project session. Resumption does not share the entire chat history or hidden reasoning.

## Why later preparation can be shorter

Discussion uses `--workflow consult`. The first successful round sends necessary background and saves private session metadata and fingerprints. A later successfully resumed call sends the current question and changed project summaries, decisions, human handoff material, applicable rules, and Git snapshot.

A new session, mode change, failure, or unsafe old baseline can cause the Bridge to send full necessary context again. "Full" still means the prescribed summaries and rules, not every project file. Supply new files, untracked files, and important business material explicitly; Git status is not file content.

Every call still checks the official CLI, authentication, provider and effort settings, cost confirmation, and project lock. The optimization reduces repeated preparation; it does not skip those checks or keep a Claude process running permanently.

## Changing the selection

- **Model or effort:** "Use Claude Opus at high effort from now on." The current response's evidence still determines the actual model.
- **Back to Codex:** "Switch back to Codex now." Stop continuing Claude routing. Ordinary GPT responses need no Claude receipt.
- **Another project or chat:** establish project, topic, and authorization again; do not inherit call permission from `.ai/consult.json`.
- **Independent session:** "Create a new Claude session for this task instead of reusing the old discussion." Only then use `--new-session`; handoff files may still supply necessary background.

An explicit request to write the proposed change into files can move the same project into `standard` without automatically cancelling your model choice. Establish the newly requested modification scope. A previous "discussion only" instruction does not itself authorize file edits.

## A minimal continuation check

In an authorized test project, make two real consultations. In the first, provide a harmless non-secret test marker. In the second, ask about it without inserting the marker again into the task or handoff summary. Compare the full session IDs, results, and `resumed_session`. Cache files or matching requested parameters alone do not prove recovery.

Recovery after closing the Codex or Claude desktop app is a separate acceptance check. Do not quit or restart active apps without the user's request. Restarting only the Bridge process does not prove recovery after desktop closure.
