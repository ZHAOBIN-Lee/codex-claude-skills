"""Behavioral, offline tests. Claude inference is replaced at process boundary."""
import fcntl
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

BASE = Path(__file__).resolve().parents[1]
BRIDGE = BASE / "lib" / "bridge.py"
FAKE = BASE / "tests" / "fake_claude.py"


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.fake = self.root / "claude"
        self.fake.write_bytes(FAKE.read_bytes())
        self.fake.chmod(0o700)
        self.config = self.root / "runtime.json"
        self.config.write_text(json.dumps({"claude_path": str(self.fake),
            "subscription_usage_credits_disabled": True}))
        self.capture = self.root / "capture.json"
        # Deliberately inherit no real credentials or real user's configuration.
        self.env = {"HOME": str(self.home), "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "FAKE_CAPTURE": str(self.capture), "TEST_POLICY": "preserve-this-policy",
                    "PYTHONUTF8": "1"}
        self.git("init", "-q")
        self.git("config", "user.email", "offline@example.invalid")
        self.git("config", "user.name", "Offline Test")
        (self.project / "shared.txt").write_text("GPT baseline\n")
        self.git("add", "shared.txt")
        self.git("commit", "-qm", "baseline")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=str(self.project), env=self.env,
                              check=True, text=True, capture_output=True).stdout

    def invoke(self, command, *args, extra_env=None):
        env = dict(self.env)
        env.update(extra_env or {})
        return subprocess.run([sys.executable, str(BRIDGE), "--runtime", str(self.config),
                               command, "--project", str(self.project), *args],
                              env=env, text=True, capture_output=True, timeout=20)

    def parsed(self, result, code=0):
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def initialize(self):
        self.parsed(self.invoke("init"))

    def bridge_module(self):
        spec = importlib.util.spec_from_file_location("bridge_redaction_fixture", BRIDGE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_init_preserves_existing_context_and_ignores_private_state(self):
        # Overwriting existing context or failing to ignore session/log state is a bug.
        self.initialize()
        ai = self.project / ".ai"
        handoff = ai / "HANDOFF.md"
        handoff.write_text("Existing decisions and history.\n")
        self.initialize()
        self.assertEqual(handoff.read_text(), "Existing decisions and history.\n")
        self.assertTrue((ai / "PROJECT_CONTEXT.md").exists())
        self.assertTrue((ai / "DECISIONS.md").exists())
        self.assertEqual(self.git("check-ignore", ".ai/sessions.json").strip(), ".ai/sessions.json")
        self.assertEqual(stat.S_IMODE((ai / "sessions.json").stat().st_mode), 0o600)

    def test_doctor_only_reports_whitelisted_auth_and_does_not_write_project(self):
        # Inference, project writes, or private auth fields in doctor violate read-only contract.
        before = list(self.project.iterdir())
        result = self.invoke("doctor")
        data = self.parsed(result)
        self.assertEqual(data["auth"], {"loggedIn": True, "authMethod": "claude.ai", "subscriptionType": "pro"})
        self.assertFalse(self.capture.exists())
        self.assertEqual(before, list(self.project.iterdir()))
        self.assertNotIn("private@example.com", result.stdout + result.stderr)
        self.assertNotIn("MUST-NOT-LEAK", result.stdout + result.stderr)

    def test_doctor_handles_official_logged_out_status_exit_one(self):
        # The real auth-status command emits valid logged-out JSON with exit 1.
        data = self.parsed(self.invoke("doctor", extra_env={"FAKE_AUTH_EXIT": "1",
            "FAKE_AUTH": json.dumps({"loggedIn": False, "authMethod": "none", "subscriptionType": None})}))
        self.assertFalse(data["subscription_auth_eligible"])
        self.assertFalse(self.capture.exists())

    def test_run_uses_stdin_shared_workspace_and_protects_normal_permissions(self):
        # Wrong cwd, shell prompt arguments, or permission bypass are bridge boundary bugs.
        self.initialize()
        (self.project / "shared.txt").write_text("GPT current modification\n")
        task = "Literal task $(touch SHOULD_NOT_EXIST) `touch ALSO_NOT`"
        data = self.parsed(self.invoke("run", "--mode", "sonnet", "--task", task,
                                       extra_env={"FAKE_ACTION": "write"}))
        capture = json.loads(self.capture.read_text())
        self.assertEqual(data["status"], "complete")
        self.assertEqual(data["claude_exit_code"], 0)
        self.assertEqual(capture["cwd"], str(self.project.resolve()))
        self.assertIn(task, capture["stdin"])
        self.assertIn("GPT current modification", capture["stdin"])
        self.assertNotIn(task, capture["args"])
        self.assertEqual(capture["policy"], "preserve-this-policy")
        self.assertEqual(capture["autoupdate"], "1")
        self.assertEqual(capture["updates"], "1")
        self.assertIn("sonnet", capture["args"])
        for unsafe in ("--dangerously-skip-permissions", "--allowedTools", "--bare"):
            self.assertNotIn(unsafe, capture["args"])
        self.assertEqual(capture["args"][capture["args"].index("--permission-mode") + 1], "manual")
        self.assertEqual(capture["args"][capture["args"].index("--permission-prompts") + 1], "none")
        self.assertFalse((self.project / "SHOULD_NOT_EXIST").exists())
        self.assertTrue((self.project / "claude-output.txt").exists())
        self.assertIn("Model-reported tests; not independently verified", (self.project / ".ai/HANDOFF.md").read_text())

    def test_session_resumes_and_explicit_new_session_omits_resume(self):
        # Lost or cross-project session IDs break the persistence contract.
        self.initialize()
        self.parsed(self.invoke("run", "--task", "first"))
        state = json.loads((self.project / ".ai/sessions.json").read_text())
        self.assertEqual(state["project"], str(self.project.resolve()))
        self.assertEqual(state["claude"]["session_id"], "11111111-1111-4111-8111-111111111111")
        self.parsed(self.invoke("run", "--task", "second"))
        args = json.loads(self.capture.read_text())["args"]
        self.assertEqual(args[args.index("--resume") + 1], "11111111-1111-4111-8111-111111111111")
        self.parsed(self.invoke("run", "--task", "third", "--new-session"))
        self.assertNotIn("--resume", json.loads(self.capture.read_text())["args"])

    def test_dry_run_is_read_only_without_inference_or_auth_requirement(self):
        # A dry run consuming usage or modifying project files is a bug.
        self.initialize()
        before = {str(p.relative_to(self.project)): p.read_bytes() for p in (self.project / ".ai").rglob("*") if p.is_file()}
        data = self.parsed(self.invoke("run", "--mode", "opus", "--task", "never send this", "--dry-run"))
        self.assertEqual(data["status"], "dry_run")
        self.assertFalse(self.capture.exists())
        after = {str(p.relative_to(self.project)): p.read_bytes() for p in (self.project / ".ai").rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertNotIn("never send this", json.dumps(data))

    def test_default_dry_run_describes_native_selection_and_resumed_model_uncertainty(self):
        # Omitting --model does not establish the account default, especially on resume.
        self.initialize()
        fresh = self.parsed(self.invoke("run", "--task", "preview", "--dry-run"))
        self.assertEqual(fresh["model"], "Claude Code native model selection")
        self.assertIsNone(fresh["resume_session"])
        state_path = self.project / ".ai/sessions.json"
        state = json.loads(state_path.read_text())
        state["claude"]["session_id"] = "11111111-1111-4111-8111-111111111111"
        state_path.write_text(json.dumps(state))
        resumed = self.parsed(self.invoke("run", "--task", "preview", "--dry-run"))
        self.assertEqual(resumed["model"], "Claude Code native model selection; resumed session may retain its prior model")
        self.assertEqual(resumed["resume_session"], state["claude"]["session_id"])
        explicit = self.parsed(self.invoke("run", "--mode", "opus", "--task", "preview", "--dry-run"))
        self.assertEqual(explicit["model"], "opus")
        new = self.parsed(self.invoke("run", "--new-session", "--task", "preview", "--dry-run"))
        self.assertEqual(new["model"], fresh["model"])
        self.assertIsNone(new["resume_session"])
        self.assertFalse(self.capture.exists())

    def test_git_snapshot_redacts_complete_values_before_prefix_bounds(self):
        # Cropping a quoted value before redaction exposes its visible prefix.
        module = self.bridge_module()
        status = ("S" * 15970 + '{"password":"DUMMY_STATUS_SECRET_' + "X" * 300 + '"}').encode()
        diff = ("D" * 23970 + '{"access_token":"DUMMY_DIFF_SECRET_' + "Y" * 300 + '"}').encode()

        def fake_git(command, **kwargs):
            if "rev-parse" in command:
                return subprocess.CompletedProcess(command, 0, b"a" * 40 + b"\n", b"")
            raw = status if "status" in command else diff
            return subprocess.CompletedProcess(command, 0, raw, b"")

        with mock.patch.object(module.subprocess, "run", side_effect=fake_git):
            snapshot = module.git_snapshot(self.project)
        self.assertFalse("DUMMY_STATUS" in snapshot["status"], "quoted status secret prefix leaked")
        self.assertFalse("DUMMY_DIFF" in snapshot["diff"], "quoted diff secret prefix leaked")
        self.assertFalse("X" * 100 in snapshot["status"], "status secret fragment leaked")
        self.assertFalse("Y" * 100 in snapshot["diff"], "diff secret fragment leaked")
        self.assertLessEqual(len(snapshot["status"]), 16000)
        self.assertLessEqual(len(snapshot["diff"]), 24000)
        self.assertTrue(snapshot["status_truncated"])
        self.assertTrue(snapshot["diff_truncated"])
        self.assertEqual(snapshot["status_sha256"], hashlib.sha256(status).hexdigest())
        self.assertEqual(snapshot["diff_sha256"], hashlib.sha256(diff).hexdigest())

    def test_context_prefix_and_recent_tails_redact_before_slicing(self):
        # Context bounds must not cut away a secret key or discard the newest handoff evidence.
        self.initialize()
        ai = self.project / ".ai"
        (ai / "PROJECT_CONTEXT.md").write_text("C" * 11970 + '{"password":"DUMMY_CONTEXT_SECRET_' + "X" * 300 + '"}')
        for name, dummy in (("DECISIONS.md", "DUMMY_DECISION_SECRET_"),
                            ("HANDOFF.md", "DUMMY_HANDOFF_SECRET_")):
            (ai / name).write_text("P" * 2000 + '{"token":"' + dummy * 100 + '"}\n' +
                                   "R" * 10900 + "\nRECENT_" + name + "_PROOF")
        module = self.bridge_module()
        prompt = module.make_prompt(self.project, "safe task", "default", {"status": "safe", "diff": "safe"})
        for dummy in ("DUMMY_CONTEXT", "DUMMY_DECISION", "DUMMY_HANDOFF"):
            self.assertFalse(dummy in prompt, "quoted context secret fragment leaked: " + dummy)
        self.assertIn("RECENT_DECISIONS.md_PROOF", prompt)
        self.assertIn("RECENT_HANDOFF.md_PROOF", prompt)
        self.assertIn("HANDOFF.md (bounded recent tail)", prompt)

    def test_unterminated_quoted_secret_values_are_redacted_without_losing_closed_public_fields(self):
        # A malformed source ending mid-value still must not emit its credential prefix.
        module = self.bridge_module()
        for quote in ('"', "'"):
            for ending in ("", "\\"):
                with self.subTest(quote=quote, ending=ending):
                    value = "{" + quote + "password" + quote + ":" + quote + "DUMMY_UNTERMINATED_SECRET" + ending
                    self.assertNotIn("DUMMY_UNTERMINATED", module.scrub(value))
        mixed = '{"password":"DUMMY_CLOSED_SECRET","public":"KEEP_PUBLIC_VALUE"}'
        scrubbed = module.scrub(mixed)
        self.assertNotIn("DUMMY_CLOSED", scrubbed)
        self.assertIn("KEEP_PUBLIC_VALUE", scrubbed)

    def test_unverified_hidden_flag_blocks_until_offline_runtime_verification(self):
        # Hidden flags require concrete parsing evidence recorded by the installer.
        self.initialize()
        env = {"FAKE_HIDE_FLAG": "--max-turns"}
        data = self.parsed(self.invoke("run", "--task", "guard", extra_env=env), 3)
        self.assertEqual(data["unsupported_flags"], ["--max-turns"])
        self.assertFalse(self.capture.exists())
        config = json.loads(self.config.read_text())
        config["verified_cli_flags"] = ["--max-turns"]
        self.config.write_text(json.dumps(config))
        self.parsed(self.invoke("run", "--task", "now explicitly verified", extra_env=env))

    def test_mode_dispatch_and_long_task_are_not_silently_changed(self):
        # Routing the default model to a named model or dropping the task tail is wrong.
        self.initialize()
        for mode, model in (("default", None), ("sonnet", "sonnet"), ("opus", "opus"), ("review", "sonnet")):
            task = "a" * 12000 + " USER_TASK_TAIL"
            self.parsed(self.invoke("run", "--mode", mode, "--task", task))
            capture = json.loads(self.capture.read_text())
            self.assertIn("USER_TASK_TAIL", capture["stdin"])
            if model:
                self.assertEqual(capture["args"][capture["args"].index("--model") + 1], model)
            else:
                self.assertNotIn("--model", capture["args"])

    def test_subscription_guard_rejects_api_unknown_or_logged_out_auth(self):
        # Accepting Console, unknown plans, or logged-out status risks the wrong usage source.
        self.initialize()
        for fields in ({"authMethod": "api_key"}, {"authMethod": "console"},
                       {"subscriptionType": "team"}, {"loggedIn": False}):
            with self.subTest(fields=fields):
                data = self.parsed(self.invoke("run", "--task", "do not send",
                    extra_env={"FAKE_AUTH": json.dumps(fields)}), 3)
                self.assertEqual(data["status"], "blocked")
                self.assertFalse(self.capture.exists())

    def test_usage_credit_confirmation_required_before_inference(self):
        # Native account authentication alone does not prove extra usage is disabled.
        self.initialize()
        for confirmation in (None, False, "true"):
            self.config.write_text(json.dumps({"claude_path": str(self.fake),
                "subscription_usage_credits_disabled": confirmation}))
            data = self.parsed(self.invoke("run", "--task", "do not bill"), 3)
            self.assertEqual(data["status"], "blocked")
            self.assertFalse(self.capture.exists())
        self.parsed(self.invoke("doctor"))

    def test_route_environment_is_rejected_without_value_leak(self):
        # Any API/upstream route override must stop before calling even auth commands.
        self.initialize()
        for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                     "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "OPENAI_API_KEY"):
            with self.subTest(name=name):
                result = self.invoke("run", "--task", "do not send", extra_env={name: "secret-value-should-not-print"})
                data = self.parsed(result, 3)
                self.assertEqual(data["status"], "blocked")
                self.assertIn(name, json.dumps(data))
                self.assertNotIn("secret-value-should-not-print", result.stdout + result.stderr)
                self.assertFalse(self.capture.exists())

    def test_custom_upstream_settings_block_without_exposing_contents(self):
        # API helpers and route env in applicable settings must not evade env guards.
        self.initialize()
        for base, settings in ((self.home, {"apiKeyHelper": "echo sensitive-key"}),
                               (self.project, {"env": {"ANTHROPIC_BASE_URL": "https://secret-upstream.invalid"}})):
            directory = base / ".claude"
            directory.mkdir(exist_ok=True)
            path = directory / "settings.json"
            path.write_text(json.dumps(settings))
            result = self.invoke("run", "--task", "blocked")
            data = self.parsed(result, 3)
            self.assertEqual(data["status"], "blocked")
            self.assertNotIn("sensitive-key", result.stdout + result.stderr)
            self.assertNotIn("secret-upstream", result.stdout + result.stderr)
            self.assertFalse(self.capture.exists())
            path.unlink()

    def test_permission_denial_does_not_promote_model_claims_or_replace_session(self):
        # A denied task cannot be recorded complete or displace the resumable prior session.
        self.initialize()
        self.parsed(self.invoke("run", "--task", "first"))
        prior = (self.project / ".ai/sessions.json").read_bytes()
        data = self.parsed(self.invoke("run", "--task", "needs permission",
                  extra_env={"FAKE_ACTION": "permission", "FAKE_SESSION": "22222222-2222-4222-8222-222222222222"}), 4)
        self.assertEqual(data["status"], "needs_permission")
        self.assertEqual(data["claude_exit_code"], 0)
        self.assertEqual(data["permission_denials"], ["Bash"])
        self.assertEqual(prior, (self.project / ".ai/sessions.json").read_bytes())
        self.assertNotIn("secret private command", json.dumps(data))

    def test_nonzero_exit_keeps_available_permission_denial_metadata(self):
        # A nonzero CLI exit still has useful denial metadata, never raw tool inputs.
        self.initialize()
        data = self.parsed(self.invoke("run", "--task", "deny", extra_env={"FAKE_ACTION": "permission_nonzero"}), 4)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["claude_exit_code"], 9)
        self.assertEqual(data["permission_denials"], ["Bash"])
        self.assertNotIn("secret private command", json.dumps(data))

    def test_nonzero_malformed_and_error_outputs_fail_without_retry_or_raw_leak(self):
        # Exit status/invalid JSON/model errors must dominate text that claims success.
        self.initialize()
        self.parsed(self.invoke("run", "--task", "first"))
        prior = (self.project / ".ai/sessions.json").read_bytes()
        for action, expected_exit in (("nonzero", 9), ("malformed", 0), ("error", 0)):
            with self.subTest(action=action):
                data = self.parsed(self.invoke("run", "--task", "failing task",
                    extra_env={"FAKE_ACTION": action}), 4)
                self.assertEqual(data["status"], "failed")
                self.assertEqual(data["claude_exit_code"], expected_exit)
                self.assertNotIn("MUST-NOT-LEAK", json.dumps(data))
                self.assertEqual(prior, (self.project / ".ai/sessions.json").read_bytes())

    def test_timeout_preserves_session_and_reports_unknown_completion(self):
        # A timeout leaves completion unknown and cannot mark PASS or rotate session.
        self.initialize()
        prior = (self.project / ".ai/sessions.json").read_bytes()
        data = self.parsed(self.invoke("run", "--task", "sleep", "--timeout", "0.2",
                           extra_env={"FAKE_ACTION": "timeout"}), 4)
        self.assertEqual(data["status"], "timeout")
        self.assertEqual(prior, (self.project / ".ai/sessions.json").read_bytes())
        self.assertIn("unknown", (self.project / ".ai/HANDOFF.md").read_text().lower())

    def test_invalid_or_cross_project_session_blocks_until_explicit_new_session(self):
        # Silently sending invalid resume IDs or fresh retry calls is unsafe.
        self.initialize()
        path = self.project / ".ai/sessions.json"
        for session in ({"project": "/elsewhere", "claude": {"session_id": "11111111-1111-4111-8111-111111111111"}},
                        {"project": str(self.project), "claude": {"session_id": "not-a-uuid"}}):
            path.write_text(json.dumps(session))
            data = self.parsed(self.invoke("run", "--task", "do not retry"), 3)
            self.assertEqual(data["status"], "blocked")
            self.assertFalse(self.capture.exists())
        self.parsed(self.invoke("run", "--task", "explicit fresh", "--new-session"))
        self.assertNotIn("--resume", json.loads(self.capture.read_text())["args"])

    def test_symlink_session_and_ai_dir_are_never_followed(self):
        # Following state symlinks can overwrite or disclose files outside project.
        self.initialize()
        state = self.project / ".ai/sessions.json"
        outside = self.root / "outside.json"
        outside.write_text("outside original")
        state.unlink()
        state.symlink_to(outside)
        data = self.parsed(self.invoke("run", "--task", "blocked"), 3)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(outside.read_text(), "outside original")
        self.assertFalse(self.capture.exists())

    def test_symlink_ai_directory_blocks_init_without_external_write(self):
        # Init cannot materialize context outside the selected project via .ai symlink.
        outside = self.root / "outside-dir"
        outside.mkdir()
        (self.project / ".ai").symlink_to(outside)
        data = self.parsed(self.invoke("init"), 3)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(list(outside.iterdir()), [])

    def test_post_inference_state_failure_is_reported_as_inference_not_safe_to_retry(self):
        # Persist failure after model usage cannot claim no inference or suggest a free retry.
        self.initialize()
        outside = self.root / "outside.txt"
        outside.write_text("do not touch")
        prior = (self.project / ".ai/sessions.json").read_bytes()
        data = self.parsed(self.invoke("run", "--task", "corrupt state", extra_env={
            "FAKE_ACTION": "corrupt_state", "FAKE_OUTSIDE": str(outside)}), 4)
        self.assertEqual(data["status"], "state_update_failed")
        self.assertTrue(data["inference"])
        self.assertEqual(data["claude_exit_code"], 0)
        self.assertEqual(prior, (self.project / ".ai/sessions.json").read_bytes())
        self.assertEqual(outside.read_text(), "do not touch")

    def test_lock_prevents_concurrent_inference(self):
        # A second writer must fail before inference instead of racing session/Handoff writes.
        self.initialize()
        with (self.project / ".ai/bridge.lock").open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            data = self.parsed(self.invoke("run", "--task", "second writer"), 3)
            self.assertEqual(data["status"], "blocked")
            self.assertFalse(self.capture.exists())

    def test_metadata_logs_and_handoff_redact_secret_shaped_model_output(self):
        # Logging prompts/raw auth/raw response or accepting unknown structured fields leaks data.
        self.initialize()
        result = self.invoke("run", "--task", "do-not-log-private-user-task", extra_env={"FAKE_ACTION": "leak"})
        data = self.parsed(result)
        self.assertNotIn("MUST-NOT-LEAK", result.stdout + result.stderr)
        self.assertNotIn("sensitive-token-value", result.stdout + result.stderr)
        for path in (self.project / ".ai/logs").iterdir():
            contents = path.read_text()
            self.assertNotIn("do-not-log-private-user-task", contents)
            self.assertNotIn("structured_output", contents)
            self.assertNotIn("private@example.com", contents)
        self.assertNotIn("MUST-NOT-LEAK", (self.project / ".ai/HANDOFF.md").read_text())
        self.assertNotIn("apiKey", json.dumps(data))

    def test_json_quoted_secret_values_are_redacted_without_swallowing_other_fields(self):
        # Quoted JSON keys must not bypass string hygiene or consume adjacent public data.
        self.initialize()
        result = self.invoke("run", "--task", "safe", extra_env={"FAKE_ACTION": "json_leak"})
        self.parsed(result)
        handoff = (self.project / ".ai/HANDOFF.md").read_text()
        for secret in ("DUMMY_JSON_PASSWORD", "DUMMY_JSON_API_KEY", "DUMMY_COOKIE"):
            self.assertNotIn(secret, result.stdout + result.stderr)
            self.assertNotIn(secret, handoff)
        self.assertIn("KEEP_PUBLIC_VALUE", result.stdout)
        self.assertIn("KEEP_PUBLIC_VALUE", handoff)

    def test_actual_model_evidence_only_returns_safe_names_not_cost_or_token_usage(self):
        # A requested model alias cannot stand in for the model actually reported by CLI.
        self.initialize()
        data = self.parsed(self.invoke("run", "--mode", "opus", "--task", "fixture"))
        self.assertEqual(data.get("actual_models"), ["claude-sonnet-4-6"])
        self.assertNotIn("malicious-private-value", json.dumps(data))
        self.assertNotIn("costUSD", json.dumps(data))
        self.assertNotIn("inputTokens", json.dumps(data))

    def test_handoff_append_keeps_original_and_records_git_evidence(self):
        # Replacing old handoff loses human decisions; missing Git evidence misstates work.
        self.initialize()
        path = self.project / ".ai/HANDOFF.md"
        path.write_text("Original human status\n")
        self.parsed(self.invoke("run", "--task", "work", extra_env={"FAKE_ACTION": "write"}))
        contents = path.read_text()
        self.assertTrue(contents.startswith("Original human status\n"))
        self.assertIn("<!-- claude-bridge:", contents)
        self.assertIn("Git before", contents)
        self.assertIn("Git after", contents)
        self.assertTrue(list((self.project / ".ai/backups").glob("HANDOFF.*.bak")))

    def test_extended_authentication_routes_and_model_aliases_are_refused(self):
        # Federated/profile credentials and alias override routes can outrank native login.
        self.initialize()
        names = ("ANTHROPIC_PROFILE", "ANTHROPIC_CONFIG_DIR", "ANTHROPIC_FEDERATION_RULE_ID",
                 "ANTHROPIC_ORGANIZATION_ID", "ANTHROPIC_WORKSPACE_ID", "ANTHROPIC_IDENTITY_TOKEN",
                 "ANTHROPIC_AWS_API_KEY", "ANTHROPIC_AWS_BASE_URL", "ANTHROPIC_FOUNDRY_AUTH_TOKEN",
                 "ANTHROPIC_AUTH_CUSTOM_HEADERS", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL",
                 "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
                 "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_FABLE_MODEL")
        for name in names:
            with self.subTest(name=name):
                result = self.invoke("run", "--task", "guard", extra_env={name: "PRIVATE_ROUTE_VALUE"})
                data = self.parsed(result, 3)
                self.assertEqual(data["reason"], "api_or_override_environment_refused")
                self.assertNotIn("PRIVATE_ROUTE_VALUE", result.stdout + result.stderr)
                self.assertFalse(self.capture.exists())

    def test_ancestor_project_settings_route_is_not_missed(self):
        # Settings inherited from parent directories apply even when project has none.
        self.initialize()
        directory = self.root / ".claude"
        directory.mkdir()
        (directory / "settings.json").write_text(json.dumps({"env": {"ANTHROPIC_PROFILE": "PRIVATE_PROFILE"}}))
        data = self.parsed(self.invoke("run", "--task", "guard"), 3)
        self.assertEqual(data["reason"], "custom_auth_or_upstream_settings_refused")
        self.assertNotIn("PRIVATE_PROFILE", json.dumps(data))
        self.assertFalse(self.capture.exists())

    def test_pinned_cli_integrity_and_version_mismatch_fail_closed(self):
        # The official executable pinned by the installer must not silently drift.
        self.initialize()
        config = json.loads(self.config.read_text())
        config["claude_sha256"] = "0" * 64
        self.config.write_text(json.dumps(config))
        data = self.parsed(self.invoke("run", "--task", "guard"), 3)
        self.assertEqual(data["reason"], "claude_executable_integrity_mismatch")
        self.assertFalse(self.capture.exists())
        config.pop("claude_sha256")
        config["claude_version"] = "9.9.9"
        self.config.write_text(json.dumps(config))
        data = self.parsed(self.invoke("run", "--task", "guard"), 3)
        self.assertEqual(data["reason"], "claude_version_mismatch")
        self.assertFalse(self.capture.exists())

    def test_implicit_anthropic_profile_presence_requires_review_without_secret_read(self):
        # Active/default profile files can select credentials above /login without env vars.
        self.initialize()
        config = self.home / ".config" / "anthropic"
        config.mkdir(parents=True)
        (config / "active_config").write_text("PRIVATE_PROFILE_NAME")
        data = self.parsed(self.invoke("run", "--task", "guard"), 3)
        self.assertEqual(data["reason"], "anthropic_profile_presence_requires_review")
        self.assertNotIn("PRIVATE_PROFILE_NAME", json.dumps(data))
        self.assertFalse(self.capture.exists())

    def test_handoff_preserves_independent_drift_during_cli_run(self):
        # The bridge must append to the newest Handoff, not replace the prompt's old copy.
        self.initialize()
        self.parsed(self.invoke("run", "--task", "drift", extra_env={"FAKE_ACTION": "handoff_drift"}))
        self.assertIn("New independent change during CLI run.", (self.project / ".ai/HANDOFF.md").read_text())

    def test_unborn_head_diff_includes_staged_and_worktree_evidence(self):
        # New repositories have no HEAD; staged additions must still reach Claude.
        self.project = self.root / "unborn-project"
        self.project.mkdir()
        self.git("init", "-q")
        (self.project / "staged-only.txt").write_text("STAGED_ONLY_PROOF\n")
        (self.project / "both.txt").write_text("STAGED_DUAL_PROOF\n")
        self.git("add", "staged-only.txt", "both.txt")
        (self.project / "both.txt").write_text("STAGED_DUAL_PROOF\nUNSTAGED_DUAL_PROOF\n")
        self.initialize()
        data = self.parsed(self.invoke("run", "--task", "inspect a new repository"))
        prompt = json.loads(self.capture.read_text())["stdin"]
        self.assertIn("STAGED_ONLY_PROOF", prompt)
        self.assertIn("STAGED_DUAL_PROOF", prompt)
        self.assertIn("UNSTAGED_DUAL_PROOF", prompt)
        self.assertIn("Staged diff (unborn HEAD)", prompt)
        self.assertIn("Worktree diff (unborn HEAD)", prompt)
        self.assertEqual(data["git_before"]["head"], "unknown")
        self.assertNotEqual(data["git_before"]["diff_sha256"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_direct_cli_default_explicitly_passes_medium_and_audits_requested_only(self):
        # Omitted effort must not inherit a prior session's high setting or imply semantic choice.
        self.initialize()
        data = self.parsed(self.invoke("run", "--task", "complex architecture max reasoning keywords"))
        args = json.loads(self.capture.read_text())["args"]
        self.assertIn("--effort", args)
        self.assertEqual(args[args.index("--effort") + 1], "medium")
        self.assertEqual(data.get("requested_effort"), "medium")
        self.assertEqual(data.get("effort_source"), "direct_default")
        self.assertEqual(data.get("effective_effort"), "unknown")
        self.assertNotIn("actual_effort", data)
        log = json.loads(next((self.project / ".ai/logs").glob("*.json")).read_text())
        self.assertEqual(log.get("requested_effort"), "medium")
        self.assertEqual(log.get("effort_source"), "direct_default")
        self.assertEqual(log.get("effective_effort"), "unknown")
        handoff = (self.project / ".ai/HANDOFF.md").read_text()
        self.assertIn("Requested effort: medium", handoff)
        self.assertIn("Effective effort: unknown", handoff)

    def test_explicit_user_effort_is_preserved_for_every_supported_level_and_resume(self):
        # Explicit user levels must win over defaults/keywords and survive resume launches.
        self.initialize()
        for level in ("low", "medium", "high", "xhigh", "max"):
            with self.subTest(level=level):
                data = self.parsed(self.invoke("run", "--effort", level, "--task", "hard architecture review"))
                args = json.loads(self.capture.read_text())["args"]
                self.assertEqual(args[args.index("--effort") + 1], level)
                self.assertEqual(data.get("requested_effort"), level)
                self.assertEqual(data.get("effort_source"), "user")
                self.assertEqual(data.get("effective_effort"), "unknown")
                if level != "low":
                    self.assertIn("--resume", args)

    def test_codex_auto_choice_is_accepted_only_for_medium_or_high(self):
        # The bridge transports Codex's semantic choice; it never automatically spends xhigh/max.
        self.initialize()
        for level in ("low", "xhigh", "max"):
            data = self.parsed(self.invoke("run", "--effort", level, "--effort-source", "auto", "--task", "guard"), 3)
            self.assertEqual(data["reason"], "auto_effort_must_be_medium_or_high")
            self.assertFalse(self.capture.exists())
        for level in ("medium", "high"):
            data = self.parsed(self.invoke("run", "--effort", level, "--effort-source", "auto",
                "--effort-reason", "Codex classified a bounded task with known interfaces.", "--task", "fixture"))
            self.assertEqual(data.get("requested_effort"), level)
            self.assertEqual(data.get("effort_source"), "auto")

    def test_auto_or_user_source_without_explicit_effort_is_rejected(self):
        # A source label alone cannot falsely turn an unchosen default into a user/semantic choice.
        self.initialize()
        for source in ("auto", "user"):
            data = self.parsed(self.invoke("run", "--effort-source", source, "--task", "guard"), 3)
            self.assertEqual(data["reason"], "effort_source_requires_explicit_effort")
            self.assertFalse(self.capture.exists())

    def test_effort_dry_run_is_auditable_and_never_invokes_or_writes(self):
        # Previewing a chosen effort must remain read-only and disclose requested, not effective, effort.
        self.initialize()
        before = {str(p): p.read_bytes() for p in (self.project / ".ai").rglob("*") if p.is_file()}
        data = self.parsed(self.invoke("run", "--dry-run", "--effort", "high", "--effort-source", "auto",
            "--effort-reason", "Concurrent code paths require careful verification.", "--task", "not sent"))
        self.assertEqual(data.get("requested_effort"), "high")
        self.assertEqual(data.get("effort_source"), "auto")
        self.assertEqual(data.get("effective_effort"), "unknown")
        self.assertFalse(self.capture.exists())
        after = {str(p): p.read_bytes() for p in (self.project / ".ai").rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_effort_environment_override_blocks_without_exposing_or_removing_value(self):
        # This official env variable outranks --effort; silently clearing or ignoring it is wrong.
        self.initialize()
        result = self.invoke("run", "--effort", "high", "--task", "guard",
            extra_env={"CLAUDE_CODE_EFFORT_LEVEL": "PRIVATE_EFFORT_OVERRIDE"})
        data = self.parsed(result, 3)
        self.assertEqual(data["reason"], "effort_environment_override_refused")
        self.assertEqual(data["environment_names"], ["CLAUDE_CODE_EFFORT_LEVEL"])
        self.assertNotIn("PRIVATE_EFFORT_OVERRIDE", result.stdout + result.stderr)
        self.assertFalse(self.capture.exists())

    def test_settings_effort_env_override_is_refused_with_original_config_intact(self):
        # Settings env writes outrank a CLI choice just as the shell variable does.
        self.initialize()
        for base in (self.project, self.project.parent, self.home):
            with self.subTest(scope=str(base)):
                directory = base / ".claude"
                directory.mkdir(exist_ok=True)
                path = directory / "settings.local.json"
                path.write_text(json.dumps({"env": {"CLAUDE_CODE_EFFORT_LEVEL": "PRIVATE_SETTINGS_LEVEL"}}))
                original = path.read_bytes()
                result = self.invoke("run", "--effort", "medium", "--task", "guard")
                data = self.parsed(result, 3)
                self.assertEqual(data["reason"], "effort_environment_override_refused")
                self.assertNotIn("PRIVATE_SETTINGS_LEVEL", result.stdout + result.stderr)
                self.assertEqual(original, path.read_bytes())
                self.assertFalse(self.capture.exists())
                path.unlink()

    def test_saved_effort_defaults_and_caps_are_preserved_and_only_audited(self):
        # Explicit CLI levels override saved defaults; existing policy caps remain in force.
        self.initialize()
        directory = self.project / ".claude"
        directory.mkdir()
        path = directory / "settings.json"
        path.write_text(json.dumps({"effortLevel": "low", "maxEffortLevel": "medium",
            "modelSettings": {"claude-opus-5-5": {"effortLevel": "low"}}}))
        original = path.read_bytes()
        data = self.parsed(self.invoke("run", "--effort", "high", "--effort-source", "user", "--task", "fixture"))
        args = json.loads(self.capture.read_text())["args"]
        self.assertEqual(args[args.index("--effort") + 1], "high")
        self.assertEqual(original, path.read_bytes())
        self.assertEqual(data.get("effective_effort"), "unknown")
        policy = data.get("effort_policy", {})
        self.assertTrue(policy.get("saved_defaults_detected"))
        self.assertTrue(policy.get("possible_caps_detected"))
        self.assertNotIn("claude-opus-5-5", json.dumps(policy))

    def test_effort_reason_is_bounded_single_line_and_secret_shaped_values_are_redacted(self):
        # Audit reasons cannot become multiline task dumps or credential copies.
        self.initialize()
        for reason in ("a" * 161, "line one\nline two", "one\rsecond", "one\x01control"):
            data = self.parsed(self.invoke("run", "--effort", "medium", "--effort-reason", reason, "--task", "guard"), 3)
            self.assertEqual(data["reason"], "effort_reason_must_be_short_single_line")
            self.assertFalse(self.capture.exists())
        result = self.invoke("run", "--effort", "high", "--effort-source", "auto",
            "--effort-reason", 'Edge-case verification. {"password":"DUMMY_REASON_SECRET"}', "--task", "never log this private task")
        data = self.parsed(result)
        self.assertIn("Edge-case verification", data.get("effort_reason", ""))
        self.assertNotIn("DUMMY_REASON_SECRET", result.stdout + result.stderr)
        for path in (self.project / ".ai/logs").glob("*.json"):
            self.assertNotIn("DUMMY_REASON_SECRET", path.read_text())
            self.assertNotIn("never log this private task", path.read_text())
        self.assertNotIn("DUMMY_REASON_SECRET", (self.project / ".ai/HANDOFF.md").read_text())

    def test_missing_native_effort_capability_blocks_before_inference(self):
        # CLI capability verification must include the new effort flag.
        self.initialize()
        data = self.parsed(self.invoke("run", "--task", "guard", extra_env={"FAKE_HIDE_FLAG": "--effort"}), 3)
        self.assertEqual(data["reason"], "required_cli_flags_unverified")
        self.assertIn("--effort", data["unsupported_flags"])
        self.assertFalse(self.capture.exists())

    def test_failed_inference_records_requested_effort_without_replacing_good_session(self):
        # Permission failure still needs audit evidence for the request actually attempted.
        self.initialize()
        prior = (self.project / ".ai/sessions.json").read_bytes()
        data = self.parsed(self.invoke("run", "--effort", "high", "--effort-source", "user",
            "--effort-reason", "Explicit user choice.", "--task", "denied", extra_env={"FAKE_ACTION": "permission"}), 4)
        self.assertEqual(data.get("requested_effort"), "high")
        self.assertEqual(data.get("effort_source"), "user")
        self.assertEqual(data.get("effective_effort"), "unknown")
        self.assertEqual(prior, (self.project / ".ai/sessions.json").read_bytes())
        log = json.loads(next((self.project / ".ai/logs").glob("*.json")).read_text())
        self.assertEqual(log.get("requested_effort"), "high")
        self.assertIn("Requested effort: high", (self.project / ".ai/HANDOFF.md").read_text())

    def test_worktree_main_checkout_effort_env_override_is_not_missed(self):
        # Native worktree sessions can inherit the main checkout's local settings.
        main_project = self.project
        directory = main_project / ".claude"
        directory.mkdir()
        settings = directory / "settings.local.json"
        settings.write_text(json.dumps({"env": {"CLAUDE_CODE_EFFORT_LEVEL": "PRIVATE_MAIN_OVERRIDE"}}))
        original = settings.read_bytes()
        worktree = self.root / "linked-worktree"
        self.git("worktree", "add", "--detach", str(worktree), "HEAD")
        self.project = worktree
        self.initialize()
        result = self.invoke("run", "--task", "guard", "--effort", "high")
        data = self.parsed(result, 3)
        self.assertEqual(data["reason"], "effort_environment_override_refused")
        self.assertEqual(data["settings_file"], str(settings.resolve()))
        self.assertNotIn("PRIVATE_MAIN_OVERRIDE", result.stdout + result.stderr)
        self.assertEqual(original, settings.read_bytes())
        self.assertFalse(self.capture.exists())

    def test_managed_settings_dropins_are_checked_and_hidden_non_json_files_ignored(self):
        # Native managed drop-ins can override effort even without managed-settings.json.
        self.initialize()
        spec = importlib.util.spec_from_file_location("bridge_managed_fixture", BRIDGE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        managed = self.root / "managed"
        dropins = managed / "managed-settings.d"
        dropins.mkdir(parents=True)
        setting = {"env": {"CLAUDE_CODE_EFFORT_LEVEL": "PRIVATE_MANAGED_LEVEL"}}
        (dropins / ".hidden.json").write_text(json.dumps(setting))
        (dropins / "not-json.txt").write_text(json.dumps(setting))
        with mock.patch.dict(os.environ, self.env, clear=True), mock.patch.object(module, "MANAGED_SETTINGS_DIR", managed, create=True):
            module.route_guard(self.project.resolve())
            (dropins / "50-policy.json").write_text(json.dumps(setting))
            with self.assertRaises(module.Blocked) as caught:
                module.route_guard(self.project.resolve())
            self.assertEqual(caught.exception.reason, "effort_environment_override_refused")
            self.assertNotIn("PRIVATE_MANAGED_LEVEL", json.dumps(caught.exception.metadata))

    def test_effort_settings_are_rechecked_after_project_lock_is_acquired(self):
        # Another serial task can change settings between the preview guard and writer lock.
        self.initialize()
        spec = importlib.util.spec_from_file_location("bridge_lock_fixture", BRIDGE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        directory = self.project / ".claude"
        directory.mkdir()
        path = directory / "settings.local.json"
        @contextlib.contextmanager
        def changing_lock(project):
            path.write_text(json.dumps({"env": {"CLAUDE_CODE_EFFORT_LEVEL": "PRIVATE_POST_LOCK_OVERRIDE"}}))
            yield
        args = module.parser().parse_args(["--runtime", str(self.config), "run", "--project", str(self.project),
            "--effort", "high", "--task", "guard"])
        with mock.patch.dict(os.environ, self.env, clear=True), mock.patch.object(module, "project_lock", changing_lock):
            with self.assertRaises(module.Blocked) as caught:
                module.execute(self.project.resolve(), self.config, args)
            self.assertEqual(caught.exception.reason, "effort_environment_override_refused")
            self.assertFalse(self.capture.exists())

    def test_unquoted_token_assignments_in_effort_reason_do_not_leak(self):
        # Common unquoted token/authorization fields must match the JSON-key hygiene rules.
        self.initialize()
        for name in ("token", "access_token", "authorization"):
            with self.subTest(name=name):
                secret = "DUMMY_EFFORT_SECRET_" + name.upper()
                result = self.invoke("run", "--effort", "medium", "--effort-source", "user",
                    "--effort-reason", "Bounded task. " + name + "=" + secret, "--task", "fixture")
                self.parsed(result)
                self.assertNotIn(secret, result.stdout + result.stderr)
                for path in (self.project / ".ai/logs").glob("*.json"):
                    self.assertNotIn(secret, path.read_text())
                self.assertNotIn(secret, (self.project / ".ai/HANDOFF.md").read_text())


if __name__ == "__main__":
    unittest.main()
