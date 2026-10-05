"""Offline bounded-I/O and stream-event behavior; the fixture never contacts a service.

Event shapes follow the metadata-only record of the real CLI probe: a top-level
system event with subtype permission_denied and a tool_name. Reasons/messages are
never interpreted or retained.
"""
import json
import os
import time
import unittest
from unittest import mock

import test_bridge

FIRST = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
PRIVATE = ("ASSISTANT_TEXT_MARKER", "TOOL_INPUT_MARKER", "TOOL_RESULT_MARKER", "FINAL_EXTRA_FIELD_MARKER",
           "PRIVATE_REASON_TEXT", "PRIVATE_MESSAGE_TEXT", "STDERR_FLOOD_SECRET", "MUST-NOT-LEAK")


class StreamTests(unittest.TestCase):
    git = test_bridge.BridgeTests.git
    invoke = test_bridge.BridgeTests.invoke
    parsed = test_bridge.BridgeTests.parsed
    initialize = test_bridge.BridgeTests.initialize
    bridge_module = test_bridge.BridgeTests.bridge_module

    def setUp(self):
        test_bridge.BridgeTests.setUp(self)
        self.initialize()

    def run_stream(self, *args, task="stream task", extra_env=None, code=0, stream=True):
        command = ["run", "--task", task] + (["--stream-events"] if stream else []) + list(args)
        return self.parsed(self.invoke(*command, extra_env=extra_env), code)

    def sessions(self):
        return (self.project / ".ai/sessions.json").read_bytes()

    def log(self):
        newest = max((self.project / ".ai/logs").glob("*.json"), key=lambda path: path.stat().st_mtime_ns)
        return json.loads(newest.read_text())

    def handoff(self):
        return (self.project / ".ai/HANDOFF.md").read_text().split("<!-- claude-bridge:")[-1]

    def assert_no_private_text(self, *texts):
        for text in texts:
            for marker in PRIVATE:
                self.assertNotIn(marker, text)

    def seed_session(self):
        self.parsed(self.invoke("run", "--task", "seed"))
        self.assertEqual(json.loads(self.sessions())["claude"]["session_id"], FIRST)
        return self.sessions()

    # -- flags ----------------------------------------------------------------
    def test_stream_flag_is_opt_in_standard_only_and_checks_verbose_before_inference(self):
        data = self.parsed(self.invoke("run", "--task", "default json"))
        args = json.loads(self.capture.read_text())["args"]
        self.assertEqual(args[args.index("--output-format") + 1], "json")
        self.assertNotIn("--verbose", args)
        self.assertNotIn("stream_events", data)
        self.capture.unlink()
        dry = self.parsed(self.invoke("run", "--task", "preview", "--stream-events", "--dry-run"))
        self.assertEqual(dry["status"], "dry_run")
        self.assertIs(dry["stream_events"], True)
        self.assertFalse(self.capture.exists())
        # Missing capability blocks; it never silently downgrades to the JSON path.
        data = self.run_stream(extra_env={"FAKE_HIDE_FLAG": "--verbose"}, code=3)
        self.assertEqual(data["reason"], "required_cli_flags_unverified")
        self.assertEqual(data["unsupported_flags"], ["--verbose"])
        self.assertIs(data["inference"], False)
        self.assertFalse(self.capture.exists())
        # The default JSON path does not need --verbose.
        self.parsed(self.invoke("run", "--task", "json ok", extra_env={"FAKE_HIDE_FLAG": "--verbose"}))
        self.capture.unlink()
        for extra in ((), ("--dry-run",)):
            data = self.parsed(self.invoke("run", "--workflow", "consult", "--task", "analysis",
                                           "--stream-events", *extra), 3)
            self.assertEqual(data["reason"], "stream_events_not_allowed_in_consult_workflow")
            self.assertIs(data["inference"], False)
            self.assertFalse(self.capture.exists())

    def test_stream_command_uses_official_flags_only(self):
        self.run_stream()
        args = json.loads(self.capture.read_text())["args"]
        self.assertEqual(args[args.index("--output-format") + 1], "stream-json")
        self.assertIn("--verbose", args)
        self.assertNotIn("--include-partial-messages", args)
        for unsafe in ("--dangerously-skip-permissions", "--allowedTools", "--bare"):
            self.assertNotIn(unsafe, args)
        self.assertEqual(args[args.index("--permission-prompts") + 1], "none")

    # -- shared final-result handling --------------------------------------------
    def test_stream_success_shares_schema_model_session_checks_and_ignores_ordinary_tool_errors(self):
        result = self.invoke("run", "--task", "stream ok", "--stream-events",
                             extra_env={"FAKE_ACTION": "leak"})
        data = self.parsed(result)
        self.assertEqual(data["status"], "complete")
        self.assertEqual(data["actual_models"], ["claude-sonnet-4-6"])
        self.assertEqual(data["actual_models_status"], "reported")
        self.assertEqual(data["session_id"], FIRST)
        self.assertEqual(json.loads(self.sessions())["claude"]["session_id"], FIRST)
        self.assertEqual(data["permission_denials_status"], "none_reported")
        events = data["stream_events"]
        self.assertEqual((events["events"]["system"], events["events"]["assistant"],
                          events["events"]["user"], events["events"]["result"]), (1, 1, 1, 1))
        self.assertEqual(events["permission_denied_events"], 0)
        self.assertEqual(events["invalid_lines"], 0)
        self.assertTrue(events["final_result_seen"])
        self.assertEqual(data["cli_output"]["stdout_format"], "stream_json")
        self.assertEqual(self.log()["stream_events"], events)
        self.assert_no_private_text(result.stdout + result.stderr, json.dumps(self.log()), self.handoff())
        # Same schema validation: oversized fields are flagged exactly as on the JSON path.
        data = self.run_stream(extra_env={"FAKE_ACTION": "truncate"})
        self.assertIs(data["result_complete"], False)
        self.assertIn("Summary", data["truncated_result_fields"])

    def test_stream_unsuccessful_final_reports_returned_session_without_persisting_it(self):
        prior = self.seed_session()
        data = self.run_stream(extra_env={"FAKE_ACTION": "stream_error_final", "FAKE_SESSION": OTHER}, code=4)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["session_id"], OTHER)
        self.assertEqual(data["returned_session_id_status"], "returned")
        self.assertIs(data["session_saved"], False)
        self.assertEqual(data["actual_models"], ["claude-sonnet-4-6"])
        self.assertEqual(prior, self.sessions())
        self.assertEqual(self.log()["session_id"], OTHER)
        self.assertIs(self.log()["session_saved"], False)

    def test_genuine_final_result_ids_are_reported_but_never_persisted_unless_complete(self):
        prior = self.seed_session()
        cases = (("permission", 4, "needs_permission"), ("permission_nonzero", 4, "failed"),
                 ("error", 4, "failed"), ("timeout_final", 4, "timeout"))
        for action, code, status in cases:
            with self.subTest(action=action):
                data = self.parsed(self.invoke("run", "--task", "final " + action, "--timeout", "1.5",
                                               extra_env={"FAKE_ACTION": action, "FAKE_SESSION": OTHER}), code)
                self.assertEqual(data["status"], status)
                self.assertEqual(data["session_id"], OTHER)
                self.assertEqual(data["returned_session_id_status"], "returned")
                self.assertIs(data["session_saved"], False)
                self.assertEqual(data["resumed_session"], FIRST)
                self.assertEqual(prior, self.sessions())
                self.assertIn(OTHER, self.handoff())
                self.assertIn("not saved", self.handoff())

    # -- immediate official denial -----------------------------------------------
    def test_official_permission_denied_event_stops_promptly_without_saving_a_session(self):
        prior = self.seed_session()
        started = time.monotonic()
        result = self.invoke("run", "--task", "denied write", "--stream-events", "--timeout", "60",
                             extra_env={"FAKE_ACTION": "stream_denial_sleep", "FAKE_SESSION": OTHER})
        elapsed = time.monotonic() - started
        data = self.parsed(result, 4)
        self.assertLess(elapsed, 10)  # the fixture would otherwise sleep for 30 seconds
        self.assertEqual(data["status"], "needs_permission")
        self.assertEqual(data["permission_denials"], ["Write"])
        self.assertEqual(data["permission_denials_status"], "listed")
        self.assertEqual(data["stream_events"]["permission_denied_events"], 1)
        self.assertEqual(data["termination"]["reason"], "permission_denied_event")
        self.assertEqual(data["termination"]["completion"], "incomplete")
        self.assertIn(data["termination"]["signal_sent"], {"SIGTERM", "SIGKILL"})
        # No final result was received: nothing about models or session is claimed.
        self.assertEqual(data["actual_models"], [])
        self.assertEqual(data["actual_models_status"], "unavailable")
        self.assertIsNone(data["session_id"])
        self.assertEqual(data["returned_session_id_status"], "unavailable")
        self.assertIs(data["session_saved"], False)
        self.assertEqual(prior, self.sessions())
        log = self.log()
        self.assertEqual(log["permission_denials"], ["Write"])
        self.assertEqual(log["permission_denials_status"], "listed")
        self.assert_no_private_text(result.stdout + result.stderr, json.dumps(log), self.handoff())
        self.assertIn("Permission denials: listed (Write)", self.handoff())

    def test_unknown_denied_tool_is_other_and_text_lookalikes_are_not_events(self):
        data = self.run_stream(extra_env={"FAKE_ACTION": "stream_denial_sleep", "FAKE_DENIED_TOOL": "mcp__private__tool"}, code=4)
        self.assertEqual(data["permission_denials"], ["Other"])
        self.assertNotIn("mcp__private__tool", json.dumps(data) + json.dumps(self.log()))
        # The success fixture carries an is_error tool_result and assistant text that both say
        # "permission denied"; neither may abort the run.
        data = self.run_stream()
        self.assertEqual(data["status"], "complete")

    def test_stream_without_final_result_is_unavailable_not_complete(self):
        prior = self.seed_session()
        data = self.run_stream(extra_env={"FAKE_ACTION": "stream_no_final", "FAKE_SESSION": OTHER}, code=4)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["reason"], "claude_stream_final_result_unavailable")
        self.assertIsNone(data["permission_denials"])
        self.assertEqual(data["permission_denials_status"], "unavailable")
        self.assertEqual(data["actual_models_status"], "unavailable")
        self.assertIsNone(data["session_id"])
        self.assertFalse(data["stream_events"]["final_result_seen"])
        self.assertEqual(prior, self.sessions())

    def test_malformed_critical_stream_line_never_becomes_completion(self):
        prior = self.seed_session()
        # A valid final follows the broken line; it must still not be trusted.
        data = self.run_stream(extra_env={"FAKE_ACTION": "stream_malformed", "FAKE_SESSION": OTHER}, code=4)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["reason"], "claude_stream_malformed_frame")
        self.assertEqual(data["cli_output"]["stdout_format"], "stream_malformed")
        self.assertEqual(data["stream_events"]["invalid_lines"], 1)
        self.assertEqual(data["termination"]["reason"], "malformed_stream_frame")
        self.assertEqual(data["permission_denials_status"], "unavailable")
        self.assertIsNone(data["session_id"])
        self.assertEqual(prior, self.sessions())

    def assert_untrusted_final(self, data, prior):
        self.assertIsNone(data["session_id"])
        self.assertEqual(data["returned_session_id_status"], "unavailable")
        self.assertIs(data["session_saved"], False)
        self.assertEqual(data["actual_models"], [])
        self.assertEqual(data["actual_models_status"], "unavailable")
        self.assertIsNone(data["permission_denials"])
        self.assertEqual(data["permission_denials_status"], "unavailable")
        self.assertNotIn("result", data)
        self.assertEqual(data["stream_events"]["invalid_lines"], 1)
        self.assertIs(data["stream_events"]["final_result_trusted"], False)
        self.assertEqual(data["cli_output"]["stdout_format"], "stream_malformed")
        self.assertEqual(prior, self.sessions())
        log = self.log()
        self.assertIsNone(log["session_id"])
        self.assertEqual(log["actual_models_status"], "unavailable")
        self.assertEqual(log["permission_denials_status"], "unavailable")

    def test_unterminated_bad_tail_after_a_valid_final_cannot_revive_that_final(self):
        prior = self.seed_session()
        for action in ("stream_eof_malformed_tail", "stream_eof_duplicate_final"):
            with self.subTest(action=action):
                result = self.invoke("run", "--task", "tail " + action, "--stream-events",
                                     extra_env={"FAKE_ACTION": action, "FAKE_SESSION": OTHER})
                data = self.parsed(result, 4)
                self.assertEqual(data["status"], "failed")
                self.assertEqual(data["reason"], "claude_stream_malformed_frame")
                self.assert_untrusted_final(data, prior)
                # The child had already exited on its own: no signal is invented for an EOF-only finding.
                termination = data["termination"]
                self.assertEqual(termination["reason"], "malformed_stream_frame")
                self.assertIsNone(termination["signal_sent"])
                self.assertIsNone(termination["exit_signal"])
                self.assertEqual(termination["exit_code"], 0)
                self.assertEqual(termination["completion"], "unknown")
                self.assertLess(data["cli_output"]["stdout_bytes"], 20000)
                self.assert_no_private_text(result.stdout, json.dumps(self.log()), self.handoff())
                self.assertNotIn("TAIL_PARTIAL_MARKER", result.stdout + json.dumps(self.log()) + self.handoff())

    def test_single_valid_final_without_trailing_newline_still_completes(self):
        data = self.run_stream(extra_env={"FAKE_ACTION": "stream_final_no_newline", "FAKE_SESSION": OTHER})
        self.assertEqual(data["status"], "complete")
        self.assertEqual(data["session_id"], OTHER)
        self.assertEqual(json.loads(self.sessions())["claude"]["session_id"], OTHER)
        self.assertEqual(data["actual_models"], ["claude-sonnet-4-6"])
        self.assertEqual(data["stream_events"]["invalid_lines"], 0)
        self.assertIs(data["stream_events"]["final_result_trusted"], True)
        self.assertNotIn("termination", data)

    def test_timeout_with_malformed_tail_stays_timeout_without_trusting_the_final(self):
        prior = self.seed_session()
        started = time.monotonic()
        data = self.run_stream("--timeout", "1.5", extra_env={
            "FAKE_ACTION": "stream_timeout_malformed_tail", "FAKE_SESSION": OTHER}, code=4)
        self.assertLess(time.monotonic() - started, 12)
        self.assertEqual(data["status"], "timeout")
        self.assertEqual(data["termination"]["reason"], "timeout")
        self.assertIn(data["termination"]["signal_sent"], {"SIGTERM", "SIGKILL"})
        self.assertEqual(data["termination"]["completion"], "unknown")
        self.assert_untrusted_final(data, prior)

    # -- bounded I/O ---------------------------------------------------------------
    def test_large_prompt_with_stderr_flood_cannot_deadlock_and_stderr_text_never_leaks(self):
        ai = self.project / ".ai"
        for name in ("PROJECT_CONTEXT.md", "DECISIONS.md", "HANDOFF.md"):
            (ai / name).write_text(("context line for " + name + "\n") * 500)
        for stream in (False, True):
            with self.subTest(stream=stream):
                started = time.monotonic()
                result = self.invoke("run", "--task", "t" * 32000, *(["--stream-events"] if stream else []),
                                     extra_env={"FAKE_ACTION": "stderr_flood"})
                data = self.parsed(result)
                self.assertLess(time.monotonic() - started, 15)
                self.assertEqual(data["status"], "complete")
                self.assertGreater(len(json.loads(self.capture.read_text())["stdin"]), 65536)
                self.assertGreater(data["cli_output"]["stderr_bytes"], 3000000)
                self.assertEqual(data["cli_output"]["stderr"], "present_not_recorded")
                self.assert_no_private_text(result.stdout + result.stderr, json.dumps(self.log()), self.handoff())

    def test_frame_total_and_stderr_bounds_fail_safely(self):
        module = self.bridge_module()
        command = [str(self.fake), "--print", "--output-format", "stream-json", "--verbose"]
        cases = (("stream_huge_frame", {"STREAM_FRAME_LIMIT": 65536}, "claude_stream_frame_too_large"),
                 ("stream_many_frames", {"STREAM_TOTAL_LIMIT": 1048576}, "claude_output_too_large"),
                 ("stderr_flood", {"CLI_STDERR_LIMIT": 200000}, "claude_stderr_too_large"))
        for action, limits, reason in cases:
            with self.subTest(action=action):
                with mock.patch.dict(os.environ, {"FAKE_ACTION": action}):
                    with mock.patch.multiple(module, **limits):
                        started = time.monotonic()
                        outcome, session = module.run_inference(command, "prompt", self.project, 20, stream=True)
                self.assertLess(time.monotonic() - started, 12)
                self.assertEqual(outcome["status"], "failed")
                self.assertEqual(outcome["reason"], reason)
                self.assertIsNone(session)
                self.assertEqual(outcome["permission_denials_status"], "unavailable")
                self.assertEqual(outcome["termination"]["completion"], "unknown")
                self.assertNotIn("result", outcome)
                self.assert_no_private_text(json.dumps(outcome))

    def test_json_path_oversized_output_is_cut_off_without_unbounded_buffering(self):
        module = self.bridge_module()
        command = [str(self.fake), "--print", "--output-format", "json"]
        with mock.patch.dict(os.environ, {"FAKE_ACTION": "oversized"}), mock.patch.object(module, "CLI_STDOUT_LIMIT", 100000):
            outcome, session = module.run_inference(command, "prompt", self.project, 20)
        self.assertEqual(outcome["reason"], "claude_output_too_large")
        self.assertEqual(outcome["cli_output"]["stdout_format"], "too_large")
        self.assertGreater(outcome["cli_output"]["stdout_bytes"], 100000)
        self.assertLess(outcome["cli_output"]["stdout_bytes"], 10485761)
        self.assertIsNone(session)

    def child_gone(self, pid_file):
        pid = int(pid_file.read_text())
        for _ in range(100):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.05)
        return False

    def test_timeout_terminates_the_process_group_and_retains_bounded_diagnostics(self):
        prior = self.seed_session()
        for stream in (False, True):
            with self.subTest(stream=stream):
                pid_file = self.root / "child.pid"
                started = time.monotonic()
                result = self.invoke("run", "--task", "group", "--timeout", "1.5", *(["--stream-events"] if stream else []),
                                     extra_env={"FAKE_ACTION": "timeout_group", "FAKE_CHILD_PID": str(pid_file)})
                data = self.parsed(result, 4)
                self.assertLess(time.monotonic() - started, 12)
                self.assertEqual(data["status"], "timeout")
                self.assertEqual(data["termination"]["reason"], "timeout")
                self.assertEqual(data["termination"]["timeout_seconds"], 1.5)
                self.assertEqual(data["termination"]["completion"], "unknown")
                self.assertTrue(self.child_gone(pid_file), "descendant survived forced termination")
                self.assertIsNone(data["session_id"])
                self.assertEqual(data["permission_denials_status"], "unavailable")
                self.assertEqual(prior, self.sessions())

    def test_descendant_holding_pipes_after_leader_exit_cannot_hang_the_run(self):
        pid_file = self.root / "child.pid"
        started = time.monotonic()
        data = self.parsed(self.invoke("run", "--task", "held pipes", "--timeout", "60",
                                       extra_env={"FAKE_ACTION": "descendant_holds_pipe", "FAKE_CHILD_PID": str(pid_file)}))
        self.assertLess(time.monotonic() - started, 12)
        # The leader's complete final result is still honoured; the straggler is killed.
        self.assertEqual(data["status"], "complete")
        self.assertIs(data["cli_output"]["descendants_held_pipes"], True)
        self.assertTrue(self.child_gone(pid_file), "descendant survived cleanup")


if __name__ == "__main__":
    unittest.main()
