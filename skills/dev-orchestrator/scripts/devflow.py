#!/usr/bin/env python3
"""Deterministic helper for the dev-orchestrator skill.

It never calls a model and never builds a router. It only:
  init        create missing .ai/ workflow files from templates (never overwrites)
  status      summarize STATE.yaml and tasks
  route       choose a model tier for a role/task (tier names only, no model names)
  transition  apply a legal state-machine move and enforce loop limits
  begin-run   reset the per-run task counter

Python 3.9+, standard library only. YAML support is a small subset
(nested maps, scalar lists, scalars) which is all STATE/config/task files use.
"""
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Australia/Melbourne")
except Exception:  # pragma: no cover
    TZ = None

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_ROOT / "templates"

# Files created by this skill. PROJECT_CONTEXT/DECISIONS/HANDOFF belong to claude-bridge
# (its `init` is idempotent) and are deliberately not created here.
OWN_FILES = ("STATE.yaml", "config.yaml", "MASTER_PLAN.md", "ARCHITECTURE.md",
             "PROGRESS.md", "BLOCKERS.md", "VALIDATION.md")
BRIDGE_FILES = ("PROJECT_CONTEXT.md", "DECISIONS.md", "HANDOFF.md")

PHASES = ("UNINITIALIZED", "PLANNING", "READY_TO_EXECUTE", "EXECUTING", "VALIDATING",
          "READY_FOR_REVIEW", "REVIEWING", "REWORK_REQUIRED", "BLOCKED", "DONE")
TRANSITIONS = {
    "UNINITIALIZED": {"PLANNING"},
    "PLANNING": {"READY_TO_EXECUTE", "BLOCKED"},
    "READY_TO_EXECUTE": {"EXECUTING", "PLANNING", "BLOCKED"},
    "EXECUTING": {"VALIDATING", "BLOCKED"},
    "VALIDATING": {"READY_FOR_REVIEW", "EXECUTING", "BLOCKED"},
    "READY_FOR_REVIEW": {"REVIEWING", "READY_TO_EXECUTE", "DONE"},  # last two = skip review, guarded
    "REVIEWING": {"READY_TO_EXECUTE", "DONE", "REWORK_REQUIRED", "BLOCKED"},
    "REWORK_REQUIRED": {"EXECUTING", "BLOCKED"},
    "BLOCKED": {"PLANNING", "READY_TO_EXECUTE", "EXECUTING"},
    "DONE": {"PLANNING"},
}
PHASE_ROLE = {
    "UNINITIALIZED": "architect", "PLANNING": "architect", "READY_TO_EXECUTE": "executor",
    "EXECUTING": "executor", "VALIDATING": "validator", "READY_FOR_REVIEW": "reviewer",
    "REVIEWING": "reviewer", "REWORK_REQUIRED": "executor", "BLOCKED": "architect",
    "DONE": None,
}
TASK_STATUS = {
    "READY_TO_EXECUTE": "ready", "EXECUTING": "executing", "VALIDATING": "validating",
    "READY_FOR_REVIEW": "ready_for_review", "REVIEWING": "reviewing",
    "REWORK_REQUIRED": "rework_required", "BLOCKED": "blocked", "DONE": "done",
}
DEFAULTS = {
    "routing": {"architect": "strong", "executor": "efficient", "reviewer": "strong"},
    "tiers": {"strong": {"via": "claude-bridge", "bridge_mode": "ask"},
              "efficient": {"via": "native"}},
    "automation": {"enabled": True, "auto_continue_low_risk": True, "max_tasks_per_run": 5,
                   "max_executor_retries": 2, "max_rework_cycles": 3,
                   "max_resolve_attempts": 1, "stop_on_high_risk_change": True},
    "review": {"required": True, "checkpoint_every_n_tasks": 3},
    "risk": {"force_strong_for": ["auth", "permissions", "payments", "encryption",
                                   "schema-migration", "destructive-data-change",
                                   "production-infra", "security", "concurrency"]},
}
# Conservative safety net on top of Architect-assigned `domains:` tags.
SENSITIVE_KEYWORDS = {
    "auth": ("auth", "login", "session token", "oauth", "jwt"),
    "permissions": ("permission", "rbac", "acl", "role-based"),
    "payments": ("payment", "billing", "invoice", "refund", "checkout"),
    "encryption": ("encrypt", "decrypt", "crypto", "secret", "kms"),
    "schema-migration": ("migration", "schema change", "alter table"),
    "destructive-data-change": ("delete data", "drop table", "purge", "truncate"),
    "production-infra": ("deploy", "terraform", "production infra", "kubernetes"),
    "concurrency": ("concurren", "race condition", "lock", "idempot"),
}


