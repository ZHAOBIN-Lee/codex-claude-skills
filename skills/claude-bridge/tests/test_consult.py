"""Offline continuation behavior; subprocess fixture never contacts a model."""
import json
import fcntl
import os
import stat
import unittest
from unittest import mock

import test_bridge


class ConsultTests(unittest.TestCase):
    # Reuse fixture helpers without inheriting/recollecting the standard suite.
    git = test_bridge.BridgeTests.git
    invoke = test_bridge.BridgeTests.invoke
    parsed = test_bridge.BridgeTests.parsed
    initialize = test_bridge.BridgeTests.initialize
    bridge_module = test_bridge.BridgeTests.bridge_module

    def setUp(self):
        test_bridge.BridgeTests.setUp(self)
        config = json.loads(self.config.read_text())
        config["usage_credits_confirmation"] = {
            "source": "user", "date": "2026-10-04", "timezone": "Australia/Melbourne"}
        self.config.write_text(json.dumps(config))
        self.initialize()

    def consult(self, task="consult task", *args, extra_env=None):
        return self.invoke("run", "--workflow", "consult", "--task", task,
                           *args, extra_env=extra_env)

    def captured(self):
        return json.loads(self.capture.read_text())

    def cache_path(self):
        return self.project / ".ai" / "consult.json"

    def cache(self):
        return json.loads(self.cache_path().read_text())

    def private_files(self):
        return {str(path.relative_to(self.project)): path.read_bytes()
                for path in (self.project / ".ai").rglob("*") if path.is_file()}

    def add_stable_context(self):
        (self.project / ".ai" / "PROJECT_CONTEXT.md").write_text("PRIVATE_PROJECT_CONTEXT_MARKER\n")
        (self.project / ".ai" / "DECISIONS.md").write_text("PRIVATE_DECISION_MARKER\n")
        (self.project / "AGENTS.md").write_text("PRIVATE_INSTRUCTION_MARKER\n")

    def test_first_full_then_resume_sends_only_changed_context_and_new_task(self):
        self.add_stable_context()
        first = self.parsed(self.consult("FIRST_PRIVATE_TASK"))
        prompt = self.captured()["stdin"]
        self.assertEqual(first["workflow"], "consult")
        self.assertEqual(first["context_delivery"], "full")
        self.assertIsNone(first["resumed_session"])
        for marker in ("FIRST_PRIVATE_TASK", "PRIVATE_PROJECT_CONTEXT_MARKER",
                       "PRIVATE_DECISION_MARKER", "PRIVATE_INSTRUCTION_MARKER"):
            self.assertIn(marker, prompt)
        second = self.parsed(self.consult("SECOND_PRIVATE_TASK"))
        capture = self.captured()
        self.assertEqual(second["context_delivery"], "delta")
        self.assertEqual(second["changed_context_names"], [])
        self.assertEqual(second["resumed_session"], first["session_id"])
        self.assertEqual(capture["args"][capture["args"].index("--resume") + 1], first["session_id"])
        self.assertIn("SECOND_PRIVATE_TASK", capture["stdin"])
        for marker in ("FIRST_PRIVATE_TASK", "PRIVATE_PROJECT_CONTEXT_MARKER",
                       "PRIVATE_DECISION_MARKER", "PRIVATE_INSTRUCTION_MARKER"):
            self.assertNotIn(marker, capture["stdin"])
        self.assertLess(second["prompt_bytes"], first["prompt_bytes"])
        self.assertEqual(second["prompt_bytes"], len(capture["stdin"].encode("utf-8")))

    def test_changed_documents_instructions_and_git_are_sent_on_resume(self):
        self.add_stable_context()
        self.parsed(self.consult())
        (self.project / ".ai" / "PROJECT_CONTEXT.md").write_text("CHANGED_PROJECT_CONTEXT\n")
        with (self.project / ".ai" / "HANDOFF.md").open("a") as handoff:
            handoff.write("INDEPENDENT_HUMAN_HANDOFF_PROOF\n")
        (self.project / "AGENTS.md").write_text("CHANGED_INSTRUCTIONS\n")
        (self.project / "shared.txt").write_text("CHANGED_GIT_PROOF\n")
        second = self.parsed(self.consult("inspect the changes"))
        changed = second["changed_context_names"]
        self.assertEqual(second["context_delivery"], "delta")
        self.assertIn("PROJECT_CONTEXT.md", changed)
        self.assertIn("HANDOFF.md", changed)
        self.assertIn("instructions:" + str((self.project / "AGENTS.md").resolve()), changed)
        self.assertIn("Git", changed)
        prompt = self.captured()["stdin"]
        for marker in ("CHANGED_PROJECT_CONTEXT", "INDEPENDENT_HUMAN_HANDOFF_PROOF",
                       "CHANGED_INSTRUCTIONS", "CHANGED_GIT_PROOF"):
            self.assertIn(marker, prompt)
        self.assertNotIn("PRIVATE_DECISION_MARKER", prompt)

    def test_added_and_deleted_instruction_files_are_explicit_changes(self):
        self.parsed(self.consult())
        instruction = self.project / "AGENTS.md"
        instruction.write_text("NEW_INSTRUCTIONS_PROOF\n")
        added = self.parsed(self.consult("instruction added"))
        key = "instructions:" + str(instruction.resolve())
        self.assertIn(key, added["changed_context_names"])
        self.assertIn("NEW_INSTRUCTIONS_PROOF", self.captured()["stdin"])
        instruction.unlink()
        deleted = self.parsed(self.consult("instruction deleted"))
        prompt = self.captured()["stdin"]
        self.assertIn(key, deleted["changed_context_names"])
        self.assertIn("AGENTS.md", prompt)
        self.assertRegex(prompt.lower(), r"deleted|removed|missing|absent|unavailable")
        self.assertNotIn("NEW_INSTRUCTIONS_PROOF", prompt)

    def test_instruction_rules_beyond_old_prefix_are_complete_on_first_and_delta(self):
        instruction = self.project / "AGENTS.md"
        instruction.write_text("instruction preface\n" + "x" * 15000 + "\nLATE_RULE_ORIGINAL_PROOF\n")
        key = "instructions:" + str(instruction.resolve())
        first = self.parsed(self.consult("respect all project rules"))
        self.assertIn("LATE_RULE_ORIGINAL_PROOF", self.captured()["stdin"])
        self.assertNotIn(key, first["truncated_context_names"])
        instruction.write_text("instruction preface\n" + "x" * 15000 + "\nLATE_RULE_CHANGED_PROOF\n")
        second = self.parsed(self.consult("the final rule changed"))
        self.assertEqual(second["context_delivery"], "delta")
        self.assertIn(key, second["changed_context_names"])
        self.assertNotIn(key, second["truncated_context_names"])
        self.assertIn("LATE_RULE_CHANGED_PROOF", self.captured()["stdin"])
        self.assertNotIn("LATE_RULE_ORIGINAL_PROOF", self.captured()["stdin"])

    def test_instruction_aggregate_over_budget_blocks_before_inference(self):
        # Two independently reasonable files must still obey the total rules budget.
        (self.project / "AGENTS.md").write_text("a" * 48001)
        (self.project / "CLAUDE.md").write_text("b" * 48001)
        data = self.parsed(self.consult(), 3)
        self.assertEqual(data["reason"], "consult_instruction_context_too_large")
        self.assertFalse(data["inference"])
        self.assertFalse(self.capture.exists())
        self.assertFalse(self.cache_path().exists())

    def test_project_change_outside_bounded_view_reports_truncation_and_requires_material(self):
        context = self.project / ".ai" / "PROJECT_CONTEXT.md"
        context.write_text("P" * 13000 + "\nOUTSIDE_VIEW_OLD_PROOF\n")
        first = self.parsed(self.consult("inspect supplied evidence"))
        self.assertIn("PROJECT_CONTEXT.md", first["truncated_context_names"])
        self.assertIn("TRUNCATED context section: PROJECT_CONTEXT.md", self.captured()["stdin"])
        self.assertNotIn("OUTSIDE_VIEW_OLD_PROOF", self.captured()["stdin"])
        context.write_text("P" * 13000 + "\nOUTSIDE_VIEW_NEW_PROOF\n")
        second = self.parsed(self.consult("a source change occurred"))
        self.assertEqual(second["context_delivery"], "delta")
        self.assertIn("PROJECT_CONTEXT.md", second["changed_context_names"])
        self.assertIn("PROJECT_CONTEXT.md", second["truncated_context_names"])
        prompt = self.captured()["stdin"]
        self.assertIn("TRUNCATED context section: PROJECT_CONTEXT.md", prompt)
        self.assertIn("Changed content may be outside that view", prompt)
        self.assertNotIn("OUTSIDE_VIEW_NEW_PROOF", prompt)

    def test_project_without_git_reports_unavailable_evidence(self):
        self.project = self.root / "nongit-project"
        self.project.mkdir()
        self.initialize()
        data = self.parsed(self.consult("analyze only available evidence"))
        self.assertEqual(data["unavailable_context_names"], ["Git"])
        self.assertFalse(data["git_before"]["available"])
        self.assertIn("unknown", self.captured()["stdin"].lower())

    def test_mode_change_new_session_and_standard_run_refresh_full_context(self):
        self.add_stable_context()
        self.parsed(self.consult())
        switched = self.parsed(self.consult("mode changed", "--mode", "opus"))
        self.assertEqual(switched["context_delivery"], "full")
        self.assertIn("PRIVATE_PROJECT_CONTEXT_MARKER", self.captured()["stdin"])
        unchanged = self.parsed(self.consult("same opus", "--mode", "opus"))
        self.assertEqual(unchanged["context_delivery"], "delta")
        fresh = self.parsed(self.consult("explicit new", "--mode", "opus", "--new-session"))
        self.assertEqual(fresh["context_delivery"], "full")
        self.assertNotIn("--resume", self.captured()["args"])
        self.parsed(self.invoke("run", "--task", "standard intervening task", "--mode", "opus"))
        after_standard = self.parsed(self.consult("return to consult", "--mode", "opus"))
        self.assertEqual(after_standard["context_delivery"], "full")
        self.assertIn("PRIVATE_PROJECT_CONTEXT_MARKER", self.captured()["stdin"])

    def test_missing_malformed_or_unmatched_cache_uses_full_context(self):
        self.add_stable_context()
        self.parsed(self.consult())
        self.cache_path().unlink()
        self.assertEqual(self.parsed(self.consult())["context_delivery"], "full")
        self.cache_path().write_text("not JSON")
        self.assertEqual(self.parsed(self.consult())["context_delivery"], "full")
        for field, value in (("project", "/different-project"), ("mode", "opus"),
                             ("session_id", "22222222-2222-4222-8222-222222222222"),
                             ("schema_version", 999)):
            with self.subTest(field=field):
                cache = self.cache()
                cache[field] = value
                self.cache_path().write_text(json.dumps(cache))
                data = self.parsed(self.consult())
                self.assertEqual(data["context_delivery"], "full")
                self.assertIn("PRIVATE_PROJECT_CONTEXT_MARKER", self.captured()["stdin"])

    def test_unknown_cache_section_names_fall_back_full_without_echoing_untrusted_names(self):
        self.parsed(self.consult())
        for name in ("PRIVATE_UNTRUSTED_CACHE_NAME", "instructions:/outside/PRIVATE_UNTRUSTED_CACHE_NAME"):
            with self.subTest(name=name):
                cache = self.cache()
                cache["fingerprints"][name] = "a" * 64
                self.cache_path().write_text(json.dumps(cache))
                result = self.consult("refresh trusted context")
                data = self.parsed(result)
                self.assertEqual(data["context_delivery"], "full")
                self.assertNotIn("PRIVATE_UNTRUSTED_CACHE_NAME", result.stdout + result.stderr)
                self.assertNotIn("PRIVATE_UNTRUSTED_CACHE_NAME", self.captured()["stdin"])
                for path in (self.project / ".ai" / "logs").glob("*.json"):
                    self.assertNotIn("PRIVATE_UNTRUSTED_CACHE_NAME", path.read_text())

    def test_legacy_private_ignore_patterns_migrate_only_on_real_consult_with_backup(self):
        ignore = self.project / ".ai" / ".gitignore"
        lines = [line for line in ignore.read_text().splitlines() if line not in ("consult.json", "requests/")]
        legacy = "\n".join(lines) + "\n# preserve custom local patterns\ncustom-private/\n"
        ignore.write_text(legacy)
        before = self.private_files()
        self.parsed(self.consult("preview legacy project", "--dry-run"))
        self.assertEqual(self.private_files(), before)
        self.assertFalse(self.capture.exists())
        self.parsed(self.consult("consult existing initialized project"))
        migrated = ignore.read_text()
        self.assertTrue(migrated.startswith(legacy))
        self.assertIn("consult.json", migrated.splitlines())
        self.assertIn("requests/", migrated.splitlines())
        self.assertEqual(self.git("check-ignore", ".ai/consult.json").strip(), ".ai/consult.json")
        self.assertEqual(self.git("check-ignore", ".ai/requests/future.txt").strip(), ".ai/requests/future.txt")
        backups = list((self.project / ".ai" / "backups").glob("gitignore.*.bak"))
        self.assertTrue(backups)
        self.assertIn(legacy, [path.read_text() for path in backups])

    def test_cache_is_private_ignored_fingerprint_metadata_without_prompt_content(self):
        self.add_stable_context()
        self.parsed(self.consult("PRIVATE_CACHE_TASK"))
        cache = self.cache()
        self.assertEqual(cache["schema_version"], 1)
        self.assertEqual(cache["project"], str(self.project.resolve()))
        self.assertEqual(cache["mode"], "default")
        self.assertEqual(cache["session_id"], "11111111-1111-4111-8111-111111111111")
        self.assertTrue(cache["fingerprints"])
        for value in cache["fingerprints"].values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")
        text = self.cache_path().read_text()
        for marker in ("PRIVATE_CACHE_TASK", "PRIVATE_PROJECT_CONTEXT_MARKER",
                       "PRIVATE_DECISION_MARKER", "PRIVATE_INSTRUCTION_MARKER"):
            self.assertNotIn(marker, text)
        self.assertEqual(stat.S_IMODE(self.cache_path().stat().st_mode), 0o600)
        self.assertEqual(self.git("check-ignore", ".ai/consult.json").strip(), ".ai/consult.json")

    def test_cache_symlink_or_public_permissions_block_before_inference(self):
        outside = self.root / "outside-cache.json"
        outside.write_text("outside original")
        self.cache_path().symlink_to(outside)
        data = self.parsed(self.consult(), 3)
        self.assertEqual(data["status"], "blocked")
        self.assertFalse(self.capture.exists())
        self.assertEqual(outside.read_text(), "outside original")
        self.cache_path().unlink()
        self.cache_path().write_text("{}")
        self.cache_path().chmod(0o644)
        data = self.parsed(self.consult(), 3)
        self.assertEqual(data["status"], "blocked")
        self.assertFalse(self.capture.exists())

    def test_failed_or_denied_consult_keeps_good_session_and_requires_full_refresh(self):
        self.parsed(self.consult("successful baseline"))
        sessions = (self.project / ".ai" / "sessions.json").read_bytes()
        for action in ("permission", "nonzero", "malformed", "error"):
            with self.subTest(action=action):
                self.parsed(self.consult("failing continuation", extra_env={"FAKE_ACTION": action}), 4)
                self.assertFalse(self.cache_path().exists())
                self.assertEqual((self.project / ".ai" / "sessions.json").read_bytes(), sessions)
                refreshed = self.parsed(self.consult("recover with complete context"))
                self.assertEqual(refreshed["context_delivery"], "full")

    def test_task_file_accepts_regular_utf8_relative_or_absolute_project_file(self):
        requests = self.project / ".ai" / "requests"
        requests.mkdir()
        path = requests / "current.txt"
        path.write_text("TASK_FILE_PRIVATE_PROOF 中文任务\n", encoding="utf-8")
        for raw in (".ai/requests/current.txt", str(path)):
            with self.subTest(path=raw):
                data = self.parsed(self.invoke("run", "--workflow", "consult", "--task-file", raw))
                self.assertEqual(data["status"], "complete")
                self.assertIn("TASK_FILE_PRIVATE_PROOF 中文任务", self.captured()["stdin"])
                self.assertNotIn("TASK_FILE_PRIVATE_PROOF", json.dumps(data, ensure_ascii=False))
        self.assertEqual(self.git("check-ignore", ".ai/requests/current.txt").strip(), ".ai/requests/current.txt")
        self.assertNotIn("TASK_FILE_PRIVATE_PROOF", self.cache_path().read_text())
        for path in (self.project / ".ai" / "logs").glob("*.json"):
            self.assertNotIn("TASK_FILE_PRIVATE_PROOF", path.read_text())

    def test_tracked_request_text_is_excluded_from_git_and_only_sent_as_current_task(self):
        requests = self.project / ".ai" / "requests"
        requests.mkdir()
        for raw in (".ai/requests/current.txt", "question [literal].txt"):
            with self.subTest(path=raw):
                task = self.project / raw
                task.write_text("OLD_PRIVATE_REQUEST_CONTENT\n")
                self.git("add", "-f", raw)
                self.git("commit", "-qm", "tracked task fixture")
                task.write_text("CURRENT_PRIVATE_REQUEST_CONTENT\n")
                self.parsed(self.invoke("run", "--workflow", "consult", "--task-file", raw))
                prompt = self.captured()["stdin"]
                self.assertEqual(prompt.count("CURRENT_PRIVATE_REQUEST_CONTENT"), 1)
                self.assertNotIn("OLD_PRIVATE_REQUEST_CONTENT", prompt)
                task.write_text("NEXT_PRIVATE_REQUEST_CONTENT\n")
                second = self.parsed(self.invoke("run", "--workflow", "consult", "--task-file", raw))
                self.assertEqual(second["context_delivery"], "delta")
                self.assertNotIn("Git", second["changed_context_names"])
                self.assertEqual(self.captured()["stdin"].count("NEXT_PRIVATE_REQUEST_CONTENT"), 1)
                self.assertNotIn("CURRENT_PRIVATE_REQUEST_CONTENT", self.captured()["stdin"])

    def test_task_file_rejects_outside_symlinks_directories_invalid_utf8_and_bounds(self):
        outside = self.root / "outside-task.txt"
        outside.write_text("OUTSIDE_TASK_SHOULD_NOT_READ")
        linked = self.project / "linked-task.txt"
        linked.symlink_to(outside)
        local = self.project / "local-task.txt"
        local.write_text("local task")
        internal_link = self.project / "internal-linked-task.txt"
        internal_link.symlink_to(local)
        linked_dir = self.project / "linked-directory"
        linked_dir.symlink_to(self.project, target_is_directory=True)
        binary = self.project / "invalid-utf8.txt"
        binary.write_bytes(b"\xff\xfeinvalid")
        huge = self.project / "huge.txt"
        huge.write_bytes(b"x" * 128001)
        long_task = self.project / "long.txt"
        long_task.write_text("x" * 32001)
        empty = self.project / "empty.txt"
        empty.write_text("  \n\t")
        fifo = self.project / "task-pipe"
        os.mkfifo(fifo)
        for raw in (str(outside), "../outside-task.txt", str(linked), str(internal_link),
                    "linked-directory/local-task.txt", str(self.project), str(binary),
                    str(huge), str(long_task), str(empty), str(fifo), "missing.txt"):
            with self.subTest(path=raw):
                result = self.invoke("run", "--workflow", "consult", "--task-file", raw)
                data = self.parsed(result, 3)
                self.assertEqual(data["status"], "blocked")
                self.assertFalse(data["inference"])
                self.assertFalse(self.capture.exists())
                self.assertNotIn("OUTSIDE_TASK_SHOULD_NOT_READ", result.stdout + result.stderr)
        self.assertEqual(outside.read_text(), "OUTSIDE_TASK_SHOULD_NOT_READ")

    def test_task_text_and_task_file_are_mutually_exclusive(self):
        path = self.project / "task.txt"
        path.write_text("private file task")
        result = self.invoke("run", "--workflow", "consult", "--task", "private inline task",
                             "--task-file", str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.capture.exists())

    def test_consult_has_no_tools_and_preserves_other_cli_boundaries(self):
        self.parsed(self.consult())
        args = self.captured()["args"]
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("--strict-mcp-config", args)
        self.assertEqual(json.loads(args[args.index("--mcp-config") + 1]), {"mcpServers": {}})
        self.assertEqual(args[args.index("--system-prompt-snapshot") + 1], "off")
        self.assertEqual(args[args.index("--permission-mode") + 1], "manual")
        self.assertEqual(args[args.index("--permission-prompts") + 1], "none")
        self.assertEqual(args[args.index("--effort") + 1], "medium")
        for unsafe in ("--dangerously-skip-permissions", "--allowedTools", "--bare"):
            self.assertNotIn(unsafe, args)
        self.parsed(self.invoke("run", "--task", "standard task"))
        self.assertNotIn("--tools", self.captured()["args"])
        self.assertNotIn("--strict-mcp-config", self.captured()["args"])
        self.assertNotIn("--mcp-config", self.captured()["args"])
        self.assertNotIn("--system-prompt-snapshot", self.captured()["args"])

    def test_missing_no_tool_capability_is_refused_before_consult_inference(self):
        for flag in ("--tools", "--strict-mcp-config", "--mcp-config", "--system-prompt-snapshot"):
            with self.subTest(flag=flag):
                data = self.parsed(self.consult(extra_env={"FAKE_HIDE_FLAG": flag}), 3)
                self.assertEqual(data["reason"], "required_cli_flags_unverified")
                self.assertIn(flag, data["unsupported_flags"])
                self.assertFalse(self.capture.exists())

    def test_consult_retains_route_auth_usage_source_and_permission_guards(self):
        config = json.loads(self.config.read_text())
        for confirmation in (None, {}, {"source": "file", "date": "2026-10-04", "timezone": "Australia/Melbourne"}):
            with self.subTest(confirmation=confirmation):
                config["usage_credits_confirmation"] = confirmation
                self.config.write_text(json.dumps(config))
                data = self.parsed(self.consult(), 3)
                self.assertEqual(data["status"], "blocked")
                self.assertFalse(self.capture.exists())
        config["usage_credits_confirmation"] = {"source": "user", "date": "2026-10-04", "timezone": "Australia/Melbourne"}
        self.config.write_text(json.dumps(config))
        for env in ({"ANTHROPIC_API_KEY": "PRIVATE_ROUTE_SECRET"},
                    {"CLAUDE_CODE_EFFORT_LEVEL": "PRIVATE_EFFORT_SECRET"},
                    {"FAKE_AUTH": json.dumps({"loggedIn": False})},
                    {"FAKE_AUTH": json.dumps({"authMethod": "api_key"})}):
            with self.subTest(env=list(env)):
                result = self.consult(extra_env=env)
                data = self.parsed(result, 3)
                self.assertEqual(data["status"], "blocked")
                self.assertFalse(self.capture.exists())
                self.assertNotIn("PRIVATE_ROUTE_SECRET", result.stdout + result.stderr)
                self.assertNotIn("PRIVATE_EFFORT_SECRET", result.stdout + result.stderr)

    def test_consult_preserves_credit_disabled_lock_and_explicit_effort_guards(self):
        config = json.loads(self.config.read_text())
        config["subscription_usage_credits_disabled"] = False
        self.config.write_text(json.dumps(config))
        blocked = self.parsed(self.consult(), 3)
        self.assertEqual(blocked["status"], "blocked")
        self.assertFalse(self.capture.exists())
        config["subscription_usage_credits_disabled"] = True
        self.config.write_text(json.dumps(config))
        with (self.project / ".ai" / "bridge.lock").open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            blocked = self.parsed(self.consult(), 3)
            self.assertEqual(blocked["reason"], "project_already_locked")
            self.assertFalse(self.capture.exists())
        for flag, value in (("--effort-source", "auto"), ("--effort", "max")):
            with self.subTest(flag=flag):
                args = (flag, value) if flag == "--effort-source" else (flag, value, "--effort-source", "auto")
                blocked = self.parsed(self.consult("bounded request", *args), 3)
                self.assertEqual(blocked["status"], "blocked")
                self.assertFalse(self.capture.exists())
        chosen = self.parsed(self.consult("bounded request", "--effort", "high", "--effort-source", "user"))
        self.assertEqual(chosen["requested_effort"], "high")
        self.assertEqual(chosen["effort_source"], "user")
        self.assertEqual(chosen["effective_effort"], "unknown")
        args = self.captured()["args"]
        self.assertEqual(args[args.index("--effort") + 1], "high")

    def test_consult_post_inference_evidence_or_cache_failure_is_not_safe_to_retry(self):
        module = self.bridge_module()
        original_write = module.atomic_write
        args = module.parser().parse_args(["--runtime", str(self.config), "run",
            "--project", str(self.project), "--workflow", "consult", "--task", "PRIVATE_PERSISTENCE_TASK"])
        for target in ("consult.json", "HANDOFF.md"):
            with self.subTest(target=target):
                if self.capture.exists():
                    self.capture.unlink()
                sessions = (self.project / ".ai" / "sessions.json").read_bytes()

                def failing_write(path, data, mode=0o600):
                    # The request Handoff write happens before inference; fail only
                    # the evidence/cache write after the subprocess consumed usage.
                    if path.name == target and self.capture.exists():
                        raise OSError("PRIVATE_FILESYSTEM_FAILURE_DETAIL")
                    return original_write(path, data, mode)

                with mock.patch.dict(module.os.environ, self.env, clear=True), \
                     mock.patch.object(module, "atomic_write", side_effect=failing_write):
                    outcome, code = module.execute(self.project.resolve(), self.config, args)
                self.assertEqual(code, 4)
                self.assertEqual(outcome["status"], "state_update_failed")
                self.assertEqual(outcome["inference_status"], "complete")
                self.assertTrue(outcome["inference"])
                self.assertTrue(self.capture.exists())
                self.assertFalse(outcome["consult_cache_saved"])
                self.assertFalse(self.cache_path().exists())
                self.assertNotIn("PRIVATE_FILESYSTEM_FAILURE_DETAIL", json.dumps(outcome))
                if target == "consult.json":
                    self.assertTrue(outcome["state_updated"])
                    self.assertTrue(outcome["session_saved"])
                else:
                    self.assertFalse(outcome["state_updated"])
                    self.assertFalse(outcome["session_saved"])
                    self.assertEqual((self.project / ".ai" / "sessions.json").read_bytes(), sessions)
                self.assertEqual(self.parsed(self.consult("fresh context after failed persistence"))["context_delivery"], "full")

    def test_late_timing_log_failure_reports_authoritative_saved_session(self):
        module = self.bridge_module()
        original_write = module.atomic_write
        args = module.parser().parse_args(["--runtime", str(self.config), "run",
            "--project", str(self.project), "--workflow", "consult", "--task", "timing-log regression"])
        new_session = "22222222-2222-4222-8222-222222222222"
        env = dict(self.env, FAKE_SESSION=new_session)
        log_writes = []

        def fail_second_log(path, data, mode=0o600):
            if path.parent.name == "logs":
                log_writes.append(path)
                if len(log_writes) == 2:
                    raise OSError("PRIVATE_LATE_LOG_FAILURE_DETAIL")
            return original_write(path, data, mode)

        with mock.patch.dict(module.os.environ, env, clear=True), \
             mock.patch.object(module, "atomic_write", side_effect=fail_second_log):
            outcome, code = module.execute(self.project.resolve(), self.config, args)
        self.assertEqual(len(log_writes), 2)
        self.assertEqual(code, 4)
        self.assertEqual(outcome["status"], "state_update_failed")
        self.assertEqual(outcome["inference_status"], "complete")
        self.assertTrue(outcome["inference"])
        self.assertTrue(outcome["session_saved"])
        self.assertFalse(outcome["state_updated"])
        self.assertFalse(outcome["consult_cache_saved"])
        self.assertFalse(self.cache_path().exists())
        sessions = json.loads((self.project / ".ai" / "sessions.json").read_text())
        self.assertEqual(sessions["claude"]["session_id"], new_session)
        self.assertNotIn("PRIVATE_LATE_LOG_FAILURE_DETAIL", json.dumps(outcome))
        refreshed = self.parsed(self.consult("complete context after late persistence failure"))
        self.assertEqual(refreshed["context_delivery"], "full")
        self.assertEqual(refreshed["resumed_session"], new_session)

    def test_timings_progress_and_logs_are_metadata_without_task_or_prompt_text(self):
        self.add_stable_context()
        result = self.consult("PRIVATE_TIMING_TASK", "--progress")
        data = self.parsed(result)
        timings = data["timings"]
        for key in ("preflight_finished_at", "cli_spawned_at", "cli_finished_at"):
            self.assertIsInstance(timings[key], str)
            self.assertTrue(timings[key])
        for key in ("preflight_wall_ms", "cli_wall_ms", "total_through_record_ms"):
            self.assertIsInstance(timings[key], (int, float))
            self.assertGreaterEqual(timings[key], 0)
        self.assertGreaterEqual(timings["total_through_record_ms"], timings["cli_wall_ms"])
        self.assertGreaterEqual(timings["total_through_record_ms"], timings["preflight_wall_ms"])
        official = timings["official_cli"]
        self.assertEqual(official["provenance"], "official_cli_result")
        self.assertIsInstance(official["duration_ms"], (int, float))
        self.assertIsInstance(official["duration_api_ms"], (int, float))
        self.assertTrue(result.stderr.strip(), "long-running inference needs a bounded progress marker")
        for marker in ("PRIVATE_TIMING_TASK", "PRIVATE_PROJECT_CONTEXT_MARKER",
                       "PRIVATE_DECISION_MARKER", "PRIVATE_INSTRUCTION_MARKER"):
            self.assertNotIn(marker, result.stdout + result.stderr)
        log = json.loads(next((self.project / ".ai" / "logs").glob("*.json")).read_text())
        self.assertEqual(log["workflow"], "consult")
        self.assertEqual(log["context_delivery"], "full")
        self.assertEqual(log["prompt_bytes"], data["prompt_bytes"])
        self.assertIn("timings", log)
        for marker in ("PRIVATE_TIMING_TASK", "PRIVATE_PROJECT_CONTEXT_MARKER",
                       "PRIVATE_DECISION_MARKER", "PRIVATE_INSTRUCTION_MARKER"):
            self.assertNotIn(marker, json.dumps(log))

    def test_consult_dry_run_reports_delivery_without_inference_or_state_writes(self):
        self.add_stable_context()
        first = self.parsed(self.consult("PRIVATE_DRY_TASK", "--dry-run",
                        extra_env={"FAKE_AUTH": json.dumps({"loggedIn": False})}))
        self.assertEqual(first["status"], "dry_run")
        self.assertEqual(first["workflow"], "consult")
        self.assertEqual(first["context_delivery"], "full")
        self.assertFalse(first["inference"])
        self.assertFalse(first["prompt_sent"])
        self.assertFalse(self.capture.exists())
        self.assertFalse(self.cache_path().exists())
        self.parsed(self.consult("successful continuation"))
        self.capture.unlink()
        before = self.private_files()
        resumed = self.parsed(self.consult("PRIVATE_DRY_TASK", "--dry-run"))
        self.assertEqual(resumed["context_delivery"], "delta")
        self.assertEqual(before, self.private_files())
        self.assertFalse(self.capture.exists())
        self.assertNotIn("PRIVATE_DRY_TASK", json.dumps(resumed))
        # Previewing standard work cannot invalidate the real consult baseline.
        self.parsed(self.invoke("run", "--task", "standard preview", "--dry-run"))
        self.assertEqual(before, self.private_files())
        self.assertEqual(self.parsed(self.consult("continued"))["context_delivery"], "delta")


if __name__ == "__main__":
    unittest.main()
