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
    text = "--print --output-format --model --resume --max-turns --json-schema --permission-mode --permission-prompts --effort --tools --strict-mcp-config --mcp-config --system-prompt-snapshot --verbose"
    hidden = os.environ.get("FAKE_HIDE_FLAG")
    print(text.replace(hidden, "") if hidden else text)
elif args == ["auth", "status", "--json"]:
    print(json.dumps({"loggedIn": True, "authMethod": "claude.ai",
                      "subscriptionType": "pro", "email": "private@example.com",
                      "apiKey": "sk-ant-MUST-NOT-LEAK", **json.loads(os.environ.get("FAKE_AUTH", "{}"))}))
    sys.exit(int(os.environ.get("FAKE_AUTH_EXIT", "0")))
elif "--print" in args:
    action = os.environ.get("FAKE_ACTION", "success")
    stream = args[args.index("--output-format") + 1] == "stream-json" if "--output-format" in args else False
    if action == "stderr_flood":
        # Fill stderr well past any pipe buffer before reading stdin: a consumer that
        # does not drain stderr while writing the prompt deadlocks here.
        for _ in range(48):
            sys.stderr.write("STDERR_FLOOD_SECRET sk-ant-MUST-NOT-LEAK " + "e" * 65400 + "\n")
        sys.stderr.flush()
    prompt = sys.stdin.read()
    capture = os.environ.get("FAKE_CAPTURE")
    if capture:
        pathlib.Path(capture).write_text(json.dumps({"args": args, "stdin": prompt,
            "cwd": os.getcwd(), "policy": os.environ.get("TEST_POLICY"),
            "autoupdate": os.environ.get("DISABLE_AUTOUPDATER"),
            "updates": os.environ.get("DISABLE_UPDATES"),
            "plugin_autoupdate": os.environ.get("FORCE_AUTOUPDATE_PLUGINS")}))
    if action in {"timeout_group", "descendant_holds_pipe"}:
        # A descendant in the same process group that inherits stdout/stderr.
        import subprocess
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], stdin=subprocess.DEVNULL)
        pathlib.Path(os.environ["FAKE_CHILD_PID"]).write_text(str(child.pid))
    if action == "timeout_group":
        time.sleep(30)
    # Declared-output fixture: stands in for a native Edit/Write that the CLI permitted.
    declared = os.environ.get("FAKE_WRITE_PATH")
    if declared:
        target = pathlib.Path(declared)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(os.environ.get("FAKE_WRITE_CONTENT", "fixture body\n"))
    if action == "timeout":
        time.sleep(10)
    if action == "timeout_partial":
        # Bytes that never form a complete final result, then a stall.
        sys.stdout.write('{"type":"result","session_id":"33333333-3333-4333-8333-333333333333",'
                         '"modelUsage":{"claude-opus-9-9":{}},"note":"PARTIAL_STDOUT_SECRET sk-ant-MUST-NOT-LEAK')
        sys.stdout.flush()
        sys.stderr.write("PARTIAL_STDERR_TEXT sk-ant-MUST-NOT-LEAK")
        sys.stderr.flush()
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
    if stream:
        def emit(event):
            print(json.dumps(event), flush=True)
        emit({"type": "system", "subtype": "init", "session_id": sid, "model": "claude-sonnet-4-6"})
        emit({"type": "assistant", "session_id": sid, "message": {"content": [
            {"type": "text", "text": "ASSISTANT_TEXT_MARKER permission denied sk-ant-MUST-NOT-LEAK"},
            {"type": "tool_use", "name": "Write", "input": {"file_path": "x", "content": "TOOL_INPUT_MARKER"}}]}})
        # An ordinary tool error whose text mentions a denial is NOT a permission event.
        emit({"type": "user", "session_id": sid, "message": {"content": [
            {"type": "tool_result", "is_error": True, "content": "Permission denied TOOL_RESULT_MARKER"}]}})
        if action in {"stream_denial_sleep", "stream_denial_final"}:
            emit({"type": "system", "subtype": "permission_denied", "tool_name": os.environ.get("FAKE_DENIED_TOOL", "Write"),
                  "tool_use_id": "toolu_fixture", "decision_reason_type": "rule",
                  "decision_reason": "PRIVATE_REASON_TEXT", "message": "PRIVATE_MESSAGE_TEXT permission denied",
                  "uuid": "55555555-5555-4555-8555-555555555555", "session_id": sid})
        if action == "stream_denial_sleep":
            time.sleep(30)
        if action == "stream_no_final":
            sys.exit(0)
        if action == "stream_malformed":
            print('{"type":"result","subtype":"succ', flush=True)
        if action == "stream_huge_frame":
            print(json.dumps({"type": "assistant", "pad": "p" * int(os.environ.get("FAKE_FRAME_BYTES", "200000"))}), flush=True)
        if action == "stream_many_frames":
            for _ in range(int(os.environ.get("FAKE_FRAME_COUNT", "40"))):
                print(json.dumps({"type": "assistant", "pad": "p" * int(os.environ.get("FAKE_FRAME_BYTES", "50000"))}), flush=True)
    result = {"type": "result", "subtype": "success", "is_error": False,
              "duration_ms": 25, "duration_api_ms": 20,
              "session_id": sid, "permission_denials": [], "total_cost_usd": 0,
              "modelUsage": {"claude-sonnet-4-6": {"inputTokens": 123, "costUSD": 1.5},
                             "malicious-private-value": {"inputTokens": 999}},
              "structured_output": {"Task": "Offline fixture task", "Summary": "Completed fixture.",
                "FilesChanged": ["claude-output.txt"] if action == "write" else [],
                "Tests": ["Model claim: fixture tests passed"], "Decisions": [],
                "RemainingIssues": [], "RecommendedNextStep": "GPT independently verify changes."}}
    # Unknown top-level fields must never reach results, logs or the Handoff.
    result["debug"] = {"apiKey": "sk-ant-MUST-NOT-LEAK-FINAL", "note": "FINAL_EXTRA_FIELD_MARKER"}
    result["secret_token"] = "sk-ant-MUST-NOT-LEAK-FINAL"
    if action in {"permission", "permission_nonzero", "stream_denial_final"}:
        result["permission_denials"] = [{"tool_name": "Bash", "tool_use_id": "id1", "tool_input": {"command": "secret private command"}}]
    if action in {"no_denials_field", "nonzero_no_denials", "timeout_final_no_denials"}:
        del result["permission_denials"]
    if action == "no_model_usage":
        del result["modelUsage"]
    if action == "oversized":
        sys.stdout.write("x" * 10485761)
        sys.exit(0)
    if action == "truncate":
        result["structured_output"]["Summary"] = "S" * 9000
        result["structured_output"]["Tests"] = ["T" * 8500] + ["short"] * 120
        result["structured_output"]["Decisions"] = ["short"] * 101
        result["structured_output"]["RemainingIssues"] = ["short"] * 100
    if action in {"error", "stream_error_final"}:
        result["is_error"] = True; result["subtype"] = "error_max_turns"
    if action == "leak":
        result["structured_output"]["Summary"] = "ANTHROPIC_API_KEY=sk-ant-MUST-NOT-LEAK Bearer sensitive-token-value"
        result["structured_output"]["apiKey"] = "sk-ant-MUST-NOT-LEAK"
    if action == "json_leak":
        result["structured_output"]["Summary"] = '{"password":"DUMMY_JSON_PASSWORD", "api_key":"DUMMY_JSON_API_KEY", "cookie":"DUMMY_COOKIE", "normal":"KEEP_PUBLIC_VALUE"}'
    if action == "invalid_timings":
        result["duration_ms"] = -1
        result["duration_api_ms"] = float("nan")
    if action == "stream_final_no_newline":
        # A single valid final whose terminating newline never arrives.
        sys.stdout.write(json.dumps(result))
        sys.stdout.flush()
        sys.exit(0)
    print(json.dumps(result), flush=True)
    if action in {"stream_eof_malformed_tail", "stream_timeout_malformed_tail"}:
        # Unterminated, unparseable bytes after an otherwise valid final.
        sys.stdout.write('{"type":"assistant","note":"TAIL_PARTIAL_MARKER')
        sys.stdout.flush()
        if action == "stream_timeout_malformed_tail":
            time.sleep(30)
        sys.exit(0)
    if action == "stream_eof_duplicate_final":
        sys.stdout.write(json.dumps(result))  # a second final, again without newline
        sys.stdout.flush()
        sys.exit(0)
    if action in {"timeout_final", "timeout_final_no_denials"}:
        # A complete final result that is delivered, yet the process does not exit.
        time.sleep(10)
    if action in {"permission_nonzero", "nonzero_no_denials"}:
        sys.exit(9)
else:
    print("Unexpected fixture arguments", file=sys.stderr); sys.exit(91)