class DevflowError(Exception):
    pass


# ---------------------------------------------------------------- YAML subset

def _strip_comment(line):
    if line.lstrip().startswith("#"):
        return ""
    if '"' in line or "'" in line:
        return line.rstrip()
    return re.sub(r"\s+#.*$", "", line).rstrip()


def _scalar(text):
    s = text.strip()
    if s in ("", "~", "null", "Null"):
        return None
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if s.startswith("[") and s.endswith("]"):
        return [_scalar(x) for x in s[1:-1].split(",") if x.strip()]
    return s


def parse_yaml(text):
    rows = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if line.strip():
            rows.append((len(line) - len(line.lstrip(" ")), line.strip()))
    if not rows:
        return {}
    value, pos = _block(rows, 0, rows[0][0])
    if pos != len(rows):
        raise DevflowError("yaml_parse_error near: " + rows[pos][1])
    return value


def _block(rows, i, indent):
    if rows[i][1].startswith("- ") or rows[i][1] == "-":
        items = []
        while i < len(rows) and rows[i][0] == indent and (rows[i][1].startswith("- ") or rows[i][1] == "-"):
            body = rows[i][1][1:].strip()
            if re.match(r"^[^\s:][^:]*:(\s|$)", body):
                raise DevflowError("list_of_maps_unsupported: " + body)
            items.append(_scalar(body))
            i += 1
        return items, i
    result = {}
    while i < len(rows) and rows[i][0] == indent:
        m = re.match(r"^([^\s:][^:]*?):(?:\s+(.*))?$", rows[i][1])
        if not m:
            raise DevflowError("yaml_parse_error near: " + rows[i][1])
        key, rest = m.group(1), m.group(2)
        i += 1
        if rest not in (None, ""):
            result[key] = _scalar(rest)
        elif i < len(rows) and (rows[i][0] > indent or (rows[i][0] == indent and rows[i][1].startswith("-"))):
            result[key], i = _block(rows, i, rows[i][0])
        else:
            result[key] = None
    return result, i


