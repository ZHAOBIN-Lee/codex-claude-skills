"""Offline declared-output, static Edit-rule and failure-diagnostic behavior.

The subprocess fixture never contacts a model; native CLI permission
enforcement is not reproduced here, only the bridge's own preflight/reporting.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest import mock

import test_bridge

OUT = "out.txt"


class PermissionTests(unittest.TestCase):
    git = test_bridge.BridgeTests.git
    invoke = test_bridge.BridgeTests.invoke
    parsed = test_bridge.BridgeTests.parsed
    initialize = test_bridge.BridgeTests.initialize
    bridge_module = test_bridge.BridgeTests.bridge_module

    def setUp(self):
        test_bridge.BridgeTests.setUp(self)
        self.initialize()

    # -- helpers -----------------------------------------------------------
    def settings(self, base, rules, name="settings.json", extra=None):
        directory = Path(base) / ".claude"
        directory.mkdir(exist_ok=True)
        data = {"permissions": rules}
        data.update(extra or {})
        path = directory / name
        path.write_text(json.dumps(data))
        return path

    def run_output(self, *outputs, task="declared output task", extra=(), extra_env=None, code=0):
        args = ["run", "--task", task]
        for output in outputs:
            args += ["--output", output]
        args += list(extra)
        return self.parsed(self.invoke(*args, extra_env=extra_env), code)

    def private_state(self):
        return {str(p.relative_to(self.project)): p.read_bytes()
                for p in (self.project / ".ai").rglob("*") if p.is_file()}

    def target_status(self, data, path=OUT):
        preflight = data["output_permission_preflight"]
        return {item["path"]: item["status"] for item in preflight["targets"]}[path]

    def assert_blocked_before_inference(self, data):
        self.assertEqual(data["status"], "blocked")
        self.assertIs(data["inference"], False)
        self.assertFalse(self.capture.exists())

    def log(self):
        # Same-second log names sort randomly; the newest write is the latest run.
        newest = max((self.project / ".ai/logs").glob("*.json"), key=lambda path: path.stat().st_mtime_ns)
        return json.loads(newest.read_text())

    def handoff(self):
        """Only the newest bridge evidence block."""
        return (self.project / ".ai/HANDOFF.md").read_text().split("<!-- claude-bridge:")[-1]

    # -- declared outputs and static Edit rules ------------------------------
    def test_legacy_run_without_outputs_keeps_working_and_adds_no_output_fields(self):
        data = self.parsed(self.invoke("run", "--task", "legacy"))
        self.assertEqual(data["status"], "complete")
        self.assertNotIn("declared_outputs", data)
        self.assertNotIn("output_permission_preflight", data)

    def test_missing_edit_rule_blocks_before_any_inference(self):
        before = self.private_state()
        data = self.run_output(OUT, code=3)
        self.assert_blocked_before_inference(data)
        self.assertEqual(self.target_status(data), "missing_rule")
        self.assertFalse(data["output_permission_preflight"]["ready"])
        self.assertEqual(before, self.private_state())

    def test_exact_edit_grants_from_confirmed_sources_allow_the_run(self):
        absolute = "//" + str(self.project.resolve()).lstrip("/") + "/" + OUT
        cases = {
            "project /path": lambda: self.settings(self.project, {"allow": ["Edit(/out.txt)"]}),
            "project relative": lambda: self.settings(self.project, {"allow": ["Edit(out.txt)"]}),
            "project dot-relative": lambda: self.settings(self.project, {"allow": ["Edit(./out.txt)"]}),
            "local settings": lambda: self.settings(self.project, {"allow": ["Edit(/out.txt)"]}, "settings.local.json"),
            "user absolute": lambda: self.settings(self.home, {"allow": ["Edit(" + absolute + ")"]}),
        }
        for name, make in cases.items():
            with self.subTest(source=name):
                path = make()
                data = self.run_output(OUT)
                self.assertEqual(data["status"], "complete")
                self.assertEqual(self.target_status(data), "static_covered")
                self.assertTrue(data["output_permission_preflight"]["ready"])
                self.assertEqual(data["output_permission_preflight"]["coverage"], "local_file_scan")
                self.capture.unlink()
                path.unlink()

    def test_user_slash_path_anchors_at_claude_directory_not_project(self):
        # In user settings /out.txt means ~/.claude/out.txt, never the project root.
        self.settings(self.home, {"allow": ["Edit(/out.txt)"]})
        data = self.run_output(OUT, code=3)
        self.assert_blocked_before_inference(data)
        self.assertEqual(self.target_status(data), "missing_rule")

    def test_worktree_uses_main_checkout_local_settings_but_not_without_them(self):
        main = self.project
        worktree = self.root / "linked-worktree"
        self.git("worktree", "add", "--detach", str(worktree), "HEAD")
        self.project = worktree
        self.initialize()
        data = self.run_output(OUT, code=3)
        self.assertEqual(self.target_status(data), "missing_rule")
        self.settings(main, {"allow": ["Edit(/out.txt)"]}, "settings.local.json")
        data = self.run_output(OUT)
        self.assertEqual(data["status"], "complete")
        self.assertEqual(self.target_status(data), "static_covered")

    def test_ancestor_and_unconfirmed_user_local_allow_rules_are_not_grants(self):
        absolute = "//" + str(self.project.resolve()).lstrip("/") + "/" + OUT
        self.settings(self.root, {"allow": ["Edit(" + absolute + ")", "Edit(project/out.txt)"]})
        self.settings(self.root, {"allow": ["Edit(" + absolute + ")"]}, "settings.local.json")
        self.settings(self.home, {"allow": ["Edit(" + absolute + ")"]}, "settings.local.json")
        data = self.run_output(OUT, code=3)
        self.assert_blocked_before_inference(data)
        self.assertEqual(self.target_status(data), "missing_rule")
        limits = data["output_permission_preflight"]["limitations"]
        self.assertIn("ancestor_settings_not_counted_as_grants", limits)
        self.assertIn("user_local_settings_not_assumed", limits)

    def test_write_rule_does_not_grant_file_writes(self):
        self.settings(self.project, {"allow": ["Write(/out.txt)", "Write(out.txt)", "MultiEdit(/out.txt)"]})
        data = self.run_output(OUT, code=3)
        self.assert_blocked_before_inference(data)
        self.assertEqual(self.target_status(data), "missing_rule")

    def test_deny_ask_and_read_rules_override_an_exact_edit_grant(self):
        absolute = "//" + str(self.project.resolve()).lstrip("/") + "/" + OUT
        conflicts = {
            "edit deny": {"deny": ["Edit(/out.txt)"]},
            "edit ask": {"ask": ["Edit(/out.txt)"]},
            "bare edit deny": {"deny": ["Edit"]},
            "bare edit ask": {"ask": ["Edit"]},
            "write deny": {"deny": ["Write(/out.txt)"]},
            "write ask": {"ask": ["Write(./out.txt)"]},
            "read deny": {"deny": ["Read(/out.txt)"]},
            "read ask": {"ask": ["Read(out.txt)"]},
            "bare read deny": {"deny": ["Read"]},
            "absolute read deny": {"deny": ["Read(" + absolute + ")"]},
            "directory read deny": {"deny": ["Read(/)"]},
        }
        for name, extra in conflicts.items():
            with self.subTest(conflict=name):
                self.settings(self.project, {"allow": ["Edit(/out.txt)"]})
                local = self.settings(self.project, extra, "settings.local.json")
                data = self.run_output(OUT, code=3)
                self.assert_blocked_before_inference(data)
                self.assertEqual(self.target_status(data), "deny_or_ask_may_apply")
                local.unlink()

    def test_deny_from_another_confirmed_source_beats_project_allow(self):
        self.settings(self.project, {"allow": ["Edit(/out.txt)"]})
        self.settings(self.home, {"deny": ["Read(~/" + "x" + ")"]})  # unrelated deny stays harmless
        self.assertEqual(self.run_output(OUT)["status"], "complete")
        self.capture.unlink()
        absolute = "//" + str(self.project.resolve()).lstrip("/") + "/" + OUT
        self.settings(self.home, {"ask": ["Edit(" + absolute + ")"]})
        data = self.run_output(OUT, code=3)
        self.assertEqual(self.target_status(data), "deny_or_ask_may_apply")

    def test_unknown_patterns_block_but_unrelated_patterns_do_not_hide_missing_rule(self):
        marker = "PRIVATE_RULE_MARKER"
        cases = {
            "allow glob only": ({"allow": ["Edit(**/*.txt)"]}, "unknown"),
            "allow dir glob": ({"allow": ["Edit(/src/**)"]}, "unknown", "src/a.txt"),
            "deny glob beside exact grant": ({"allow": ["Edit(/out.txt)"], "deny": ["Read(**/" + marker + "*)"]}, "unknown"),
            "ask glob beside exact grant": ({"allow": ["Edit(/out.txt)"], "ask": ["Edit(*.txt)"]}, "unknown"),
            "dot dot rule": ({"allow": ["Edit(/out.txt)"], "deny": ["Edit(/a/../out.txt)"]}, "unknown"),
            "malformed rule": ({"allow": ["Edit(/out.txt)"], "deny": ["Edit(/out.txt"]}, "unknown"),
            "empty specifier": ({"allow": ["Edit(/out.txt)"], "deny": ["Edit()"]}, "unknown"),
            "bare filename may match at depth": ({"allow": ["Edit(deep.txt)"]}, "unknown", "sub/deep.txt"),
            "unrelated glob": ({"allow": ["Edit(docs/**)"]}, "missing_rule"),
            "unrelated literal": ({"allow": ["Edit(/other.txt)"]}, "missing_rule"),
            "malformed permissions": ({"allow": "Edit(/out.txt)"}, "unknown"),
        }
        for name, spec in cases.items():
            rules, expected = spec[0], spec[1]
            target = spec[2] if len(spec) > 2 else OUT
            with self.subTest(case=name):
                self.settings(self.project, rules)
                result = self.invoke("run", "--task", "pattern", "--output", target)
                data = self.parsed(result, 3)
                self.assert_blocked_before_inference(data)
                self.assertEqual(self.target_status(data, target), expected)
                self.assertNotIn(marker, result.stdout + result.stderr)

    def test_oversized_rule_list_is_unknown_not_silently_truncated(self):
        self.settings(self.project, {"allow": ["Edit(/out.txt)"] + ["Edit(/pad%d.txt)" % i for i in range(1200)]})
        data = self.run_output(OUT, code=3)
        self.assert_blocked_before_inference(data)
        self.assertEqual(self.target_status(data), "unknown")

    def test_managed_sources_grant_and_managed_only_policy_discards_other_allow_rules(self):
        module = self.bridge_module()
        managed = self.root / "managed"
        (managed / "managed-settings.d").mkdir(parents=True)
        with mock.patch.dict(os.environ, self.env, clear=True), mock.patch.object(module, "MANAGED_SETTINGS_DIR", managed):
            project = self.project.resolve()
            def status():
                return module.output_permission_preflight(project, [OUT])["targets"][0]["status"]
            dropin = managed / "managed-settings.d" / "10-edit.json"
            self.assertEqual(status(), "missing_rule")
            dropin.write_text(json.dumps({"permissions": {"allow": ["Edit(//" + str(project).lstrip("/") + "/out.txt)"]}}))
            self.assertEqual(status(), "static_covered")
            # A managed single-slash anchor is ambiguous, so it cannot be proven to grant.
            dropin.write_text(json.dumps({"permissions": {"allow": ["Edit(/out.txt)"]}}))
            self.assertEqual(status(), "unknown")
            dropin.unlink()
            (managed / "managed-settings.json").write_text(json.dumps({"permissions": {"allow": ["Edit(./out.txt)"]}}))
            self.assertEqual(status(), "static_covered")
            (managed / "managed-settings.json").write_text(
                json.dumps({"allowManagedPermissionRulesOnly": True, "permissions": {"allow": []}}))
            self.settings(self.project, {"allow": ["Edit(/out.txt)"]})
            verdict = module.output_permission_preflight(project, [OUT])
            self.assertEqual(verdict["targets"][0]["status"], "missing_rule")
            self.assertTrue(verdict["managed_permission_rules_only"])

    def test_diagnostics_never_echo_rule_values_and_settings_are_not_modified(self):
        marker = "PRIVATE_RULE_MARKER"
        path = self.settings(self.project, {"allow": ["Edit(/" + marker + "/**)", "Write(/" + marker + ")"],
                                            "deny": ["Edit(**/" + marker + ")"]})
        original = path.read_bytes()
        result = self.invoke("run", "--task", "diag", "--output", OUT)
        self.parsed(result, 3)
        self.assertNotIn(marker, result.stdout + result.stderr)
        self.assertEqual(original, path.read_bytes())

    # -- path validation -----------------------------------------------------
    def test_invalid_output_paths_are_rejected_before_inference_and_state_is_untouched(self):
        self.settings(self.project, {"allow": ["Edit"]})  # permissive: only path validation can block
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "target.txt").write_text("outside original")
        (self.project / "linkdir").symlink_to(outside)
        (self.project / "linkfile").symlink_to(outside / "target.txt")
        (self.project / "subdir").mkdir()
        (self.project / "regular.txt").write_text("x")
        bad = ["../escape.txt", "sub/../../escape.txt", "/etc/hosts", str(self.project / "abs.txt"),
               "~/note.txt", "linkdir/new.txt", "linkfile", "subdir", "regular.txt/child", "", ".", "dir/",
               "a*.txt", "a?.txt", "[x].txt", "a\\b.txt", "with\nnewline.txt", ".git/config",
               ".git/hooks/pre-commit", "nested/.git/config", ".claude/settings.local.json",
               ".CLAUDE/settings.json", ".GIT/config", ".ai/HANDOFF.md", ".ai/handoff.md",
               ".ai/STATE.yaml", ".ai/VALIDATION.md", ".ai/PROGRESS.md", ".ai/sessions.json",
               ".ai/consult.json", ".ai/logs/x.json", ".ai/backups/x.bak", ".ai/bridge.lock",
               ".ai/other.lock", ".ai/requests/r.json", ".ai/.gitignore", "x" * 1100]
        before = self.private_state()
        for path in bad:
            with self.subTest(path=path[:40]):
                data = self.parsed(self.invoke("run", "--task", "bad path", "--output", path), 3)
                self.assert_blocked_before_inference(data)
        self.assertEqual(before, self.private_state())
        self.assertEqual((outside / "target.txt").read_text(), "outside original")

    def test_bare_edit_allow_is_broad_not_an_exact_grant_and_blocks_before_inference(self):
        prior = self.seed_session()
        path = self.settings(self.project, {"allow": ["Edit"]})
        original = path.read_bytes()
        before = self.private_state()
        result = self.invoke("run", "--task", "bare allow", "--output", "docs/plan.md")
        data = self.parsed(result, 3)
        self.assert_blocked_before_inference(data)
        self.assertEqual(data["reason"], "declared_output_edit_permission_unconfirmed")
        self.assertEqual(self.target_status(data, "docs/plan.md"), "unknown")
        self.assertFalse(data["output_permission_preflight"]["ready"])
        self.assertEqual(data["output_permission_preflight"]["targets"][0]["reason_codes"],
                         ["related_pattern_or_ambiguous_rule"])
        self.assertEqual(before, self.private_state())
        self.assertEqual(prior, (self.project / ".ai/sessions.json").read_bytes())
        self.assertEqual(original, path.read_bytes())
        self.assertNotIn('"Edit"', result.stdout)
        # An exact grant beside the bare one still supplies coverage; neither rule is changed.
        self.settings(self.project, {"allow": ["Edit", "Edit(/docs/plan.md)"]})
        data = self.run_output("docs/plan.md")
        self.assertEqual(data["status"], "complete")
        self.assertEqual(self.target_status(data, "docs/plan.md"), "static_covered")
        self.capture.unlink()
        # A bare Edit deny or ask still blocks everything, even beside an exact grant.
        for rules in ({"allow": ["Edit(/docs/plan.md)"], "deny": ["Edit"]},
                      {"allow": ["Edit(/docs/plan.md)"], "ask": ["Edit"]}):
            self.settings(self.project, rules)
            data = self.run_output("docs/plan.md", code=3)
            self.assertEqual(self.target_status(data, "docs/plan.md"), "deny_or_ask_may_apply")

    def seed_session(self):
        self.parsed(self.invoke("run", "--task", "seed"))
        self.capture.unlink()  # later assertions look for a capture from the run under test
        return (self.project / ".ai/sessions.json").read_bytes()

    def test_allowed_new_nested_and_existing_paths_are_accepted(self):
        # Exact rules for the three real outputs; a bare Edit allow would not be a precise grant.
        self.settings(self.project, {"allow": ["Edit(/existing.txt)", "Edit(/docs/new/readme.md)",
                                               "Edit(/.ai/PROJECT_CONTEXT.md)"]})
        (self.project / "existing.txt").write_text("old\n")
        data = self.run_output("existing.txt", "docs/new/readme.md", ".ai/PROJECT_CONTEXT.md")
        self.assertEqual(data["status"], "complete")
        self.assertEqual([item["path"] for item in data["declared_outputs"]],
                         ["existing.txt", "docs/new/readme.md", ".ai/PROJECT_CONTEXT.md"])

    def test_consult_workflow_blocks_declared_outputs(self):
        self.settings(self.project, {"allow": ["Edit"]})
        config = json.loads(self.config.read_text())
        config["usage_credits_confirmation"] = {"source": "user", "date": "2026-10-04", "timezone": "Australia/Melbourne"}
        self.config.write_text(json.dumps(config))
        data = self.parsed(self.invoke("run", "--workflow", "consult", "--task", "analysis",
                                       "--output", OUT), 3)
        self.assert_blocked_before_inference(data)
        self.assertEqual(data["reason"], "outputs_not_allowed_in_consult_workflow")
        data = self.parsed(self.invoke("run", "--workflow", "consult", "--task", "analysis",
                                       "--output", OUT, "--dry-run"), 3)
        self.assert_blocked_before_inference(data)

    def test_dry_run_with_outputs_is_read_only_without_auth_probe_or_inference(self):
        self.settings(self.project, {"allow": ["Edit(/out.txt)"]})
        (self.project / OUT).write_text("existing body\n")
        before = self.private_state()
        data = self.parsed(self.invoke("run", "--task", "preview", "--output", OUT, "--dry-run",
            extra_env={"FAKE_AUTH": json.dumps({"loggedIn": False, "authMethod": "none"}),
                       "FAKE_AUTH_EXIT": "1"}))
        self.assertEqual(data["status"], "dry_run")
        self.assertIs(data["inference"], False)
        self.assertFalse(self.capture.exists())
        self.assertEqual(before, self.private_state())
        self.assertEqual((self.project / OUT).read_text(), "existing body\n")
        self.assertEqual(data["declared_outputs"], [OUT])
        self.assertEqual(self.target_status(data), "static_covered")
        self.assertNotIn("existing body", json.dumps(data))
        missing = self.parsed(self.invoke("run", "--task", "preview", "--output", "none.txt", "--dry-run"))
        self.assertEqual(missing["status"], "dry_run")
        self.assertFalse(missing["output_permission_preflight"]["ready"])

    def test_multiple_outputs_all_need_coverage(self):
        self.settings(self.project, {"allow": ["Edit(/out.txt)"]})
        data = self.run_output(OUT, "second.txt", code=3)
        self.assert_blocked_before_inference(data)
        self.assertEqual(self.target_status(data, OUT), "static_covered")
        self.assertEqual(self.target_status(data, "second.txt"), "missing_rule")
        self.settings(self.project, {"allow": ["Edit(/out.txt)", "Edit(/second.txt)"]})
        self.assertEqual(self.run_output(OUT, "second.txt")["status"], "complete")

    # -- snapshots ---------------------------------------------------------------
    def test_snapshots_report_created_modified_unchanged_without_file_bodies(self):
        self.settings(self.project, {"allow": ["Edit(/out.txt)", "Edit(/kept.txt)", "Edit(/old.txt)"]})
        (self.project / "kept.txt").write_text("kept body\n")
        (self.project / "old.txt").write_text("OLD_BODY_MARKER\n")
        new_body = "NEW_BODY_MARKER\n"
        result = self.invoke("run", "--task", "write", "--output", OUT, "--output", "kept.txt",
                             "--output", "old.txt", extra_env={"FAKE_WRITE_PATH": "old.txt", "FAKE_WRITE_CONTENT": new_body})
        data = self.parsed(result)
        changes = {item["path"]: item for item in data["declared_outputs"]}
        self.assertEqual(changes[OUT]["change"], "unchanged")
        self.assertFalse(changes[OUT]["after"]["exists"])
        self.assertEqual(changes["kept.txt"]["change"], "unchanged")
        self.assertEqual(changes["kept.txt"]["after"]["sha256"], hashlib.sha256(b"kept body\n").hexdigest())
        self.assertEqual(changes["old.txt"]["change"], "modified")
        self.assertEqual(changes["old.txt"]["before"]["sha256"], hashlib.sha256(b"OLD_BODY_MARKER\n").hexdigest())
        self.assertEqual(changes["old.txt"]["after"]["bytes"], len(new_body))
        self.assertEqual(changes["old.txt"]["after"]["sha256"], hashlib.sha256(new_body.encode()).hexdigest())
        self.assertEqual(data["output_observation"]["kind"], "observation_only")
        everything = result.stdout + json.dumps(self.log()) + self.handoff()
        for marker in ("OLD_BODY_MARKER", "NEW_BODY_MARKER"):
            self.assertNotIn(marker, everything)
        self.assertIn("old.txt", self.log()["declared_outputs"][2]["path"])

    def test_created_output_is_reported_and_failed_run_is_never_restored_or_retried(self):
        self.settings(self.project, {"allow": ["Edit(/out.txt)"]})
        data = self.run_output(OUT, extra_env={"FAKE_ACTION": "nonzero", "FAKE_WRITE_PATH": OUT,
                                              "FAKE_WRITE_CONTENT": "partial work\n"}, code=4)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["declared_outputs"][0]["change"], "created")
        self.assertEqual((self.project / OUT).read_text(), "partial work\n")
        self.assertEqual(len(list((self.project / ".ai/logs").glob("*.json"))), 1)

    def test_snapshot_flags_symlink_swapped_in_during_run_without_following_it(self):
        self.settings(self.project, {"allow": ["Edit(/out.txt)"]})
        secret = self.root / "private.txt"
        secret.write_text("SYMLINK_TARGET_BODY")
        module = self.bridge_module()
        (self.project / OUT).symlink_to(secret)
        entry = module.snapshot_output(self.project.resolve(), OUT, {"remaining": 1 << 20})
        self.assertEqual(entry["state"], "symlink")
        self.assertIsNone(entry["sha256"])
        self.assertNotIn("SYMLINK_TARGET_BODY", json.dumps(entry))

    def test_bounded_hashing_marks_large_outputs_unhashed_not_unchanged(self):
        module = self.bridge_module()
        (self.project / OUT).write_bytes(b"a" * 64)
        with mock.patch.object(module, "OUTPUT_HASH_LIMIT", 16):
            first = module.snapshot_output(self.project.resolve(), OUT, {"remaining": 1 << 20})
            (self.project / OUT).write_bytes(b"b" * 64)
            second = module.snapshot_output(self.project.resolve(), OUT, {"remaining": 1 << 20})
        self.assertIsNone(first["sha256"])
        self.assertEqual(first["bytes"], 64)
        self.assertEqual(module.output_change(first, second), "unknown")

    # -- timeout and permission-denial honesty ------------------------------------
    def test_timeout_keeps_stream_byte_counts_but_not_text_and_marks_denials_unavailable(self):
        prior = (self.project / ".ai/sessions.json").read_bytes()
        result = self.invoke("run", "--task", "stall", "--timeout", "1.5",
                             extra_env={"FAKE_ACTION": "timeout_partial"})
        data = self.parsed(result, 4)
        self.assertEqual(data["status"], "timeout")
        self.assertGreater(data["cli_output"]["stdout_bytes"], 50)
        self.assertEqual(data["cli_output"]["stderr_bytes"], len("PARTIAL_STDERR_TEXT sk-ant-MUST-NOT-LEAK"))
        self.assertEqual(data["cli_output"]["stdout_format"], "malformed")
        self.assertEqual(data["termination"]["timeout_seconds"], 1.5)
        self.assertIn(data["termination"]["signal_sent"], {"SIGTERM", "SIGKILL"})
        self.assertEqual(data["termination"]["completion"], "unknown")
        self.assertIsNone(data["permission_denials"])
        self.assertEqual(data["permission_denials_status"], "unavailable")
        self.assertEqual(data["actual_models"], [])
        self.assertEqual(data["actual_models_status"], "unavailable")
        self.assertIsNone(data["session_id"])
        self.assertEqual(data["returned_session_id_status"], "unavailable")
        self.assertEqual(prior, (self.project / ".ai/sessions.json").read_bytes())
        for text in (result.stdout + result.stderr, json.dumps(self.log()), self.handoff()):
            self.assertNotIn("PARTIAL_STDOUT_SECRET", text)
            self.assertNotIn("PARTIAL_STDERR_TEXT", text)
            self.assertNotIn("MUST-NOT-LEAK", text)
            self.assertNotIn("claude-opus-9-9", text)
        log = self.log()
        self.assertIsNone(log["permission_denials"])
        self.assertEqual(log["permission_denials_status"], "unavailable")
        self.assertEqual(log["termination"]["completion"], "unknown")
        self.assertIn("Permission denials: unavailable", self.handoff())

    def test_timeout_after_complete_final_result_retains_metadata_without_marking_complete(self):
        prior = (self.project / ".ai/sessions.json").read_bytes()
        data = self.parsed(self.invoke("run", "--task", "stall after final", "--timeout", "1.5",
                           extra_env={"FAKE_ACTION": "timeout_final",
                                      "FAKE_SESSION": "44444444-4444-4444-8444-444444444444"}), 4)
        self.assertEqual(data["status"], "timeout")
        self.assertNotIn("result", data)
        self.assertEqual(data["permission_denials"], [])
        self.assertEqual(data["permission_denials_status"], "none_reported")
        self.assertEqual(data["actual_models"], ["claude-sonnet-4-6"])
        self.assertEqual(data["cli_output"]["stdout_format"], "json_object")
        self.assertEqual(data["termination"]["completion"], "unknown")
        # The genuine final result's own ID is reported; forced termination never saves it.
        self.assertEqual(data["session_id"], "44444444-4444-4444-8444-444444444444")
        self.assertEqual(data["returned_session_id_status"], "returned")
        self.assertFalse(data["session_saved"])
        self.assertEqual(prior, (self.project / ".ai/sessions.json").read_bytes())
        data = self.parsed(self.invoke("run", "--task", "stall without field", "--timeout", "1.5",
                           extra_env={"FAKE_ACTION": "timeout_final_no_denials"}), 4)
        self.assertEqual(data["permission_denials_status"], "unavailable")
        self.assertIsNone(data["permission_denials"])

    def test_legacy_timeout_without_any_output_never_reports_empty_denials(self):
        data = self.parsed(self.invoke("run", "--task", "sleep", "--timeout", "0.5",
                           extra_env={"FAKE_ACTION": "timeout"}), 4)
        self.assertEqual(data["status"], "timeout")
        self.assertIsNone(data["permission_denials"])
        self.assertEqual(data["cli_output"]["stdout_bytes"], 0)
        self.assertIsNone(self.log()["permission_denials"])

    def test_permission_denial_status_is_listed_none_reported_or_unavailable_everywhere(self):
        cases = (("success", 0, "none_reported", []),
                 ("permission", 4, "listed", ["Bash"]),
                 ("permission_nonzero", 4, "listed", ["Bash"]),
                 ("no_denials_field", 0, "unavailable", None),
                 ("nonzero_no_denials", 4, "unavailable", None),
                 ("nonzero", 4, "unavailable", None),
                 ("malformed", 4, "unavailable", None),
                 ("oversized", 4, "unavailable", None))
        for action, code, status, denials in cases:
            with self.subTest(action=action):
                data = self.parsed(self.invoke("run", "--task", "status " + action,
                                               extra_env={"FAKE_ACTION": action}), code)
                self.assertEqual(data["permission_denials_status"], status)
                self.assertEqual(data["permission_denials"], denials)
                log = self.log()
                self.assertEqual(log["permission_denials_status"], status)
                self.assertEqual(log["permission_denials"], denials)
                self.assertIn("Permission denials: " + status, self.handoff())

    def test_nonzero_final_json_keeps_known_denials_and_overall_failure(self):
        data = self.parsed(self.invoke("run", "--task", "deny", extra_env={"FAKE_ACTION": "permission_nonzero"}), 4)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["claude_exit_code"], 9)
        self.assertEqual(data["permission_denials_status"], "listed")
        self.assertEqual(data["actual_models"], ["claude-sonnet-4-6"])
        self.assertEqual(data["actual_models_status"], "reported")
        self.assertNotIn("secret private command", json.dumps(data) + json.dumps(self.log()))

    def test_nonzero_malformed_and_oversized_outputs_have_finite_safe_diagnostics(self):
        for action, fmt, stdout_min in (("nonzero", "empty", 0), ("malformed", "malformed", 10),
                                         ("oversized", "too_large", 10485761)):
            with self.subTest(action=action):
                result = self.invoke("run", "--task", "diag", extra_env={"FAKE_ACTION": action})
                data = self.parsed(result, 4)
                diag = data["cli_output"]
                self.assertEqual(diag["stdout_format"], fmt)
                self.assertGreaterEqual(diag["stdout_bytes"], stdout_min)
                self.assertTrue(set(diag) <= {"stdout_bytes", "stderr_bytes", "stdout_format", "stderr"})
                self.assertEqual(data["actual_models"], [])
                self.assertEqual(data["actual_models_status"], "unavailable")
                self.assertNotIn("MUST-NOT-LEAK", result.stdout + json.dumps(self.log()) + self.handoff())
                self.assertLess(len(json.dumps(self.log())), 6000)

    def test_returned_session_and_models_come_only_from_the_final_result(self):
        first = self.parsed(self.invoke("run", "--task", "one"))
        self.assertEqual(first["returned_session_id_status"], "returned")
        resumed_state = (self.project / ".ai/sessions.json").read_bytes()
        data = self.parsed(self.invoke("run", "--task", "no models", extra_env={"FAKE_ACTION": "no_model_usage"}))
        self.assertEqual(data["actual_models"], [])
        self.assertEqual(data["actual_models_status"], "unavailable")
        self.assertEqual(self.log()["actual_models_status"], "unavailable")
        self.assertEqual(json.loads(resumed_state)["claude"]["session_id"], first["session_id"])
        failed = self.parsed(self.invoke("run", "--task", "denied", extra_env={
            "FAKE_ACTION": "permission", "FAKE_SESSION": "22222222-2222-4222-8222-222222222222"}), 4)
        # A genuine unsuccessful final result reports its returned ID, distinct from the resumed
        # session, without saving it.
        self.assertEqual(failed["session_id"], "22222222-2222-4222-8222-222222222222")
        self.assertFalse(failed["session_saved"])
        self.assertEqual(failed["resumed_session"], first["session_id"])
        self.assertEqual(failed["returned_session_id_status"], "returned")
        self.assertEqual(resumed_state, (self.project / ".ai/sessions.json").read_bytes())

    # -- result truncation -----------------------------------------------------------
    def test_oversized_result_fields_are_flagged_instead_of_counted_complete(self):
        result = self.invoke("run", "--task", "long", extra_env={"FAKE_ACTION": "truncate"})
        data = self.parsed(result)
        self.assertEqual(data["status"], "complete")
        self.assertIs(data["result_complete"], False)
        self.assertEqual(sorted(data["truncated_result_fields"]),
                         ["Decisions[entries]", "Summary", "Tests[element]", "Tests[entries]"])
        self.assertEqual(len(data["result"]["Summary"]), 8000)
        self.assertEqual(len(data["result"]["Tests"]), 100)
        self.assertEqual(len(data["result"]["Tests"][0]), 8000)
        self.assertEqual(len(data["result"]["Decisions"]), 100)
        log = self.log()
        self.assertIs(log["result_complete"], False)
        self.assertEqual(sorted(log["truncated_result_fields"]), sorted(data["truncated_result_fields"]))
        self.assertNotIn("S" * 100, json.dumps(log))
        self.assertIn("incomplete", self.handoff().lower())

    def test_within_limit_results_report_complete_and_no_truncated_fields(self):
        data = self.parsed(self.invoke("run", "--task", "short"))
        self.assertIs(data["result_complete"], True)
        self.assertEqual(data["truncated_result_fields"], [])
        self.assertEqual(self.log()["truncated_result_fields"], [])

    # -- bounds and help --------------------------------------------------------------
    def test_max_turns_and_timeout_bounds_have_separate_codes_ranges_and_no_inference(self):
        turns = ("max_turns_out_of_bounds", "1..20")
        seconds = ("timeout_out_of_bounds", "0<seconds<=3600")
        for option, reason_and_bound in (("--max-turns=32", turns), ("--max-turns=0", turns), ("--max-turns=21", turns),
                                         ("--max-turns=-5", turns), ("--timeout=0", seconds), ("--timeout=-1", seconds),
                                         ("--timeout=3601", seconds), ("--timeout=nan", seconds),
                                         ("--timeout=inf", seconds), ("--timeout=-inf", seconds)):
            with self.subTest(option=option):
                data = self.parsed(self.invoke("run", "--task", "bounds", option), 3)
                self.assert_blocked_before_inference(data)
                self.assertEqual((data["reason"], data["allowed_range"]), reason_and_bound)
        for option in ("--max-turns=20", "--max-turns=1", "--timeout=3600", "--timeout=0.5"):
            with self.subTest(accepted=option):
                self.assertEqual(self.parsed(self.invoke("run", "--task", "bounds", "--dry-run", option))["status"], "dry_run")

    def test_help_states_numeric_bounds_and_output_option(self):
        result = subprocess.run([sys.executable, str(test_bridge.BRIDGE), "run", "--help"], env=self.env,
                                text=True, capture_output=True, timeout=20)
        text = re.sub(r"\s+", " ", result.stdout)
        self.assertIn("1..20", text)
        self.assertIn("default 3", text)
        self.assertIn("0<seconds<=3600", text)
        self.assertIn("default 120", text)
        self.assertIn("--output PATH", text)

    def test_new_metadata_is_synchronized_into_the_metadata_only_log_and_handoff(self):
        self.settings(self.project, {"allow": ["Edit(/out.txt)"]})
        self.run_output(OUT, extra_env={"FAKE_WRITE_PATH": OUT, "FAKE_WRITE_CONTENT": "LOGGED_BODY_MARKER\n"})
        log = self.log()
        for key in ("permission_denials_status", "actual_models_status", "returned_session_id_status",
                    "cli_output", "result_complete", "truncated_result_fields", "declared_outputs",
                    "output_permission_preflight", "output_observation"):
            self.assertIn(key, log)
        self.assertEqual(log["declared_outputs"][0]["change"], "created")
        self.assertNotIn("LOGGED_BODY_MARKER", json.dumps(log) + self.handoff())
        self.assertIn("Declared outputs", self.handoff())
        self.assertNotIn("result", log)


if __name__ == "__main__":
    unittest.main()
