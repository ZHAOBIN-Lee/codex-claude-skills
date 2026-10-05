import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import devflow  # noqa: E402

TASK = """---
id: {id}
title: {title}
status: pending
risk: {risk}
complexity: {cx}
domains: {domains}
executor_tier: {tier}
dependencies: []
---

# Objective
{title}
"""


def make_project(config=None):
    tmp = tempfile.TemporaryDirectory()
    devflow.init(tmp.name)
    if config:
        (Path(tmp.name) / ".ai" / "config.yaml").write_text(config)
    return tmp


def add_task(project, id, title="Add helper", risk="low", cx=3, domains="[]", tier="efficient"):
    path = Path(project) / ".ai" / "tasks" / (id + ".md")
    path.write_text(TASK.format(id=id, title=title, risk=risk, cx=cx, domains=domains, tier=tier))


def walk(project, steps):
    out = None
    for step in steps:
        out = devflow.transition(project, step)
    return out


class YamlTests(unittest.TestCase):
    def test_roundtrip_state_template(self):
        text = (ROOT / "templates" / "STATE.yaml").read_text().replace("{{UPDATED_AT}}", "2026-10-04T21:00:00+11:00")
        data = devflow.parse_yaml(text)
        self.assertEqual(data["current_phase"], "UNINITIALIZED")
        self.assertEqual(data["counters"]["rework_cycles"], 0)
        self.assertEqual(devflow.parse_yaml("\n".join(devflow.dump_yaml(data))), data)

    def test_config_template_parses_and_matches_defaults(self):
        data = devflow.parse_yaml((ROOT / "templates" / "config.yaml").read_text())
        self.assertEqual(data["routing"], devflow.DEFAULTS["routing"])
        self.assertEqual(data["risk"]["force_strong_for"], devflow.DEFAULTS["risk"]["force_strong_for"])
        self.assertEqual(data["tiers"]["strong"]["bridge_mode"], "ask")

    def test_task_template_front_matter(self):
        meta, body = devflow.parse_task((ROOT / "templates" / "TASK.md").read_text())
        self.assertEqual(meta["complexity"], 4)
        self.assertEqual(meta["domains"], [])
        for section in ("Objective", "Scope", "Non-Scope", "Acceptance Criteria", "Validation", "Escalation Conditions"):
            self.assertIn("# " + section, body)


class InitTests(unittest.TestCase):
    def test_init_never_overwrites_and_leaves_bridge_files(self):
        with tempfile.TemporaryDirectory() as d:
            ai = Path(d) / ".ai"
            ai.mkdir()
            (ai / "HANDOFF.md").write_text("bridge owned")
            (ai / "MASTER_PLAN.md").write_text("mine")
            r = devflow.init(d)
            self.assertEqual((ai / "HANDOFF.md").read_text(), "bridge owned")
            self.assertEqual((ai / "MASTER_PLAN.md").read_text(), "mine")
            self.assertIn("MASTER_PLAN.md", r["skipped_existing"])
            self.assertNotIn("HANDOFF.md", r["created"])
            self.assertEqual(sorted(r["bridge_owned_missing"]), ["DECISIONS.md", "PROJECT_CONTEXT.md"])
            self.assertTrue((ai / "tasks").is_dir())
            r2 = devflow.init(d)
            self.assertEqual(r2["created"], [])

    def test_all_templates_exist(self):
        for name in devflow.OWN_FILES + ("TASK.md", "DECISIONS.md", "HANDOFF.md"):
            self.assertTrue((ROOT / "templates" / name).exists(), name)


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = make_project()
        self.p = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def tier(self, **kw):
        add_task(self.p, "TASK-001", **kw)
        return devflow.route(self.p, "executor", "TASK-001")

    def test_defaults(self):
        self.assertEqual(devflow.route(self.p, "architect")["tier"], "strong")
        self.assertEqual(devflow.route(self.p, "reviewer")["tier"], "strong")
        self.assertEqual(self.tier()["tier"], "efficient")

    def test_complexity_6_7_stays_efficient_8_upgrades(self):
        self.assertEqual(self.tier(cx=7)["tier"], "efficient")
        self.assertEqual(self.tier(cx=8)["tier"], "strong")

    def test_high_risk_and_sensitive_upgrade(self):
        self.assertEqual(self.tier(risk="high")["tier"], "strong")
        self.assertEqual(self.tier(domains="[payments]")["tier"], "strong")
        r = self.tier(title="Rotate OAuth token storage")
        self.assertEqual(r["tier"], "strong")
        self.assertTrue(any("auth" in x for x in r["reasons"]))

    def test_architect_hint_only_upgrades(self):
        self.assertEqual(self.tier(tier="strong")["tier"], "strong")
        self.assertEqual(self.tier(risk="high", tier="efficient")["tier"], "strong")

    def test_user_override_wins_both_ways(self):
        add_task(self.p, "TASK-001", risk="high")
        self.assertEqual(devflow.route(self.p, "executor", "TASK-001", "efficient")["tier"], "efficient")
        add_task(self.p, "TASK-002")
        r = devflow.route(self.p, "executor", "TASK-002", "strong")
        self.assertEqual((r["tier"], r["reasons"]), ("strong", ["user override"]))

    def test_dispatch_uses_existing_alias_not_model_names(self):
        r = devflow.route(self.p, "architect")
        self.assertEqual(r["dispatch"]["via"], "claude-bridge")
        self.assertEqual(r["effort"], {"value": "high", "source": "auto"})
        self.assertIsNone(devflow.route(self.p, "executor", None)["effort"])
        blob = json.dumps(devflow.DEFAULTS) + (ROOT / "templates" / "config.yaml").read_text()
        for name in ("gpt-", "claude-opus", "claude-sonnet", "claude-fable"):
            self.assertNotIn(name, blob)

    def test_project_config_override(self):
        tmp = make_project("routing:\n  executor: strong\n")
        try:
            self.assertEqual(devflow.route(tmp.name, "executor")["tier"], "strong")
        finally:
            tmp.cleanup()


class StateMachineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = make_project()
        self.p = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_illegal_transitions_rejected(self):
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "EXECUTING")
        walk(self.p, ["PLANNING", "READY_TO_EXECUTE"])
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "DONE")
        self.assertEqual(devflow.load_state(self.p)["current_phase"], "READY_TO_EXECUTE")

    def test_happy_path_to_done(self):
        walk(self.p, ["PLANNING", "READY_TO_EXECUTE", "EXECUTING", "VALIDATING", "READY_FOR_REVIEW", "REVIEWING"])
        r = devflow.transition(self.p, "DONE")
        self.assertEqual(r["to"], "DONE")
        self.assertEqual(devflow.load_state(self.p)["project_status"], "done")

    def test_rework_loop_is_bounded_and_forces_blocked(self):
        walk(self.p, ["PLANNING", "READY_TO_EXECUTE", "EXECUTING", "VALIDATING", "READY_FOR_REVIEW"])
        seen = []
        for _ in range(10):
            devflow.transition(self.p, "REVIEWING")
            devflow.transition(self.p, "REWORK_REQUIRED")
            r = devflow.transition(self.p, "EXECUTING")
            seen.append(r["to"])
            if r["to"] == "BLOCKED":
                break
            walk(self.p, ["VALIDATING", "READY_FOR_REVIEW"])
        self.assertEqual(seen, ["EXECUTING", "EXECUTING", "EXECUTING", "BLOCKED"])
        self.assertEqual(r["stop_run"], "max_rework_cycles")

    def test_executor_retries_bounded(self):
        walk(self.p, ["PLANNING", "READY_TO_EXECUTE", "EXECUTING"])
        results = []
        for _ in range(5):
            devflow.transition(self.p, "VALIDATING")
            r = devflow.transition(self.p, "EXECUTING")
            results.append(r["to"])
            if r["to"] == "BLOCKED":
                break
        self.assertEqual(results, ["EXECUTING", "EXECUTING", "BLOCKED"])
        self.assertEqual(r["stop_run"], "max_executor_retries")

    def test_resolve_attempts_end_in_needs_user(self):
        walk(self.p, ["PLANNING", "READY_TO_EXECUTE", "EXECUTING"])
        r = devflow.transition(self.p, "BLOCKED", reason="needs schema change")
        self.assertFalse(r["needs_user"])  # strong RCA still allowed once
        self.assertEqual(devflow.next_action(self.p)["role"], "architect")
        devflow.transition(self.p, "EXECUTING")  # architect resolved
        r = devflow.transition(self.p, "BLOCKED", reason="still stuck")
        self.assertTrue(r["needs_user"])
        n = devflow.next_action(self.p)
        self.assertIsNone(n["role"])
        self.assertTrue(n["needs_user"])

    def test_total_executor_attempts_per_task_are_finite(self):
        """Adversarial driver: always rework, always 'resolve'. Must terminate with needs_user."""
        walk(self.p, ["PLANNING", "READY_TO_EXECUTE", "EXECUTING", "VALIDATING", "READY_FOR_REVIEW"])
        executions = 0
        for _ in range(200):
            phase = devflow.load_state(self.p)["current_phase"]
            if devflow.load_state(self.p).get("needs_user"):
                break
            if phase == "READY_FOR_REVIEW":
                devflow.transition(self.p, "REVIEWING")
            elif phase == "REVIEWING":
                devflow.transition(self.p, "REWORK_REQUIRED")
            elif phase == "REWORK_REQUIRED":
                r = devflow.transition(self.p, "EXECUTING")
                executions += r["to"] == "EXECUTING"
            elif phase == "EXECUTING":
                devflow.transition(self.p, "VALIDATING")
            elif phase == "VALIDATING":
                devflow.transition(self.p, "READY_FOR_REVIEW")
            elif phase == "BLOCKED":
                devflow.transition(self.p, "EXECUTING")
                executions += 1
        else:
            self.fail("workflow did not terminate")
        self.assertTrue(devflow.load_state(self.p)["needs_user"])
        self.assertLessEqual(executions, 12)

    def test_max_tasks_per_run_and_checkpoint(self):
        cfg = "automation:\n  max_tasks_per_run: 2\nreview:\n  checkpoint_every_n_tasks: 2\n"
        tmp = make_project(cfg)
        try:
            p = tmp.name
            add_task(p, "TASK-002")
            add_task(p, "TASK-003")
            walk(p, ["PLANNING", "READY_TO_EXECUTE", "EXECUTING", "VALIDATING", "READY_FOR_REVIEW", "REVIEWING"])
            r = devflow.transition(p, "READY_TO_EXECUTE", task="TASK-002")
            self.assertIsNone(r["stop_run"])
            walk(p, ["EXECUTING", "VALIDATING", "READY_FOR_REVIEW", "REVIEWING"])
            r = devflow.transition(p, "READY_TO_EXECUTE", task="TASK-003")
            self.assertEqual(r["stop_run"], "max_tasks_per_run")
            self.assertTrue(any("checkpoint" in n for n in r["notes"]))
            devflow.begin_run(p, "opus")
            self.assertEqual(devflow.load_state(p)["counters"]["tasks_this_run"], 0)
            self.assertEqual(devflow.load_state(p)["session"]["strong_mode"], "opus")
        finally:
            tmp.cleanup()

    def test_new_task_resets_loop_counters(self):
        add_task(self.p, "TASK-009")
        walk(self.p, ["PLANNING", "READY_TO_EXECUTE", "EXECUTING", "VALIDATING", "READY_FOR_REVIEW", "REVIEWING"])
        devflow.transition(self.p, "REWORK_REQUIRED")
        devflow.transition(self.p, "EXECUTING")
        walk(self.p, ["VALIDATING", "READY_FOR_REVIEW", "REVIEWING"])
        r = devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-009")
        self.assertEqual(r["counters"]["rework_cycles"], 0)

    def test_review_skip_needs_user_override(self):
        walk(self.p, ["PLANNING", "READY_TO_EXECUTE", "EXECUTING", "VALIDATING", "READY_FOR_REVIEW"])
        with self.assertRaises(devflow.DevflowError) as cm:
            devflow.transition(self.p, "DONE")
        self.assertIn("review_skip_requires_user_override", str(cm.exception))
        self.assertEqual(devflow.load_state(self.p)["current_phase"], "READY_FOR_REVIEW")
        r = devflow.transition(self.p, "DONE", user_override=True)
        self.assertTrue(any("review skipped" in n for n in r["notes"]))

    def test_review_skip_allowed_when_config_says_not_required(self):
        tmp = make_project("review:\n  required: false\n")
        try:
            walk(tmp.name, ["PLANNING", "READY_TO_EXECUTE", "EXECUTING", "VALIDATING", "READY_FOR_REVIEW"])
            r = devflow.transition(tmp.name, "DONE")
            self.assertEqual(r["to"], "DONE")
        finally:
            tmp.cleanup()