def _fmt(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    s = str(v)
    if s == "" or s != s.strip() or re.search(r":\s|\s#", s) or s[0] in "[{&*!|>'\"%@`-" and not re.fullmatch(r"-?\d+", s):
        return json.dumps(s, ensure_ascii=False)
    return s


def dump_yaml(data, indent=0):
    pad = "  " * indent
    out = []
    for k, v in data.items():
        if isinstance(v, dict):
            out.append(pad + k + ":")
            out.extend(dump_yaml(v, indent + 1))
        elif isinstance(v, list):
            if not v:
                out.append(pad + k + ": []")
            else:
                out.append(pad + k + ":")
                out.extend(pad + "  - " + _fmt(x) for x in v)
        else:
            out.append(pad + k + ": " + _fmt(v))
    return out


# --------------------------------------------------------------------- files

def now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def ai_dir(project):
    p = Path(project).expanduser().resolve()
    if not p.is_dir():
        raise DevflowError("project_not_a_directory: " + str(p))
    return p / ".ai"


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(project):
    path = ai_dir(project) / "config.yaml"
    user = parse_yaml(path.read_text(encoding="utf-8")) if path.exists() else {}
    return merge(DEFAULTS, user)


def load_state(project):
    path = ai_dir(project) / "STATE.yaml"
    if not path.exists():
        raise DevflowError("state_missing: run `devflow.py init --project DIR` first")
    state = parse_yaml(path.read_text(encoding="utf-8"))
    state["current_phase"] = str(state.get("current_phase", "UNINITIALIZED")).upper()
    if state["current_phase"] not in PHASES:
        raise DevflowError("unknown_phase: " + state["current_phase"])
    state.setdefault("counters", {})
    for key in ("rework_cycles", "executor_retries", "resolve_attempts", "tasks_this_run",
                "tasks_since_checkpoint"):
        state["counters"][key] = int(state["counters"].get(key) or 0)
    return state


def save_state(project, state):
    state["updated_at"] = now()
    body = "# Managed by dev-orchestrator scripts/devflow.py. Prefer `transition` over hand edits.\n"
    atomic_write(ai_dir(project) / "STATE.yaml", body + "\n".join(dump_yaml(state)) + "\n")


def read_task(project, task_id):
    path = ai_dir(project) / "tasks" / (task_id + ".md")
    if not path.exists():
        raise DevflowError("task_missing: " + str(path))
    return parse_task(path.read_text(encoding="utf-8"))


def parse_task(text):
    m = re.match(r"^---\n(.*?)\n---(?:\n|\Z)(.*)$", text, re.S)
    if not m:
        raise DevflowError("task_front_matter_missing")
    # A preserved quoted scalar can also have a comment; remove it only from the parse input.
    front = re.sub(r'''^([ \t]*[^:\n]+:[ \t]*(?:"[^"\n]*"|'[^'\n]*'))[ \t]+\#.*$''',
                   r"\1", m.group(1), flags=re.M)
    return parse_yaml(front), m.group(2)


def transition_tasks(project, task_ids):
    """Validate every referenced task before preparing any writes; retain exact text."""
    root = ai_dir(project) / "tasks"
    if root.resolve().parent != ai_dir(project).resolve():
        raise DevflowError("task_directory_outside_project: " + str(root))
    tasks, visiting = {}, set()

    def load(task_id):
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", task_id):
            raise DevflowError("invalid_task_id: " + str(task_id))
        if task_id in visiting:
            raise DevflowError("task_rework_cycle: " + task_id)
        if task_id in tasks:
            return
        path = root / (task_id + ".md")
        if path.resolve().parent != root.resolve():
            raise DevflowError("task_outside_directory: " + str(path))
        if not path.is_file():
            raise DevflowError("task_missing: " + str(path))
        try:
            text = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise DevflowError("task_read_failed: %s: %s" % (path, exc)) from exc
        normalized = text.replace("\r\n", "\n")
        meta, _ = parse_task(normalized)
        if not isinstance(meta, dict):
            raise DevflowError("task_front_matter_not_mapping: " + task_id)
        front = re.match(r"^---\n(.*?)\n---", normalized, re.S).group(1)
        # Only these top-level fields are owned/used here; reject duplicates and malformed scalars.
        for name in ("id", "status", "rework_of"):
            lines = re.findall(r"^" + name + r":[ \t]*(.*)$", front, re.M)
            if len(lines) > 1 or (not lines and name != "rework_of"):
                raise DevflowError("task_field_missing_or_duplicate: %s: %s" % (task_id, name))
            if not lines:
                continue
            match = re.fullmatch(r'''("[^"\n]*"|'[^'\n]*'|[^#'"\n]*?)([ \t]+\#.*)?''', lines[0])
            if not match:
                raise DevflowError("task_invalid_field: %s: %s" % (task_id, name))
            meta[name] = _scalar(match.group(1).strip())
        if meta.get("id") != task_id:
            raise DevflowError("task_id_mismatch: " + task_id)
        if meta.get("status") not in ("pending", *TASK_STATUS.values()):
            raise DevflowError("task_invalid_status: " + task_id)
        visiting.add(task_id)
        parent = meta.get("rework_of")
        if parent is not None:
            load(parent)
        visiting.remove(task_id)
        tasks[task_id] = {"path": path, "text": text, "parent": parent}

    for task_id in task_ids:
        if task_id is not None:
            load(task_id)
    return tasks


def task_with_status(text, status):
    """Replace just the top-level front-matter scalar, preserving quotes/comments/CRLF/body."""
    end = re.search(r"\r?\n---(?:\r?\n|$)", text[4:])
    front_end = 4 + end.start()
    front, rest = text[:front_end], text[front_end:]
    pattern = r'''^(status:[ \t]*)("[^"\r\n]*"|'[^'\r\n]*'|[^#\r\n]*?)([ \t]*(?:\#.*)?\r?)$'''

    def replace(match):
        value = match.group(2).strip()
        quote = value[0] if value and value[0] in "\"'" else ""
        return match.group(1) + quote + status + quote + match.group(3)

    return re.sub(pattern, replace, front, count=1, flags=re.M) + rest


def save_transition(project, state, tasks, updates):
    """Rollback ordinary failed writes. This is not multi-file crash atomicity."""
    prepared = []
    for task_id, status in updates.items():
        item = tasks[task_id]
        changed = task_with_status(item["text"], status)
        if changed != item["text"]:
            prepared.append((item, changed))
    written = []
    try:
        for item, changed in prepared:
            atomic_write(item["path"], changed)
            written.append(item)
        save_state(project, state)
    except OSError as exc:
        rollback_errors = []
        for item in reversed(written):
            try:
                atomic_write(item["path"], item["text"])
            except OSError as rollback_exc:
                rollback_errors.append("%s: %s" % (item["path"], rollback_exc))
        detail = "; rollback_failed: " + "; ".join(rollback_errors) if rollback_errors else "; tasks rolled back"
        raise DevflowError("transition_write_failed: " + str(exc) + detail) from exc


# -------------------------------------------------------------------- routing

def sensitive_domains(meta, body, forced):
    tags = [str(t).lower() for t in (meta.get("domains") or [])]
    hits = [t for t in tags if t in forced]
    head = (str(meta.get("title", "")) + "\n" + _section(body, "Objective")).lower()
    for domain, words in SENSITIVE_KEYWORDS.items():
        if domain in forced and domain not in hits and any(w in head for w in words):
            hits.append(domain)
    return hits


def _section(body, name):
    m = re.search(r"^#\s+" + re.escape(name) + r"\s*\n(.*?)(?=^#\s|\Z)", body, re.S | re.M)
    return m.group(1) if m else ""


def route(project, role, task_id=None, force=None):
    """Return the tier decision. Only tier names; the model is resolved by the existing router."""
    cfg = load_config(project)
    if role not in ("architect", "executor", "reviewer"):
        raise DevflowError("unknown_role: " + role)
    tier, reasons, meta, body = cfg["routing"][role], ["default routing for " + role], {}, ""
    if task_id:
        meta, body = read_task(project, task_id)
    if force in ("strong", "efficient"):
        tier, reasons = force, ["user override"]
    elif role == "executor" and task_id:
        risk = str(meta.get("risk", "medium")).lower()
        complexity = int(meta.get("complexity") or 5)
        hits = sensitive_domains(meta, body, cfg["risk"]["force_strong_for"])
        if risk == "high":
            tier, reasons = "strong", ["risk=high"]
        elif complexity >= 8:
            tier, reasons = "strong", ["complexity=%d>=8" % complexity]
        elif hits:
            tier, reasons = "strong", ["sensitive domain: " + ", ".join(hits)]
        elif str(meta.get("executor_tier", "")).lower() == "strong":
            tier, reasons = "strong", ["Architect set executor_tier=strong"]
        else:
            reasons = ["complexity=%d, risk=%s, no sensitive domain" % (complexity, risk)]
    result = {"role": role, "tier": tier, "reasons": reasons, "task": task_id,
              "dispatch": cfg["tiers"].get(tier, {"via": "unknown"})}
    result["effort"] = suggest_effort(role, meta, tier, reasons)
    return result


def suggest_effort(role, meta, tier, reasons):
    """Bridge effort request for strong tier. Auto choice is only medium|high (bridge rule)."""
    if tier != "strong":
        return None
    risk = str(meta.get("risk", "")).lower()
    complexity = int(meta.get("complexity") or 0)
    high = role == "architect" or risk == "high" or complexity >= 7 or any("sensitive" in r for r in reasons)
    return {"value": "high" if high else "medium", "source": "auto"}


# --------------------------------------------------------------- state machine

def transition(project, to_phase, task=None, reason="", user_override=False):
    cfg, state = load_config(project), load_state(project)
    auto, c = cfg["automation"], state["counters"]
    frm, to = state["current_phase"], to_phase.upper()
    if to not in PHASES:
        raise DevflowError("unknown_phase: " + to)
    if to not in TRANSITIONS[frm]:
        raise DevflowError("illegal_transition: %s -> %s (allowed: %s)" % (frm, to, ", ".join(sorted(TRANSITIONS[frm]))))
    current = state.get("current_task")
    tasks = transition_tasks(project, (current, task))
    if task is not None and task != current:
        if to not in ("READY_TO_EXECUTE", "REWORK_REQUIRED"):
            raise DevflowError("task_switch_not_allowed_for_phase: " + to)
        if to == "REWORK_REQUIRED" and (not current or tasks[task]["parent"] != current):
            raise DevflowError("rework_task_must_reference_current_task: " + task)
    notes, stop = [], None
    if frm == "REWORK_REQUIRED" and to == "EXECUTING":
        c["rework_cycles"] += 1
        if c["rework_cycles"] > int(auto["max_rework_cycles"]):
            to, stop = "BLOCKED", "max_rework_cycles"
    if frm == "VALIDATING" and to == "EXECUTING":
        c["executor_retries"] += 1
        if c["executor_retries"] > int(auto["max_executor_retries"]):
            to, stop = "BLOCKED", "max_executor_retries"
    if frm == "VALIDATING" and to == "READY_FOR_REVIEW":
        c["executor_retries"] = 0
    if frm == "BLOCKED":
        c["resolve_attempts"] += 1
        c["rework_cycles"] = c["executor_retries"] = 0
        state["needs_user"] = False
    if to == "BLOCKED":
        if c["resolve_attempts"] >= int(auto["max_resolve_attempts"]):
            state["needs_user"] = True
            notes.append("strong-model root-cause attempts exhausted: report to user")
        state["blocked_reason"] = stop or reason or "unspecified"
    skipped_review = frm == "READY_FOR_REVIEW" and to in ("READY_TO_EXECUTE", "DONE")
    if skipped_review:
        if not (user_override or not cfg["review"]["required"]):
            raise DevflowError("review_skip_requires_user_override")
        notes.append("review skipped by " + ("user override" if user_override else "config review.required=false")
                     + ": record it in HANDOFF.md and PROGRESS.md")
    completed = (frm == "REVIEWING" or skipped_review) and to in ("READY_TO_EXECUTE", "DONE")
    completed_ids = []
    if completed and current:
        parent = current
        while parent is not None:
            completed_ids.append(parent)
            parent = tasks[parent]["parent"]
        if to == "READY_TO_EXECUTE" and (not task or task in completed_ids):
            raise DevflowError("next_task_must_be_distinct: use --task NEXT outside completed rework ancestry or transition to DONE")
    if completed:
        c["tasks_this_run"] += 1
        c["tasks_since_checkpoint"] += 1
        every = int(cfg["review"]["checkpoint_every_n_tasks"] or 0)
        if every and c["tasks_since_checkpoint"] >= every and to == "READY_TO_EXECUTE":
            notes.append("checkpoint due: run a strong Reviewer over the combined diff before continuing")
            c["tasks_since_checkpoint"] = 0
        if to == "READY_TO_EXECUTE" and c["tasks_this_run"] >= int(auto["max_tasks_per_run"]):
            stop = "max_tasks_per_run"
    if to == "READY_TO_EXECUTE" and task and task != state.get("current_task"):
        state["current_task"] = task
        c["rework_cycles"] = c["executor_retries"] = c["resolve_attempts"] = 0
    elif task:
        state["current_task"] = task
    state["current_phase"] = to
    state["last_role"] = PHASE_ROLE.get(frm) or state.get("last_role")
    state["next_role"] = PHASE_ROLE.get(to)
    state["project_status"] = "done" if to == "DONE" else "blocked" if to == "BLOCKED" else "active"
    if to != "BLOCKED":
        state["blocked_reason"] = None
    updates = {}
    if completed_ids:
        updates.update((task_id, "done") for task_id in completed_ids)
    elif current and task and current != task and to == "REWORK_REQUIRED":
        updates[current] = "rework_required"
    selected = state.get("current_task")
    if selected and to in TASK_STATUS:
        updates[selected] = TASK_STATUS[to]
    save_transition(project, state, tasks, updates)
    return {"from": frm, "to": to, "stop_run": stop, "needs_user": bool(state.get("needs_user")),
            "counters": c, "notes": notes}


def begin_run(project, strong_mode=None):
    state = load_state(project)
    state["counters"]["tasks_this_run"] = 0
    if strong_mode:
        if strong_mode not in ("opus", "sonnet", "default"):
            raise DevflowError("strong_mode_must_be_opus_sonnet_or_default")
        state.setdefault("session", {})["strong_mode"] = strong_mode
    save_state(project, state)
    return {"tasks_this_run": 0, "strong_mode": (state.get("session") or {}).get("strong_mode")}


def next_action(project):
    cfg, state = load_config(project), load_state(project)
    phase = state["current_phase"]
    role = PHASE_ROLE[phase]
    result = {"phase": phase, "role": role, "task": state.get("current_task"),
              "needs_user": bool(state.get("needs_user")), "automation_enabled": bool(cfg["automation"]["enabled"])}
    if phase == "BLOCKED":
        result["role"] = None if state.get("needs_user") else "architect"
        result["action"] = "report blocker to user" if state.get("needs_user") else "strong-model root-cause analysis"
    return result


# ------------------------------------------------------------------- commands

def init(project, dry_run=False):
    ai = ai_dir(project)
    created, skipped = [], []
    for name in OWN_FILES:
        target = ai / name
        if target.exists():
            skipped.append(name)
            continue
        created.append(name)
        if not dry_run:
            text = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
            if name == "STATE.yaml":
                text = text.replace("{{UPDATED_AT}}", now())
            atomic_write(target, text)
    if not (ai / "tasks").exists():
        created.append("tasks/")
        if not dry_run:
            (ai / "tasks").mkdir(parents=True, exist_ok=True)
    missing_bridge = [n for n in BRIDGE_FILES if not (ai / n).exists()]
    return {"project": str(ai.parent), "created": created, "skipped_existing": skipped,
            "bridge_owned_missing": missing_bridge, "dry_run": dry_run,
            "next": ("run `claude-bridge init --project DIR` (needs user authorization to add files) "
                     "before any strong-tier call") if missing_bridge else "ready"}


def status(project):
    state, ai = load_state(project), ai_dir(project)
    tasks = {}
    for path in sorted((ai / "tasks").glob("*.md")):
        try:
            meta, _ = parse_task(path.read_text(encoding="utf-8"))
            tasks[path.stem] = {"status": meta.get("status"), "risk": meta.get("risk"),
                                "complexity": meta.get("complexity")}
        except DevflowError as e:
            tasks[path.stem] = {"status": "INVALID", "error": str(e)}
    by = {}
    for tid, t in tasks.items():
        by.setdefault(str(t["status"]), []).append(tid)
    return {"phase": state["current_phase"], "milestone": state.get("current_milestone"),
            "current_task": state.get("current_task"), "last_role": state.get("last_role"),
            "next_role": state.get("next_role"), "counters": state["counters"],
            "needs_user": bool(state.get("needs_user")), "blocked_reason": state.get("blocked_reason"),
            "tasks_by_status": by, "updated_at": state.get("updated_at")}


def main(argv=None):
    p = argparse.ArgumentParser(prog="devflow.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("init", "status", "next", "begin-run", "route", "transition"):
        s = sub.add_parser(name)
        s.add_argument("--project", required=True)
        if name == "init":
            s.add_argument("--dry-run", action="store_true")
        if name == "begin-run":
            s.add_argument("--strong-mode", choices=("opus", "sonnet", "default"))
        if name == "route":
            s.add_argument("--role", required=True, choices=("architect", "executor", "reviewer"))
            s.add_argument("--task")
            s.add_argument("--force", choices=("strong", "efficient"))
        if name == "transition":
            s.add_argument("--to", required=True)
            s.add_argument("--task")
            s.add_argument("--reason", default="")
            s.add_argument("--user-override", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.cmd == "init":
            out = init(a.project, a.dry_run)
        elif a.cmd == "status":
            out = status(a.project)
        elif a.cmd == "next":
            out = next_action(a.project)
        elif a.cmd == "begin-run":
            out = begin_run(a.project, a.strong_mode)
        elif a.cmd == "route":
            out = route(a.project, a.role, a.task, a.force)
        else:
            out = transition(a.project, a.to, a.task, a.reason, a.user_override)
    except DevflowError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, **out}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
