# Continued conversations and session recovery

[简体中文](../02-conversation.md) · [English](02-conversation.md)

To keep using Claude on one topic, start with something like:

```text
For this project and this plan's discussion, keep using Claude Sonnet at medium effort until I say switch back to Codex.
First analyze the problems in the plan. Discussion only; do not modify files.
```

You have to say this yourself, in the current chat. Examples in a tutorial, a project cache, or something you said in another chat don't count. Until you've said it, a bare "continue" won't make Codex call Claude.

## Follow-ups

Once you've said it, inside the same project and topic you can just write:

```text
Continue and expand the second point.
Compare the two options using the constraints we discussed.
Here is additional background; reassess the plan.
```

Codex keeps your model and effort and sends Claude the current question plus any new material. Use the same project directory for follow-ups. There's no need for a temporary project per question, no `--new-session`, and no `doctor` before each one.

## Two kinds of continuation

| What continues | What it does | How to check |
| --- | --- | --- |
| The choice in this Codex chat | Keeps routing questions to Claude within what you authorized | Your standing authorization, plus the receipt for that call |
| The project's Claude session | Asks to resume the session recorded in `.ai/sessions.json` | Two real calls return the same `session_id`, and the second understands non-sensitive details from the first that weren't sent again |

One Codex chat doesn't necessarily map to one Claude session. Different Codex chats in the same project may resume the same project session. Resuming a session doesn't mean either side shares the full chat history or hidden reasoning.

## Why later rounds need less preparation

Discussion uses `--workflow consult`. The first successful round sends the necessary background and saves a private session record and fingerprint baseline. After that, when the same session resumes successfully, the Bridge sends only the current question plus whatever changed in the project summaries, decisions, human handoff notes, applicable rules, and Git snapshot.

With a new session, a different model mode, a failed previous round, or an old baseline it can't confirm is safe, the Bridge falls back to sending the full set of necessary context. "Full" here means the defined summaries and rules, not a read of the whole project. Give Claude new files, untracked files, and important business material explicitly. Git status tells Claude which files changed, but not what's in them.

Every call still checks the official CLI, authentication, provider, effort settings, cost confirmation, and project lock. What you save is repeated preparation. None of those checks is skipped, and no Claude process stays running in the background.

## Changing the setup

- **Model or effort:** say "use Claude Opus at high effort from now on." The receipt for each call still tells you which model actually answered.
- **Back to Codex:** say "switch back to Codex now." Codex stops carrying the Claude choice forward, and ordinary GPT answers need no Claude receipt.
- **Another project or a new chat:** state the project, topic, and authorization again. A `.ai/consult.json` file doesn't mean you agreed to a call.
- **A separate Claude session:** say "start a new Claude session for this task instead of reusing the old discussion." Only then does `--new-session` come into play, and the handoff files may still supply necessary background.

If you move the same project from discussion to "write this plan into these files," your Claude model choice stays. Codex confirms which files you actually want changed from your new request and switches to the standard workflow. An earlier "discussion only" isn't permission to edit.

## A quick check that resuming works

In an authorized test project, make two real consultations. In the first, give a harmless, non-secret test marker. In the second, ask what the marker was, without putting it into the task or handoff summary again. Compare the full session IDs and answers across the two receipts, then confirm `resumed_session`. A cache file or identical request parameters don't prove the session was resumed.

Recovery after closing the Codex or Claude desktop app is a separate check. Don't quit or restart an app you're using unless you asked for that. Restarting only the Bridge process doesn't show that recovery after closing the desktop app works.