class CliTests(unittest.TestCase):
    def test_cli_status_and_error_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            script = str(ROOT / "scripts" / "devflow.py")
            bad = subprocess.run([sys.executable, script, "status", "--project", d], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)
            self.assertFalse(json.loads(bad.stdout)["ok"])
            subprocess.run([sys.executable, script, "init", "--project", d], check=True, capture_output=True)
            add_task(d, "TASK-001")
            ok = subprocess.run([sys.executable, script, "status", "--project", d], capture_output=True, text=True)
            out = json.loads(ok.stdout)
            self.assertEqual(ok.returncode, 0)
            self.assertEqual(out["phase"], "UNINITIALIZED")
            self.assertEqual(out["tasks_by_status"], {"pending": ["TASK-001"]})


class TaskStatusTests(unittest.TestCase):
    """Exercise saved files and fresh CLI reads, rather than an in-memory mirror."""

    def setUp(self):
        self.tmp = make_project()
        self.p = self.tmp.name
        self.ai = Path(self.p) / ".ai"
        add_task(self.p, "TASK-001")
        add_task(self.p, "TASK-002")
        devflow.transition(self.p, "PLANNING")

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, task="TASK-001"):
        return self.ai / "tasks" / (task + ".md")

    def task_status(self, task="TASK-001"):
        return devflow.read_task(self.p, task)[0]["status"]

    def reviewed(self, task="TASK-001"):
        devflow.transition(self.p, "READY_TO_EXECUTE", task=task)
        walk(self.p, ["EXECUTING", "VALIDATING", "READY_FOR_REVIEW", "REVIEWING"])

    def snapshot(self):
        return {p: p.read_bytes() for p in [self.ai / "STATE.yaml", *self.ai.joinpath("tasks").glob("*.md")]}

    def assert_snapshot(self, before):
        for p, text in before.items():
            self.assertEqual(p.read_bytes(), text, str(p))

    def test_happy_path_syncs_each_phase_and_fresh_cli_after_done(self):
        devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-001")
        self.assertEqual(self.task_status(), "ready")
        for phase, expected in [("EXECUTING", "executing"), ("VALIDATING", "validating"),
                                ("READY_FOR_REVIEW", "ready_for_review"), ("REVIEWING", "reviewing"),
                                ("DONE", "done")]:
            with self.subTest(phase=phase):
                devflow.transition(self.p, phase)
                self.assertEqual(self.task_status(), expected)
        cli = subprocess.run([sys.executable, str(ROOT / "scripts" / "devflow.py"), "status", "--project", self.p],
                             capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        out = json.loads(cli.stdout)
        self.assertEqual((out["phase"], out["current_task"]), ("DONE", "TASK-001"))
        self.assertEqual(out["tasks_by_status"], {"done": ["TASK-001"], "pending": ["TASK-002"]})

    def test_switch_completes_old_and_readies_new_task(self):
        self.reviewed()
        devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
        self.assertEqual(self.task_status("TASK-001"), "done")
        self.assertEqual(self.task_status("TASK-002"), "ready")
        self.assertEqual(devflow.load_state(self.p)["current_task"], "TASK-002")

    def test_review_pass_requires_distinct_next_task_when_current_is_real(self):
        self.reviewed()
        for next_task in (None, "TASK-001"):
            with self.subTest(next_task=next_task):
                before = self.snapshot()
                with self.assertRaises(devflow.DevflowError):
                    devflow.transition(self.p, "READY_TO_EXECUTE", task=next_task)
                self.assert_snapshot(before)

    def test_done_cannot_mark_an_unreviewed_next_task_done(self):
        self.reviewed()
        before = self.snapshot()
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "DONE", task="TASK-002")
        self.assert_snapshot(before)

    def test_new_work_after_done_preserves_completed_old_task(self):
        self.reviewed()
        walk(self.p, ["DONE", "PLANNING"])
        devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
        self.assertEqual(self.task_status("TASK-001"), "done")
        self.assertEqual(self.task_status("TASK-002"), "ready")

    def test_unrelated_task_cannot_inherit_an_in_progress_phase(self):
        devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-001")
        for phase in ("EXECUTING", "VALIDATING", "READY_FOR_REVIEW", "REVIEWING", "BLOCKED"):
            with self.subTest(phase=phase):
                before = self.snapshot()
                with self.assertRaises(devflow.DevflowError):
                    devflow.transition(self.p, phase, task="TASK-002")
                self.assert_snapshot(before)
                if phase != "BLOCKED":
                    devflow.transition(self.p, phase)

    def test_rework_handoff_must_reference_the_current_task(self):
        self.reviewed()
        before = self.snapshot()
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "REWORK_REQUIRED", task="TASK-002")
        self.assert_snapshot(before)

    def test_authorized_review_skip_completes_old_and_readies_new(self):
        devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-001")
        walk(self.p, ["EXECUTING", "VALIDATING", "READY_FOR_REVIEW"])
        devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002", user_override=True)
        self.assertEqual(self.task_status("TASK-001"), "done")
        self.assertEqual(self.task_status("TASK-002"), "ready")

    def test_status_edit_preserves_metadata_comments_body_and_newlines(self):
        original = ('---\r\nid: TASK-001\r\n# Keep this comment\r\nstatus: "pending"  # workflow status\r\n'
                    'risk: low\r\nmetadata:\r\n  status: nested-value\r\n  custom: "unchanged"\r\n'
                    'custom: yes\r\n---\r\n\r\n# Objective\r\nstatus: body-value\r\n中文正文\r\n')
        self.path().write_bytes(original.encode("utf-8"))
        devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-001")
        self.assertEqual(self.path().read_bytes(), original.replace('"pending"', '"ready"', 1).encode("utf-8"))
        self.assertEqual(devflow.status(self.p)["tasks_by_status"], {"ready": ["TASK-001"], "pending": ["TASK-002"]})

    def test_rework_review_completes_parent_and_child_before_next_task(self):
        self.reviewed()
        add_task(self.p, "REWORK-TASK-001-01")
        child = self.path("REWORK-TASK-001-01")
        child.write_text(child.read_text().replace("dependencies: []", "dependencies: []\nrework_of: TASK-001"))
        devflow.transition(self.p, "REWORK_REQUIRED", task="REWORK-TASK-001-01")
        self.assertEqual(self.task_status("TASK-001"), "rework_required")
        self.assertEqual(self.task_status("REWORK-TASK-001-01"), "rework_required")
        walk(self.p, ["EXECUTING", "VALIDATING", "READY_FOR_REVIEW", "REVIEWING"])
        devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
        self.assertEqual(self.task_status("TASK-001"), "done")
        self.assertEqual(self.task_status("REWORK-TASK-001-01"), "done")
        self.assertEqual(self.task_status("TASK-002"), "ready")

    def test_rework_review_done_completes_parent_and_child(self):
        self.reviewed()
        add_task(self.p, "REWORK-TASK-001-01")
        child = self.path("REWORK-TASK-001-01")
        child.write_text(child.read_text().replace("dependencies: []", "dependencies: []\nrework_of: TASK-001"))
        devflow.transition(self.p, "REWORK_REQUIRED", task="REWORK-TASK-001-01")
        walk(self.p, ["EXECUTING", "VALIDATING", "READY_FOR_REVIEW", "REVIEWING", "DONE"])
        self.assertEqual(self.task_status("TASK-001"), "done")
        self.assertEqual(self.task_status("REWORK-TASK-001-01"), "done")

    def test_rework_pass_cannot_select_its_completed_parent_as_next(self):
        self.reviewed()
        add_task(self.p, "REWORK-TASK-001-01")
        child = self.path("REWORK-TASK-001-01")
        child.write_text(child.read_text().replace("dependencies: []", "dependencies: []\nrework_of: TASK-001"))
        devflow.transition(self.p, "REWORK_REQUIRED", task="REWORK-TASK-001-01")
        walk(self.p, ["EXECUTING", "VALIDATING", "READY_FOR_REVIEW", "REVIEWING"])
        before = self.snapshot()
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-001")
        self.assert_snapshot(before)

    def test_counter_override_syncs_blocked_instead_of_requested_executing(self):
        self.reviewed()
        devflow.transition(self.p, "REWORK_REQUIRED")
        self.assertEqual(self.task_status(), "rework_required")
        cfg = self.ai / "config.yaml"
        cfg.write_text("automation:\n  max_rework_cycles: 0\n")
        result = devflow.transition(self.p, "EXECUTING")
        self.assertEqual((result["to"], result["stop_run"]), ("BLOCKED", "max_rework_cycles"))
        self.assertEqual(self.task_status(), "blocked")
        devflow.transition(self.p, "EXECUTING")
        self.assertEqual(self.task_status(), "executing")

    def test_executor_retry_limit_syncs_blocked(self):
        devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-001")
        walk(self.p, ["EXECUTING", "VALIDATING"])
        (self.ai / "config.yaml").write_text("automation:\n  max_executor_retries: 0\n")
        result = devflow.transition(self.p, "EXECUTING")
        self.assertEqual((result["to"], result["stop_run"]), ("BLOCKED", "max_executor_retries"))
        self.assertEqual(self.task_status(), "blocked")

    def test_missing_next_task_fails_without_writing_any_files(self):
        self.reviewed()
        before = self.snapshot()
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-MISSING")
        self.assert_snapshot(before)

    def test_malformed_next_task_fails_without_completing_current(self):
        self.reviewed()
        for bad in ["missing front matter", "---\nid: TASK-WRONG\nstatus: pending\n---\n",
                    "---\nid: TASK-002\n---\n", "---\nid: TASK-002\nstatus: []\n---\n",
                    "---\nid: TASK-002\nstatus: ready\nstatus: pending\n---\n"]:
            with self.subTest(front_matter=bad):
                self.path("TASK-002").write_text(bad)
                before = self.snapshot()
                with self.assertRaises(devflow.DevflowError):
                    devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
                self.assert_snapshot(before)

    def test_current_task_is_validated_before_any_write(self):
        self.reviewed()
        self.path().write_text("broken task")
        before = self.snapshot()
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
        self.assert_snapshot(before)

    def test_malformed_closing_delimiter_is_rejected_before_completing_old_task(self):
        self.reviewed()
        self.path("TASK-002").write_text("---\nid: TASK-002\nstatus: pending\n---junk\n")
        before = self.snapshot()
        try:
            devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
        except devflow.DevflowError:
            pass
        except Exception as exc:
            self.fail("malformed tasks must return a validation error before writes: " + repr(exc))
        else:
            self.fail("malformed task closing delimiter must be rejected")
        self.assert_snapshot(before)

    def test_all_status_edits_are_prepared_before_any_task_is_written(self):
        self.reviewed()
        before = self.snapshot()
        prepare = devflow.task_with_status
        def fail_next(text, status):
            if "id: TASK-002\n" in text:
                raise devflow.DevflowError("simulated status preparation failure")
            return prepare(text, status)
        with mock.patch.object(devflow, "task_with_status", side_effect=fail_next):
            with self.assertRaises(devflow.DevflowError):
                devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
        self.assert_snapshot(before)

    def test_invalid_rework_parent_fails_before_writing(self):
        self.reviewed()
        child = self.path("TASK-002")
        child.write_text(child.read_text().replace("dependencies: []", "dependencies: []\nrework_of: TASK-MISSING"))
        before = self.snapshot()
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "REWORK_REQUIRED", task="TASK-002")
        self.assert_snapshot(before)

    def test_outside_task_paths_and_symlinks_are_rejected(self):
        self.reviewed()
        outside = self.ai / "outside.md"
        outside.write_text(TASK.format(id="outside", title="Outside", risk="low", cx=1, domains="[]", tier="efficient"))
        before = self.snapshot()
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "READY_TO_EXECUTE", task="../outside")
        self.assert_snapshot(before)
        self.path("TASK-002").unlink()
        self.path("TASK-002").symlink_to(outside)
        before = self.snapshot()
        with self.assertRaises(devflow.DevflowError):
            devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
        self.assert_snapshot(before)

    def test_state_write_failure_rolls_back_all_task_updates(self):
        self.reviewed()
        before = self.snapshot()
        write = devflow.atomic_write
        def fail_state(path, text):
            if path.name == "STATE.yaml":
                raise OSError("simulated STATE write failure")
            return write(path, text)
        with mock.patch.object(devflow, "atomic_write", side_effect=fail_state):
            try:
                devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
            except devflow.DevflowError:
                pass
            except OSError as exc:
                self.fail("write failures must produce a DevflowError: " + str(exc))
            else:
                self.fail("a failed STATE write must not report success")
        self.assert_snapshot(before)

    def test_second_task_write_failure_rolls_back_first_task(self):
        self.reviewed()
        before = self.snapshot()
        write = devflow.atomic_write
        def fail_next(path, text):
            if path.name == "TASK-002.md":
                raise OSError("simulated next-task write failure")
            return write(path, text)
        with mock.patch.object(devflow, "atomic_write", side_effect=fail_next):
            with self.assertRaises(devflow.DevflowError):
                devflow.transition(self.p, "READY_TO_EXECUTE", task="TASK-002")
        self.assert_snapshot(before)


class SkillStructureTests(unittest.TestCase):
    def test_every_referenced_path_exists(self):
        import re
        text = (ROOT / "SKILL.md").read_text()
        paths = set(re.findall(r"`((?:roles|references|templates|scripts)/[A-Za-z0-9_./-]+?)(?:#[^`]*)?`", text))
        self.assertTrue(paths)
        for rel in paths:
            self.assertTrue((ROOT / rel.rstrip("/")).exists(), rel)

    def test_frontmatter(self):
        text = (ROOT / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\nname: dev-orchestrator\ndescription: "))


if __name__ == "__main__":
    unittest.main()
