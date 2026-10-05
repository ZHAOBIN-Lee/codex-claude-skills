#!/usr/bin/env python3
"""Offline subprocess fixture; never contacts a model service."""
import json
import os
import pathlib
import sys
import time

args = sys.argv[1:]
if args == ["--version"]:
    print("2.1.0 (Claude Code)")
elif args == ["--help"]:
    text = "--print --output-format --model --resume --max-turns --json-schema --permission-mode --permission-prompts --effort --tools --strict-mcp-config --mcp-config --system-prompt-snapshot"
    hidden = os.environ.get("FAKE_HIDE_FLAG")
    print(text.replace(hidden, "") if hidden else text)
elif args == ["auth", "status", "--json"]:
    print(json.dumps({"loggedIn": True, "authMethod": "claude.ai",
                      "subscriptionType": "pro", "email": "private@example.com",
                      "apiKey": "sk-ant-MUST-NOT-LEAK", **json.loads(os.environ.get("FAKE_AUTH", "{}"))}))
    sys.exit(int(os.environ.get("FAKE_AUTH_EXIT", "0")))
elif "--print" in args:
    prompt = sys.stdin.read()
    capture = os.environ.get("FAKE_CAPTURE")
    if capture:
        pathlib.Path(capture).write_text(json.dumps({"args": args, "stdin": prompt,
            "cwd": os.getcwd(), "policy": os.environ.get("TEST_POLICY"),
            "autoupdate": os.environ.get("DISABLE_AUTOUPDATER"),
            "updates": os.environ.get("DISABLE_UPDATES"),
            "plugin_autoupdate": os.environ.get("FORCE_AUTOUPDATE_PLUGINS")}))
    action = os.environ.get("FAKE_ACTION", "success")
    if action == "timeout":
        time.sleep(10)
    if action == "write":
        pathlib.Path("claude-output.txt").write_text("Claude read shared workspace and wrote this file.\n")
    if action == "corrupt_state":
        pathlib.Path(".ai/HANDOFF.md").unlink()
        pathlib.Path(".ai/HANDOFF.md").symlink_to(os.environ["FAKE_OUTSIDE"])
    if action == "handoff_drift":
        with pathlib.Path(".ai/HANDOFF.md").open("a") as handle:
            handle.write("New independent change during CLI run.\n")
    if action == "malformed":
        print("raw secret sk-ant-MUST-NOT-LEAK"); sys.exit(0)
    if action == "nonzero":
        print("raw secret sk-ant-MUST-NOT-LEAK", file=sys.stderr); sys.exit(9)
    sid = os.environ.get("FAKE_SESSION", "11111111-1111-4111-8111-111111111111")
    result = {"type": "result", "subtype": "success", "is_error": False,
              "duration_ms": 25, "duration_api_ms": 20,
              "session_id": sid, "permission_denials": [], "total_cost_usd": 0,
              "modelUsage": {"claude-sonnet-4-6": {"inputTokens": 123, "costUSD": 1.5},
                             "malicious-private-value": {"inputTokens": 999}},
              "structured_output": {"Task": "Offline fixture task", "Summary": "Completed fixture.",
                "FilesChanged": ["claude-output.txt"] if action == "write" else [],
                "Tests": ["Model claim: fixture tests passed"], "Decisions": [],
                "RemainingIssues": [], "RecommendedNextStep": "GPT independently verify changes."}}
    if action in {"permission", "permission_nonzero"}:
        result["permission_denials"] = [{"tool_name": "Bash", "tool_use_id": "id1", "tool_input": {"command": "secret private command"}}]
    if action == "error":
        result["is_error"] = True; result["subtype"] = "error_max_turns"
    if action == "leak":
        result["structured_output"]["Summary"] = "ANTHROPIC_API_KEY=sk-ant-MUST-NOT-LEAK Bearer sensitive-token-value"
        result["structured_output"]["apiKey"] = "sk-ant-MUST-NOT-LEAK"
    if action == "json_leak":
        result["structured_output"]["Summary"] = '{"password":"DUMMY_JSON_PASSWORD", "api_key":"DUMMY_JSON_API_KEY", "cookie":"DUMMY_COOKIE", "normal":"KEEP_PUBLIC_VALUE"}'
    if action == "invalid_timings":
        result["duration_ms"] = -1
        result["duration_api_ms"] = float("nan")
    print(json.dumps(result))
    if action == "permission_nonzero":
        sys.exit(9)
else:
    print("Unexpected fixture arguments", file=sys.stderr); sys.exit(91)
