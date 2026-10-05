#!/usr/bin/env python3
"""Subscription-only Claude Code subprocess bridge. Python 3.9+, stdlib only.

No authentication material is read by this program. Authentication is checked
with the official CLI's JSON status command and only three fields are emitted.
No inference is made by init, doctor, or run --dry-run. Successful CLI execution
does not independently verify model-reported tests or prove subscription billing.
"""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import posixpath
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

BASE = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = BASE / "config" / "runtime.json"
MANAGED_SETTINGS_DIR = Path("/Library/Application Support/ClaudeCode")
EFFORT_ENV = "CLAUDE_CODE_EFFORT_LEVEL"
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
EFFORT_AUDIT_FIELDS = ("requested_effort", "effort_source", "effort_reason", "effective_effort", "effort_policy")
ROUTE_ENV = {
    "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_BASE",
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
    "ANTHROPIC_BEDROCK_BASE_URL", "CLAUDE_CODE_API_KEY", "CLAUDE_CODE_API_BASE_URL",
    "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_SIMPLE", "CLAUDE_CONFIG_DIR",
    "AWS_BEARER_TOKEN_BEDROCK", "ANTHROPIC_VERTEX_BASE_URL",
    "ANTHROPIC_API_KEY_FILE_DESCRIPTOR", "ANTHROPIC_FOUNDRY_API_KEY",
    "ANTHROPIC_FOUNDRY_BASE_URL", "ANTHROPIC_FOUNDRY_RESOURCE", "ANTHROPIC_CUSTOM_HEADERS",
    # Official auth precedence/env-vars references: profiles/federation and
    # cloud credentials can outrank the account's /login credential.
    "ANTHROPIC_PROFILE", "ANTHROPIC_CONFIG_DIR", "ANTHROPIC_FEDERATION_RULE_ID",
    "ANTHROPIC_ORGANIZATION_ID", "ANTHROPIC_WORKSPACE_ID", "ANTHROPIC_SERVICE_ACCOUNT_ID",
    "ANTHROPIC_IDENTITY_TOKEN", "ANTHROPIC_IDENTITY_TOKEN_FILE", "ANTHROPIC_AWS_API_KEY",
    "ANTHROPIC_AWS_BASE_URL", "ANTHROPIC_AWS_WORKSPACE_ID", "ANTHROPIC_FOUNDRY_AUTH_TOKEN",
    "ANTHROPIC_AUTH_CUSTOM_HEADERS", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_FABLE_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL", "ANTHROPIC_CUSTOM_MODEL_OPTION",
    "ANTHROPIC_BEDROCK_MANTLE_BASE_URL", "ANTHROPIC_VERTEX_PROJECT_ID",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_BEDROCK_MANTLE",
    "CLAUDE_CODE_SUBAGENT_MODEL",
}
ROUTE_SETTINGS = {"apiKeyHelper", "awsAuthRefresh", "awsCredentialExport", "forceLoginGatewayUrl"}
RESULT_FIELDS = ("Task", "Summary", "FilesChanged", "Tests", "Decisions",
                 "RemainingIssues", "RecommendedNextStep")
LIST_FIELDS = {"FilesChanged", "Tests", "Decisions", "RemainingIssues"}
SCHEMA = {
    "type": "object", "properties": {
        key: ({"type": "array", "items": {"type": "string"}} if key in LIST_FIELDS
              else {"type": "string"}) for key in RESULT_FIELDS
    }, "required": list(RESULT_FIELDS), "additionalProperties": False,
}
TEMPLATES = {
    "PROJECT_CONTEXT.md": """# Project Context

## Project Goal
Fill in the current project goal before handing off work.

## Tech Stack
Unknown; inspect the actual project.

## Architecture
Unknown; inspect the actual project.

## Constraints
- Use native subscriptions; no API fallback or additional usage purchases.
- Preserve existing files, instructions, and normal Claude Code permissions.
- Work serially; do not modify files concurrently with GPT.
- No destructive Git commands or automatic commits.

## Common Commands
Unknown; inspect the actual project and independently verify tests.
""",
    "DECISIONS.md": "# Architecture Decisions\n\nRecord date, decision, reason, and alternatives rejected.\n",
    "HANDOFF.md": """# AI Handoff

## Current Goal
Awaiting a project task.

## Current Status
Context initialized. Claude inference has not been verified.

## Last Agent
GPT

## Work Completed
Context initialization only.

## Files Changed
.ai context files.

## Tests
Unknown; no project tests have been run by Claude.

## Decisions Made
Native subscription authentication only; no API fallback.

## Known Issues
Pending authentication, usage-source, permissions, and live acceptance checks.

## Next Recommended Action
Run doctor, confirm subscription usage credits are disabled, then explicitly invoke a task.
""",
}
REQUIRED_FLAGS = ("--print", "--output-format", "--model", "--resume", "--max-turns",
                  "--json-schema", "--permission-mode", "--permission-prompts", "--effort")
TASK_LIMIT = 32000
TASK_FILE_LIMIT = 128000
CONSULT_LOG_FIELDS = ("workflow", "context_delivery", "changed_context_names", "prompt_bytes",
                      "truncated_context_names", "unavailable_context_names", "resumed_session", "timings")
# Whitelisted, metadata-only run evidence. Result bodies never reach logs.
RUN_LOG_FIELDS = ("permission_denials_truncated", "returned_session_id_status", "actual_models_status",
                  "cli_output", "termination", "result_complete", "truncated_result_fields",
                  "declared_outputs", "output_permission_preflight", "output_observation", "stream_events")
MAX_TURNS_RANGE = (1, 20)
TIMEOUT_MAX_SECONDS = 3600
RESULT_STRING_LIMIT = 8000
RESULT_LIST_LIMIT = 100
CLI_STDOUT_LIMIT = 10485760
# Fixed bounded-I/O limits. JSON mode retains at most CLI_STDOUT_LIMIT bytes of stdout. Stream mode
# retains one frame at a time (STREAM_FRAME_LIMIT) and stops at STREAM_TOTAL_LIMIT of stdout in total.
# stderr is only counted, never retained; CLI_STDERR_LIMIT stops a runaway writer.
STREAM_FRAME_LIMIT = 4 * 1024 * 1024
STREAM_TOTAL_LIMIT = 64 * 1024 * 1024
CLI_STDERR_LIMIT = 64 * 1024 * 1024
IO_CHUNK = 65536
TERMINATE_GRACE = 2.0   # seconds between SIGTERM and SIGKILL, and for reaping afterwards
DRAIN_GRACE = 1.0       # seconds to collect bytes already written by a terminated CLI
EXIT_DRAIN_GRACE = 2.0  # seconds to keep reading after the leader exited (descendant-held pipes)
STREAM_EVENT_TYPES = ("system", "assistant", "user", "result")
KNOWN_DENIAL_TOOLS = frozenset({"Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch", "Agent", "Task"})
# Stops after which the received bytes are not trusted for any final-result evidence.
UNTRUSTED_STOPS = frozenset({"oversized", "frame_too_large", "critical_frame", "stderr_flood"})
OUTPUT_LIMIT = 20
OUTPUT_PATH_LIMIT = 1024
OUTPUT_HASH_LIMIT = 16 * 1024 * 1024
OUTPUT_HASH_BUDGET = 64 * 1024 * 1024
OUTPUT_FORBIDDEN_CHARS = frozenset("*?[]{}!\\")
# Host/bridge-owned names directly under .ai; also any *.lock file and state.* file.
OWNED_AI_NAMES = frozenset({"handoff.md", "state.yaml", "validation.md", "progress.md", "sessions.json",
                            "consult.json", "bridge.lock", ".gitignore"})
OWNED_AI_DIRS = frozenset({"logs", "backups", "requests"})
PERMISSION_EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
PERMISSION_TOOLS = PERMISSION_EDIT_TOOLS + ("Read",)
PERMISSION_RULE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)(?:\(([\s\S]*)\))?")
PERMISSION_TOOL_HINT = re.compile(r"\s*(?:edit|write|multiedit|notebookedit|read)\b", re.IGNORECASE)
PERMISSION_GLOB_CHARS = frozenset("*?[]{}!\\$`")
PERMISSION_RULE_LIMIT = 1000
PERMISSION_LIMITATIONS = (
    "local_file_scan_only", "remote_managed_session_and_cli_rules_not_scanned",
    "ancestor_settings_not_counted_as_grants", "user_local_settings_not_assumed",
    "native_cli_enforces_effective_permission", "static_check_is_not_a_sandbox_or_overwrite_guard")


class Blocked(Exception):
    """A safe, fixed-message diagnostic; never stores subprocess output or secrets."""

    def __init__(self, reason, metadata=None):
        super().__init__(reason)
        self.reason = reason
        self.metadata = metadata or {}


def emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def no_symlink(path):
    """Refuse symlink targets and symlink components, without reading their contents."""
    path = Path(path).absolute()
    for component in (path,) + tuple(path.parents):
        if component.is_symlink():
            # Darwin exposes these fixed system directory aliases by default.
            # They are not project-controlled state indirections.
            aliases = {Path("/var"): Path("/private/var"), Path("/tmp"): Path("/private/tmp"),
                       Path("/etc"): Path("/private/etc")}
            if component in aliases and component.resolve() == aliases[component]:
                continue
            raise Blocked("symlink_refused", {"file": component.name})
    if path.exists() and not (path.is_file() or path.is_dir()):
        raise Blocked("non_regular_path_refused", {"file": path.name})


def secure_directory(path):
    no_symlink(path)
    if path.exists() and not path.is_dir():
        raise Blocked("directory_required", {"file": path.name})
    path.mkdir(mode=0o700, exist_ok=True)


def read_bytes(path, limit=1048576):
    no_symlink(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(str(path), flags)
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise Blocked("non_regular_path_refused", {"file": path.name})
            data = handle.read(limit + 1)
    except OSError:
        raise Blocked("file_read_failed", {"file": path.name})
    if len(data) > limit:
        raise Blocked("file_too_large", {"file": path.name})
    return data


def atomic_write(path, data, mode=0o600):
    """Private temporary sibling + fsync + replace; refuses symlink destinations."""
    no_symlink(path)
    fd, temp = tempfile.mkstemp(prefix=".bridge-", dir=str(path.parent))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        no_symlink(path)
        os.replace(temp, str(path))
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_json(path):
    try:
        data = json.loads(read_bytes(path).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise Blocked("invalid_json", {"file": path.name})
    if not isinstance(data, dict):
        raise Blocked("json_object_required", {"file": path.name})
    return data


def resolve_project(raw):
    # A project is always explicit. Resolving a chosen project does not authorize
    # writing to another workspace through a symlink inside its .ai directory.
    project = Path(raw).expanduser().resolve()
    if not project.is_dir():
        raise Blocked("project_directory_required")
    return project


def task_text(project, args):
    """Validate raw components before resolution, then read a bounded regular file."""
    if args.task_file is None:
        task = args.task
    else:
        raw = Path(args.task_file).expanduser()
        raw = raw if raw.is_absolute() else project / raw
        # Path.resolve would hide symlink components, including a link/../ hop.
        no_symlink(raw)
        path = raw.resolve()
        try:
            path.relative_to(project)
        except ValueError:
            raise Blocked("task_file_must_be_inside_project")
        if not path.is_file():
            raise Blocked("task_file_regular_file_required")
        try:
            task = read_bytes(path, TASK_FILE_LIMIT).decode("utf-8")
        except UnicodeDecodeError:
            raise Blocked("task_file_must_be_utf8")
        args.task_path = path
    if not isinstance(task, str) or not task.strip() or len(task) > TASK_LIMIT:
        raise Blocked("task_required_and_must_be_bounded")
    try:
        task.encode("utf-8")
    except UnicodeEncodeError:
        raise Blocked("task_must_be_utf8")
    return task


@contextlib.contextmanager
def project_lock(project):
    path = project / ".ai" / "bridge.lock"
    no_symlink(path)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Blocked("project_already_locked")
        yield
    finally:
        os.close(fd)


def state_path(project):
    path = project / ".ai" / "sessions.json"
    no_symlink(path)
    if path.exists() and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise Blocked("session_permissions_must_be_0600")
    return path


def validate_ai(project):
    ai = project / ".ai"
    no_symlink(ai)
    if not ai.is_dir():
        raise Blocked("project_not_initialized", {"next_step": "Use init --project with this explicit directory."})
    for name in tuple(TEMPLATES) + ("sessions.json", "consult.json", "logs", "backups", "bridge.lock", ".gitignore"):
        no_symlink(ai / name)
    for name in TEMPLATES:
        if not (ai / name).is_file():
            raise Blocked("context_file_missing", {"file": name})
    state_path(project)
    return ai


def backup(ai, label, data):
    directory = ai / "backups"
    secure_directory(directory)
    name = label + "." + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S") + "." + uuid.uuid4().hex[:8] + ".bak"
    atomic_write(directory / name, data)


def ensure_ignore_patterns(ai, patterns):
    """Called under the project lock; append required ignores and back up edits."""
    ignore = ai / ".gitignore"
    existing = read_bytes(ignore) if ignore.exists() else b""
    missing = [pattern for pattern in patterns if pattern not in existing.decode("utf-8", "replace").splitlines()]
    if not missing:
        return None
    if existing:
        backup(ai, "gitignore", existing)
    suffix = b"\n" if existing and not existing.endswith(b"\n") else b""
    suffix += ("\n".join(missing) + "\n").encode("utf-8")
    atomic_write(ignore, existing + suffix)
    return "modified" if existing else "created"


def initialize(project):
    ai = project / ".ai"
    secure_directory(ai)
    created, modified = [], []
    with project_lock(project):
        for directory in ("logs", "backups"):
            existed = (ai / directory).exists()
            secure_directory(ai / directory)
            if not existed:
                created.append(".ai/" + directory + "/")
        for name, contents in TEMPLATES.items():
            path = ai / name
            no_symlink(path)
            if not path.exists():
                atomic_write(path, contents.encode("utf-8"))
                created.append(".ai/" + name)
        path = state_path(project)
        if not path.exists():
            state = {"schema_version": 1, "project": str(project), "claude": {}}
            atomic_write(path, json.dumps(state, indent=2).encode("utf-8") + b"\n")
            created.append(".ai/sessions.json")
        change = ensure_ignore_patterns(ai, ("sessions.json", "consult.json", "requests/", "logs/", "backups/", "bridge.lock"))
        if change:
            (modified if change == "modified" else created).append(".ai/.gitignore")
    return {"status": "initialized", "project": str(project), "created": created,
            "modified": modified, "inference": False}


def runtime_config(path):
    config = read_json(path)
    raw = config.get("claude_path")
    if not isinstance(raw, str) or not Path(raw).is_absolute():
        raise Blocked("runtime_requires_absolute_claude_path")
    executable = Path(raw)
    # Official native installation may expose a symlink. Pinning a version's
    # actual path in runtime.json is recommended; no PATH-based CLI lookup occurs.
    if not executable.is_file() or not os.access(str(executable), os.X_OK):
        raise Blocked("configured_claude_not_executable")
    expected_hash = config.get("claude_sha256")
    if expected_hash is not None:
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise Blocked("invalid_claude_integrity_metadata")
        actual_hash = hashlib.sha256()
        with executable.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1048576), b""):
                actual_hash.update(chunk)
        if actual_hash.hexdigest() != expected_hash:
            raise Blocked("claude_executable_integrity_mismatch")
    return config, str(executable)


def cli_environment():
    env = dict(os.environ)
    env["DISABLE_AUTOUPDATER"] = "1"
    env["DISABLE_UPDATES"] = "1"
    env.pop("FORCE_AUTOUPDATE_PLUGINS", None)
    return env


def setting_routes(data, prefix=""):
    found = []
    for key, value in data.items():
        if key in ROUTE_SETTINGS and value:
            found.append(prefix + key)
        elif key == "forceLoginMethod" and value and value != "claudeai":
            found.append(prefix + key)
        elif key == "env" and isinstance(value, dict):
            found.extend(prefix + "env." + name for name in sorted(ROUTE_ENV) if value.get(name))
        elif isinstance(value, dict) and key not in {"mcpServers", "oauthAccount"}:
            found.extend(setting_routes(value, prefix + key + "."))
    return found


def git_primary_checkout(project):
    """Resolve Git's primary checkout using metadata commands, without hooks."""
    env = cli_environment()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    command = ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null"]
    def query(arguments):
        try:
            result = subprocess.run(command + arguments, cwd=str(project), env=env,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        if len(result.stdout) > 1048576:
            raise Blocked("git_settings_metadata_too_large")
        return result.stdout
    # Non-Git directories remain supported. An unborn Git repository still has
    # a common dir and a worktree record even before its first commit.
    common = query(["rev-parse", "--path-format=absolute", "--git-common-dir"])
    if common is None:
        return None
    records = query(["worktree", "list", "--porcelain", "-z"])
    if records is None:
        raise Blocked("git_primary_settings_root_unverified")
    first = records.split(b"\0\0", 1)[0].split(b"\0")
    if b"bare" in first:
        return None
    for field in first:
        if field.startswith(b"worktree "):
            try:
                root = Path(os.fsdecode(field[len(b"worktree "):])).resolve()
            except (OSError, ValueError):
                raise Blocked("git_primary_settings_root_unverified")
            if root.is_dir():
                return root
    raise Blocked("git_primary_settings_root_unverified")


def settings_paths(project):
    """Applicable local-file metadata sources; no credentials/MDM/remote reads."""
    home = Path.home().resolve()
    paths = [home / ".claude" / "settings.json", home / ".claude" / "settings.local.json",
             home / ".claude.json", project / ".claude" / "settings.json",
             project / ".claude" / "settings.local.json", project / ".claude.json",
             home / ".claude" / "managed-settings.json",
             MANAGED_SETTINGS_DIR / "managed-settings.json"]
    for ancestor in project.parents:
        paths.extend([ancestor / ".claude" / "settings.json",
                      ancestor / ".claude" / "settings.local.json"])
    primary = git_primary_checkout(project)
    if primary is not None:
        # Native Git worktree local settings can live in the main checkout.
        # Keep the starting-directory path above as an additional conservative scan.
        paths.append(primary / ".claude" / "settings.local.json")
    dropins = MANAGED_SETTINGS_DIR / "managed-settings.d"
    no_symlink(dropins)
    if dropins.is_dir():
        paths.extend(path for path in sorted(dropins.glob("*.json"))
                     if not path.name.startswith(".") and (path.is_file() or path.is_symlink()))
    return list(dict.fromkeys(paths))


def effort_env_in_settings(data):
    for key, value in data.items():
        if key == "env" and isinstance(value, dict) and value.get(EFFORT_ENV):
            return True
        if isinstance(value, dict) and key not in {"mcpServers", "oauthAccount"} and effort_env_in_settings(value):
            return True
    return False


def effort_settings_metadata(data):
    """Report only known field names, never model names or settings values."""
    defaults, caps = [], []
    if "effortLevel" in data:
        defaults.append("effortLevel")
    if "maxEffortLevel" in data:
        caps.append("maxEffortLevel")
    models = data.get("modelSettings")
    if isinstance(models, dict):
        for value in models.values():
            if isinstance(value, dict) and "effortLevel" in value:
                defaults.append("modelSettings.*.effortLevel")
            if isinstance(value, dict) and "maxEffortLevel" in value:
                caps.append("modelSettings.*.maxEffortLevel")
    return sorted(set(defaults)), sorted(set(caps))


def route_guard(project):
    if os.environ.get(EFFORT_ENV):
        raise Blocked("effort_environment_override_refused", {"environment_names": [EFFORT_ENV]})
    names = sorted(name for name in ROUTE_ENV if os.environ.get(name))
    if names:
        raise Blocked("api_or_override_environment_refused", {"environment_names": names})
    home = Path.home().resolve()
    # Inspect presence only, never any credentials/ file or active profile name.
    # Active/default federation profiles can outrank /login without env overrides.
    profile_root = home / ".config" / "anthropic"
    for profile in (profile_root / "active_config", profile_root / "configs" / "default.json"):
        if profile.exists() or profile.is_symlink():
            raise Blocked("anthropic_profile_presence_requires_review", {"file": str(profile)})
    checked, effort_defaults, effort_caps = [], [], []
    for path in settings_paths(project):
        # Refuse symlinks even if broken, rather than silently skipping them.
        no_symlink(path)
        if path.exists():
            settings = read_json(path)
            if effort_env_in_settings(settings):
                raise Blocked("effort_environment_override_refused", {
                    "settings_file": str(path), "environment_names": [EFFORT_ENV]})
            routes = setting_routes(settings)
            checked.append(str(path))
            if routes:
                raise Blocked("custom_auth_or_upstream_settings_refused", {
                    "settings_file": str(path), "setting_names": sorted(set(routes))})
            defaults, caps = effort_settings_metadata(settings)
            if defaults:
                effort_defaults.append({"settings_file": str(path), "setting_names": defaults})
            if caps:
                effort_caps.append({"settings_file": str(path), "setting_names": caps})
    return {"environment_route_overrides": [], "settings_checked": checked,
            "effort_policy": {"coverage": "local_file_scan", "saved_defaults_detected": effort_defaults,
                              "possible_caps_detected": effort_caps,
                              "note": "Explicit CLI effort overrides saved defaults. Existing local/organization caps and model support can limit it; effective effort remains unknown."}}


def output_owned_reason(parts):
    folded = [part.casefold() for part in parts]
    if ".git" in folded or ".claude" in folded:
        return "output_path_git_or_claude_refused"
    if folded[0] == ".ai":
        name = folded[1] if len(folded) > 1 else ""
        if (not name or name in OWNED_AI_NAMES or name in OWNED_AI_DIRS
                or name.endswith(".lock") or name.split(".")[0] == "state"):
            return "output_path_bridge_owned_refused"
    return None


def normalize_output(project, raw, index):
    """One host-declared output: project-relative regular-file path, no indirection."""
    where = {"output_index": index}
    if not isinstance(raw, str) or not raw or len(raw) > OUTPUT_PATH_LIMIT:
        raise Blocked("output_path_invalid", where)
    if (any(ord(char) < 32 or ord(char) == 127 or char in "  " for char in raw)
            or any(char in OUTPUT_FORBIDDEN_CHARS for char in raw)):
        raise Blocked("output_path_unsupported_characters", where)
    try:
        raw.encode("utf-8")
    except UnicodeEncodeError:
        raise Blocked("output_path_unsupported_characters", where)
    if raw.startswith("/") or raw == "~" or raw.startswith("~/"):
        raise Blocked("output_path_must_be_project_relative", where)
    if raw.endswith("/"):
        raise Blocked("output_path_must_be_regular_file", where)
    parts = [part for part in raw.split("/") if part not in ("", ".")]
    if ".." in parts:
        raise Blocked("output_path_traversal_refused", where)
    if not parts:
        raise Blocked("output_path_invalid", where)
    reason = output_owned_reason(parts)
    if reason:
        raise Blocked(reason, where)
    current = project
    for position, part in enumerate(parts):
        current = current / part
        try:
            info = os.lstat(str(current))
        except (FileNotFoundError, NotADirectoryError):
            break
        except OSError:
            raise Blocked("output_path_unreadable", where)
        if stat.S_ISLNK(info.st_mode):
            raise Blocked("output_path_symlink_refused", where)
        if position == len(parts) - 1:
            if not stat.S_ISREG(info.st_mode):
                raise Blocked("output_path_must_be_regular_file", where)
        elif not stat.S_ISDIR(info.st_mode):
            raise Blocked("output_path_parent_not_directory", where)
    return "/".join(parts)


def validate_outputs(project, raw_outputs, workflow):
    """The host-supplied --output list is the only source of authorized output scope."""
    if not raw_outputs:
        return []
    if workflow == "consult":
        raise Blocked("outputs_not_allowed_in_consult_workflow")
    if len(raw_outputs) > OUTPUT_LIMIT:
        raise Blocked("too_many_declared_outputs", {"limit": OUTPUT_LIMIT})
    return list(dict.fromkeys(normalize_output(project, raw, index) for index, raw in enumerate(raw_outputs)))


def snapshot_output(project, rel, budget):
    """Existence, size and bounded hash only; never contents, never following symlinks."""
    entry = {"state": "missing", "exists": False, "bytes": None, "sha256": None, "hash_status": "not_applicable"}
    parts = rel.split("/")
    current = project
    try:
        for position, part in enumerate(parts):
            current = current / part
            info = os.lstat(str(current))
            last = position == len(parts) - 1
            if stat.S_ISLNK(info.st_mode):
                entry.update(state="symlink", exists=True)
                return entry
            if last and not stat.S_ISREG(info.st_mode):
                entry.update(state="not_regular", exists=True)
                return entry
            if not last and not stat.S_ISDIR(info.st_mode):
                entry["state"] = "not_regular"
                return entry
    except (FileNotFoundError, NotADirectoryError):
        return entry
    except OSError:
        entry.update(state="unreadable", exists=True)
        return entry
    entry.update(state="regular", exists=True, bytes=info.st_size)
    if info.st_size > OUTPUT_HASH_LIMIT:
        entry["hash_status"] = "skipped_size_limit"
        return entry
    if info.st_size > budget["remaining"]:
        entry["hash_status"] = "skipped_budget"
        return entry
    budget["remaining"] -= info.st_size
    try:
        fd = os.open(str(current), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                entry.update(state="not_regular", bytes=None)
                return entry
            hasher, total = hashlib.sha256(), 0
            for chunk in iter(lambda: handle.read(1048576), b""):
                total += len(chunk)
                if total > OUTPUT_HASH_LIMIT:
                    entry.update(bytes=total, hash_status="skipped_size_limit")
                    return entry
                hasher.update(chunk)
    except OSError:
        entry.update(state="unreadable", bytes=None)
        return entry
    entry.update(bytes=total, sha256=hasher.hexdigest(), hash_status="hashed")
    return entry


def observe_outputs(project, outputs):
    budget = {"remaining": OUTPUT_HASH_BUDGET}
    return {rel: snapshot_output(project, rel, budget) for rel in outputs}


def output_change(before, after):
    old, new = before["state"], after["state"]
    if "unreadable" in (old, new):
        return "unknown"
    if old == "missing" and new == "missing":
        return "unchanged"
    if old == "missing" and new == "regular":
        return "created"
    if old == "regular" and new == "missing":
        return "deleted"
    if old == "regular" and new == "regular":
        if before["sha256"] and after["sha256"]:
            return "unchanged" if before["sha256"] == after["sha256"] else "modified"
        return "modified" if before["bytes"] != after["bytes"] else "unknown"
    return "unknown" if old == new else "type_changed"


def output_observations(outputs, before, after):
    public = ("exists", "state", "bytes", "sha256", "hash_status")
    return [{"path": rel, "change": output_change(before[rel], after[rel]),
             "before": {key: before[rel][key] for key in public},
             "after": {key: after[rel][key] for key in public}} for rel in outputs]


def parse_permission_rule(entry):
    """None: unrelated tool. 'malformed': looks like a file-tool rule but is unparseable."""
    match = PERMISSION_RULE.fullmatch(entry)
    if match is None:
        return "malformed" if PERMISSION_TOOL_HINT.match(entry) else None
    tool, specifier = match.group(1), match.group(2)
    if tool not in PERMISSION_TOOLS:
        return "malformed" if tool.casefold() in {name.casefold() for name in PERMISSION_TOOLS} else None
    return tool, specifier


def read_permission_source(label, kind, path):
    source = {"source": label, "kind": kind, "status": "ok", "managed_only": False,
              "rules": {"allow": [], "ask": [], "deny": []}}
    try:
        no_symlink(path)
        if not path.exists():
            return None
        data = json.loads(read_bytes(path).decode("utf-8"))
    except Blocked as error:
        source["status"] = "oversized" if error.reason == "file_too_large" else "unreadable"
        return source
    except (ValueError, UnicodeDecodeError, RecursionError):
        source["status"] = "malformed"
        return source
    except OSError:
        source["status"] = "unreadable"
        return source
    permissions = data.get("permissions") if isinstance(data, dict) else None
    if not isinstance(data, dict) or not (permissions is None or isinstance(permissions, dict)):
        source["status"] = "malformed"
        return source
    source["managed_only"] = kind == "managed" and data.get("allowManagedPermissionRulesOnly") is True
    for name in ("allow", "ask", "deny"):
        entries = (permissions or {}).get(name, [])
        if not isinstance(entries, list) or not all(isinstance(entry, str) for entry in entries):
            source.update(status="malformed", rules={"allow": [], "ask": [], "deny": []})
            return source
        if len(entries) > PERMISSION_RULE_LIMIT or any(len(entry) > 2048 for entry in entries):
            source.update(status="oversized", rules={"allow": [], "ask": [], "deny": []})
            return source
        source["rules"][name] = [rule for rule in map(parse_permission_rule, entries) if rule is not None]
    return source


def permission_source_paths(project):
    """Confirmed local permission sources only; ancestors and user settings.local are not assumed."""
    home = Path.home().resolve()
    paths = [("user_settings", "user", home / ".claude" / "settings.json"),
             ("project_settings", "project", project / ".claude" / "settings.json"),
             ("project_local_settings", "project", project / ".claude" / "settings.local.json")]
    primary = git_primary_checkout(project)
    if primary is not None and primary != project:
        # The session's own directory stays the anchor for /path rules in this file.
        paths.append(("worktree_primary_local_settings", "project", primary / ".claude" / "settings.local.json"))
    paths.append(("managed_settings", "managed", MANAGED_SETTINGS_DIR / "managed-settings.json"))
    dropins = MANAGED_SETTINGS_DIR / "managed-settings.d"
    no_symlink(dropins)
    if dropins.is_dir():
        for index, path in enumerate(sorted(dropins.glob("*.json"))):
            if not path.name.startswith(".") and (path.is_file() or path.is_symlink()):
                paths.append(("managed_dropin_" + str(index), "managed", path))
    return paths


def permission_anchor(text, kind, project, home):
    """Absolute form of a rule path prefix, or None when its anchor is not unambiguous."""
    if text.startswith("//"):
        return text[1:]
    if text.startswith("~/"):
        return str(home) + text[1:]
    if text.startswith("~"):
        return None
    if text.startswith("/"):
        if kind == "user":
            return str(home / ".claude") + text
        return str(project) + text if kind == "project" else None
    if text.startswith("./"):
        return str(project) + text[1:]
    return str(project) + "/" + text


def classify_permission_path(spec, kind, project, home):
    """(form, absolute value, bare filename). Only literal paths are ever treated as exact."""
    if (not spec or spec != spec.strip() or len(spec) > 1024 or ".." in spec.split("/")
            or any(ord(char) < 32 or ord(char) == 127 for char in spec)):
        return "ambiguous", None, False
    glob = next((index for index, char in enumerate(spec) if char in PERMISSION_GLOB_CHARS), None)
    anchored = permission_anchor(spec if glob is None else spec[:glob], kind, project, home)
    if anchored is None:
        return "ambiguous", None, False
    if glob is not None:
        return "pattern", anchored[:anchored.rfind("/") + 1], False
    value = posixpath.normpath(anchored)
    if spec.endswith("/") or spec.split("/")[-1] == ".":
        return "directory", value.rstrip("/") + "/", False
    return "literal", value, "/" not in spec


def permission_relation(spec, kind, target, project, home):
    """exact | covers | maybe | None. 'maybe' means a rule could apply but is not provable."""
    form, value, bare = classify_permission_path(spec, kind, project, home)
    folded = target.casefold()
    if form == "ambiguous":
        return "maybe"
    if form == "pattern":
        return "maybe" if folded.startswith(value.casefold()) else None
    if form == "directory":
        return "covers" if folded.startswith(value.casefold()) else None
    if value == target:
        return "exact"
    folded_value = value.casefold()
    if folded_value == folded:
        return "maybe"
    if folded.startswith(folded_value + "/"):
        return "covers"
    if bare and posixpath.basename(folded_value) in folded.split("/"):
        return "maybe"
    return None


def classify_output_target(rel, project, home, sources, managed_only):
    target = str(project / rel)
    deny_or_ask = unknown = exact = unknown_allow = False
    reasons = set()
    for source in sources:
        if source["status"] != "ok":
            unknown = True
            reasons.add("source_unreadable_or_malformed")
            continue
        for list_name in ("deny", "ask", "allow"):
            if list_name == "allow" and managed_only and source["kind"] != "managed":
                continue
            for rule in source["rules"][list_name]:
                if rule == "malformed":
                    if list_name == "allow":
                        unknown_allow = True
                    else:
                        unknown = True
                    reasons.add("malformed_rule")
                    continue
                tool, spec = rule
                if list_name == "allow" and tool != "Edit":
                    continue
                if spec is None:
                    # A bare tool rule is broad: it blocks as deny/ask, but as allow it is not
                    # evidence of a precise grant, only related broad coverage.
                    relation = "exact" if list_name != "allow" else "maybe"
                else:
                    relation = permission_relation(spec, source["kind"], target, project, home)
                if relation is None:
                    continue
                if list_name == "allow":
                    if relation == "exact":
                        exact = True
                    else:
                        unknown_allow = True
                        reasons.add("related_pattern_or_ambiguous_rule")
                elif relation in ("exact", "covers"):
                    deny_or_ask = True
                else:
                    unknown = True
                    reasons.add("related_pattern_or_ambiguous_rule")
    if deny_or_ask:
        status = "deny_or_ask_may_apply"
    elif unknown:
        status = "unknown"
    elif exact:
        status = "static_covered"
    elif unknown_allow:
        status = "unknown"
    else:
        status = "missing_rule"
    return {"path": rel, "status": status,
            "reason_codes": sorted(reasons) if status in {"unknown", "deny_or_ask_may_apply"} else []}


def output_permission_preflight(project, outputs):
    """Conservative static check of exact Edit grants; native CLI still enforces permission.

    Only fixed codes and counts leave this function: no rule text, no settings values.
    """
    home = Path.home().resolve()
    sources = [source for source in (read_permission_source(*item) for item in permission_source_paths(project))
               if source is not None]
    managed_only = any(source["managed_only"] for source in sources if source["status"] == "ok")
    targets = [classify_output_target(rel, project, home, sources, managed_only) for rel in outputs]
    ignored = sum(1 for source in sources for rule in source["rules"]["allow"]
                  if rule != "malformed" and rule[0] in ("Write", "MultiEdit", "NotebookEdit"))
    return {"coverage": "local_file_scan", "ready": all(item["status"] == "static_covered" for item in targets),
            "targets": targets,
            "sources_scanned": [{"source": source["source"], "status": source["status"]} for source in sources],
            "managed_permission_rules_only": managed_only, "non_edit_allow_rules_ignored": ignored,
            "limitations": list(PERMISSION_LIMITATIONS),
            "note": "Static exact-rule check only; native Claude Code enforces the effective permission."}


def run_probe(executable, args, project, accepted_codes=(0,)):
    try:
        result = subprocess.run([executable] + args, cwd=str(project), env=cli_environment(),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Blocked("claude_probe_failed", {"probe": " ".join(args)})
    if result.returncode not in accepted_codes:
        raise Blocked("claude_probe_nonzero", {"probe": " ".join(args), "claude_exit_code": result.returncode})
    if len(result.stdout) > 1048576:
        raise Blocked("claude_probe_output_too_large")
    return result.stdout.decode("utf-8", "replace")


def cli_info(executable, config, project, workflow="standard", stream=False):
    raw_version = run_probe(executable, ["--version"], project)
    match = re.search(r"\b(\d+\.\d+\.\d+)\b", raw_version)
    version = match.group(1) if match else "unknown"
    expected_version = config.get("claude_version")
    if expected_version is not None and expected_version != version:
        raise Blocked("claude_version_mismatch", {"expected_version": expected_version, "actual_version": version})
    help_text = run_probe(executable, ["--help"], project)
    # An independently verified hidden flag may be listed in runtime.json.
    verified = config.get("verified_cli_flags", [])
    if not isinstance(verified, list) or not all(isinstance(f, str) for f in verified):
        raise Blocked("invalid_verified_cli_flags")
    required = (REQUIRED_FLAGS + (("--tools", "--strict-mcp-config", "--mcp-config", "--system-prompt-snapshot") if workflow == "consult" else ())
                + (("--verbose",) if stream else ()))
    unsupported = [flag for flag in required if flag not in help_text and flag not in verified]
    return version, unsupported


def auth_status(executable, project):
    # Official auth status returns 1 with valid logged-out JSON; that is useful
    # read-only evidence, not a reason to print raw error output.
    text = run_probe(executable, ["auth", "status", "--json"], project, accepted_codes=(0, 1))
    try:
        raw = json.loads(text)
    except ValueError:
        raise Blocked("auth_status_json_unavailable")
    if not isinstance(raw, dict):
        raise Blocked("auth_status_json_unavailable")
    # Strict enums prevent hidden data from being smuggled through status fields.
    method = raw.get("authMethod")
    plan = raw.get("subscriptionType")
    methods = {"none", "claude.ai", "oauth_token", "api_key", "api_key_helper", "third_party", "console"}
    plans = {"pro", "max", "team", "enterprise", "free"}
    return {"loggedIn": raw.get("loggedIn") is True,
            "authMethod": method if method in methods else "unknown",
            "subscriptionType": plan if plan in plans else "unknown"}


def doctor(project, runtime):
    config, executable = runtime_config(runtime)
    routes = route_guard(project)
    version, unsupported = cli_info(executable, config, project)
    auth = auth_status(executable, project)
    eligible = auth["loggedIn"] and auth["authMethod"] == "claude.ai" and auth["subscriptionType"] in {"pro", "max"}
    return {"status": "doctor", "project": str(project), "claude_path": executable,
            "claude_version": version, "auth": auth, "subscription_auth_eligible": eligible,
            "subscription_usage_credits_disabled": config.get("subscription_usage_credits_disabled") is True,
            "unsupported_flags": unsupported, "routing": routes, "inference": False,
            "note": "Authentication type alone does not independently prove billing source or remaining quota."}


def scrub(text, limit=8000):
    """Best-effort output hygiene; use limit=None before choosing a bounded tail."""
    text = str(text)
    secret_key = r"(?:[A-Z0-9_]*(?:API[_-]?KEY|AUTH[_-]?TOKEN|OAUTH[_-]?TOKEN)|password|cookie|secret|token|access_token|refresh_token|id_token|authorization)"
    # Handle embedded JSON string values independently; do not consume the next
    # field or expose quoted credentials that bypass the unquoted assignment rule.
    # Also redact values whose source itself ends before the closing quote,
    # including a final escape. Bound only after matching the complete input.
    json_secret = re.compile(r'(?i)("' + secret_key + r'"\s*:\s*)"(?:\\[\s\S]|[^"\\])*(?:"|\\?\Z)')
    text = json_secret.sub(lambda match: match.group(1) + '"[REDACTED]"', text)
    single_secret = re.compile(r"(?i)('" + secret_key + r"'\s*:\s*)'(?:\\[\s\S]|[^'\\])*(?:'|\\?\Z)")
    text = single_secret.sub(lambda match: match.group(1) + "'[REDACTED]'", text)
    text = re.sub(r"(?i)\b(?:sk-ant-|sk-proj-|sk-live-|sk-)[A-Za-z0-9_-]+", "[REDACTED]", text)
    text = re.sub(r"(?i)\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", text)
    text = re.sub(r"(?i)\b" + secret_key + r"\s*[:=]\s*[^\s,;]+", "[REDACTED_SECRET]", text)
    text = re.sub(r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED_JWT]", text)
    # Avoid injected Markdown markers/scripts in bridge-generated Handoff blocks.
    text = text.replace("<!--", "&lt;!--").replace("-->", "--&gt;").replace("\x00", "")
    return text if limit is None else text[:limit]


def bounded_sanitized_text(raw, limit, tail=False):
    """Redact the complete input, then choose a UTF-8 byte-bounded view."""
    sanitized = scrub(raw.decode("utf-8", "replace"), limit=None).encode("utf-8")
    bounded = sanitized[-limit:] if tail else sanitized[:limit]
    # A byte budget may split a multibyte character, never a raw secret value.
    return bounded.decode("utf-8", "ignore"), len(sanitized) > limit


def git_snapshot(project, consult=False, task_path=None):
    env = cli_environment()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    base = ["git", "-c", "core.fsmonitor=false", "-c", "diff.external="]
    def git(args):
        try:
            p = subprocess.run(base + args, cwd=str(project), env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            return p.stdout if p.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    head = git(["rev-parse", "HEAD"])
    # No external diff/textconv execution and no automatic credential/log diff.
    excludes = [".ai/sessions.json", ".ai/consult.json", ".ai/requests/**", ".ai/logs/**", ".ai/backups/**", ".ai/bridge.lock",
                "**/.env", "**/.env.*", ".env", ".env.*", "**/*.pem", "**/*.key",
                "**/credentials*", "**/auth.json", "**/secrets*", "**/.claude.json"]
    if consult:
        # Generated request/evidence additions are not project code changes.
        # Independent human Handoff changes are fingerprinted separately.
        excludes.append(".ai/HANDOFF.md")
    paths = ["."] + [":(exclude)" + path for path in excludes]
    if task_path is not None:
        paths.append(":(literal,exclude)" + str(task_path.relative_to(project)))
    status = git(["status", "--porcelain=v1", "--untracked-files=normal"] + (["--"] + paths if consult or task_path is not None else []))
    diff = git(["diff", "--no-ext-diff", "--no-textconv", "HEAD", "--"] + paths)
    if diff is None and status is not None:
        # An unborn repository has no HEAD. Worktree-only diff would silently
        # omit all staged new files, so retain both independently labelled views.
        staged = git(["diff", "--no-ext-diff", "--no-textconv", "--cached", "--"] + paths)
        worktree = git(["diff", "--no-ext-diff", "--no-textconv", "--"] + paths)
        if staged is not None and worktree is not None:
            diff = b"--- Staged diff (unborn HEAD) ---\n" + staged + b"\n--- Worktree diff (unborn HEAD) ---\n" + worktree
    return {"available": status is not None,
            "head": head.decode("ascii", "replace").strip() if head and re.fullmatch(rb"[0-9a-f]{40,64}\s*", head) else "unknown",
            "status_sha256": digest(status) if status is not None else "unknown",
            "diff_sha256": digest(diff) if diff is not None else "unknown",
            "status": bounded_sanitized_text(status, 16000)[0] if status is not None else "unknown (Git unavailable)",
            "diff": bounded_sanitized_text(diff, 24000)[0] if diff is not None else "unknown (Git unavailable)",
            "status_truncated": bool(status and len(status) > 16000),
            "diff_truncated": bool(diff and len(diff) > 24000)}


def public_snapshot(snapshot):
    return {key: snapshot[key] for key in ("available", "head", "status_sha256", "diff_sha256",
                                           "status_truncated", "diff_truncated")}


def session_for(project, new_session):
    path = state_path(project)
    if new_session:
        return None
    state = read_json(path)
    if state.get("project") != str(project):
        raise Blocked("session_project_mismatch", {"next_step": "Inspect state; use --new-session only for an explicit fresh session."})
    claude = state.get("claude")
    if not isinstance(claude, dict) or set(claude) - {"session_id"}:
        raise Blocked("session_state_schema_invalid")
    if set(state) - {"schema_version", "project", "claude"}:
        raise Blocked("session_state_schema_invalid")
    sid = claude.get("session_id")
    if sid is None:
        return None
    if not valid_session(sid):
        raise Blocked("invalid_session_id", {"next_step": "Inspect state; use --new-session only for an explicit fresh session."})
    return sid


def valid_session(value):
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value.lower()
    except (ValueError, AttributeError):
        return False


def consult_cache_path(project):
    path = project / ".ai" / "consult.json"
    no_symlink(path)
    if path.exists() and (not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600):
        raise Blocked("consult_permissions_must_be_0600")
    return path


def consult_cache(project, session, mode):
    path = consult_cache_path(project)
    if not path.exists() or not session:
        return None
    try:
        data = read_json(path)
    except Blocked as error:
        if error.reason in {"invalid_json", "json_object_required", "file_too_large"}:
            return None
        raise
    if (set(data) != {"schema_version", "project", "mode", "session_id", "fingerprints"}
            or data.get("schema_version") != 1 or data.get("project") != str(project)
            or data.get("mode") != mode or data.get("session_id") != session):
        return None
    hashes = data.get("fingerprints")
    allowed_names = set(TEMPLATES) | {"Git"}
    allowed_names.update("instructions:" + str(directory / name)
                         for directory in (project,) + tuple(project.parents)
                         for name in ("AGENTS.md", "CLAUDE.md"))
    if (not isinstance(hashes, dict) or not hashes or len(hashes) > 256
            or not all(isinstance(key, str) and key in allowed_names
                       and isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                       for key, value in hashes.items())):
        return None
    return hashes


def invalidate_consult_cache(project):
    path = consult_cache_path(project)
    if path.exists():
        path.unlink()


def human_handoff(raw):
    """Remove only complete bridge-owned blocks, retaining incomplete/human text."""
    for marker in (b"claude-bridge", b"claude-bridge-consult-request"):
        pattern = rb"<!-- " + marker + rb":[0-9a-f]{32} -->[\s\S]*?<!-- /" + marker + rb" -->"
        raw = re.sub(pattern, b"", raw)
    # Generated appends introduce separator blank lines; these are not human edits.
    return raw.rstrip()


def consult_context(project, before):
    sections, hashes, truncated_names = {}, {}, []
    for name in TEMPLATES:
        raw = read_bytes(project / ".ai" / name)
        if name == "HANDOFF.md":
            raw = human_handoff(raw)
        hashes[name] = digest(raw)
        bounded, truncated = bounded_sanitized_text(raw, 12000, name != "PROJECT_CONTEXT.md")
        if truncated:
            truncated_names.append(name)
        suffix = " (bounded recent tail)" if truncated and name != "PROJECT_CONTEXT.md" else " (bounded prefix)" if truncated else ""
        sections[name] = name + suffix + ":\n" + bounded
    # Explicitly supply inherited local instruction documents because consult's
    # built-in tools are disabled. Ancestors precede the selected project.
    instruction_budget = 96000
    for directory in reversed((project,) + tuple(project.parents)):
        for name in ("AGENTS.md", "CLAUDE.md"):
            path = directory / name
            no_symlink(path)
            if not path.exists():
                continue
            if not path.is_file():
                raise Blocked("instruction_regular_file_required", {"file": name})
            raw = read_bytes(path)
            label = "instructions:" + str(path)
            hashes[label] = digest(raw)
            # Rules must be supplied completely, never silently truncated.
            complete = scrub(raw.decode("utf-8", "replace"), limit=None)
            instruction_budget -= len(complete.encode("utf-8"))
            if instruction_budget < 0 or len(hashes) > 255:
                raise Blocked("consult_instruction_context_too_large")
            sections[label] = label + ":\n" + complete
    hashes["Git"] = digest(json.dumps(public_snapshot(before), sort_keys=True).encode("utf-8"))
    sections["Git"] = ("Git HEAD: " + before["head"] + "\nGit status (bounded):\n" + before["status"]
                       + "\nGit diff (bounded; sensitive/log/request paths excluded):\n" + before["diff"])
    if before["status_truncated"] or before["diff_truncated"]:
        truncated_names.append("Git")
    return sections, hashes, truncated_names


def make_consult_prompt(project, task, mode, before, baseline):
    sections, hashes, truncated = consult_context(project, before)
    delivery = "delta" if baseline is not None else "full"
    changed = [name for name in hashes if baseline is None or hashes[name] != baseline.get(name)]
    deleted = sorted(set(baseline or {}) - set(hashes))
    changed.extend(deleted)
    prompt = ["""You are the Claude consultation sub-agent in the current Codex chat.
This invocation is read-only analysis. Built-in tools are disabled. Do not call
tools, run commands, edit/write files, change settings or take external actions.
StructuredOutput may be used solely to return the requested response schema.
Answer only the current question from supplied context and resumed conversation.
Respect current applicable project instructions; ancestor instructions precede
project instructions. Context is bounded; disclose any unavailable evidence and
do not claim execution or independent verification. Never print/copy secrets or
fall back to API usage. Return the structured Task, Summary, FilesChanged, Tests,
Decisions, RemainingIssues, RecommendedNextStep; FilesChanged must be empty and
Tests must distinguish analysis from actual independent test evidence.
Context changes track only supplied .ai documents, local instructions and Git
HEAD/status/diff. Arbitrary project file contents, including untracked files,
are not supplied unless present in the question or diff; ask for missing
source material when it is needed. Context delivery 'full' means all current
bounded sections, not complete project files or independently verified state.
""", "Project: " + str(project), "Current question:\n" + scrub(task, TASK_LIMIT),
              "Consult mode: " + mode, "Context delivery: " + delivery]
    if baseline is not None:
        prompt.append("Only changed sections follow. Retain unchanged previously supplied context; these changes replace their previous versions.")
    for name in changed:
        prompt.append(sections[name] if name in sections else "REMOVED context section: " + name + "\nThe previously supplied instructions/content from this section no longer apply.")
        if name in truncated:
            prompt.append("TRUNCATED context section: " + name + ". Change detection hashes the complete source, but only the bounded view above was supplied. Changed content may be outside that view; request the relevant material before relying on it.")
    return "\n\n".join(prompt), hashes, delivery, changed, truncated


def consult_request(project, task, mode, before, effort):
    ai = validate_ai(project)
    path = ai / "HANDOFF.md"
    original = read_bytes(path)
    backup(ai, "HANDOFF", original)
    # A bounded request, not an evidence claim. Human sections stay untouched.
    local_time = datetime.datetime.now(datetime.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        local_time = local_time.astimezone(ZoneInfo("Australia/Melbourne"))
    except (ImportError, KeyError):
        raise Blocked("melbourne_timezone_unavailable")
    block = ["", "<!-- claude-bridge-consult-request:" + uuid.uuid4().hex + " -->",
             "## Claude Bridge consultation request", "",
             "Request goal (bounded): " + scrub(task, 800).replace("\n", " ").replace("\r", " "),
             "Melbourne time: " + local_time.isoformat(timespec="seconds"),
             "Project: " + str(project), "Requested mode/model: " + mode + (" (native selection)" if mode == "default" else " (sonnet)" if mode == "review" else ""),
             "Requested effort: " + effort["requested_effort"],
             "Effort source: " + effort["effort_source"], "Effort reason: " + effort["effort_reason"],
             "Git HEAD: " + before["head"], "Git status SHA256: " + before["status_sha256"],
             "Git diff SHA256: " + before["diff_sha256"],
             "Request only; no inference, test, billing or project acceptance evidence is claimed.",
             "<!-- /claude-bridge-consult-request -->\n"]
    atomic_write(path, original + (b"\n" if original and not original.endswith(b"\n") else b"")
                 + "\n".join(block).encode("utf-8"))


def make_prompt(project, task, mode, before):
    sections = ["""You are the Claude sub-agent in the current Codex workflow.
GPT and Claude share this explicitly chosen project directory. Complete only
the current task. Read the supplied working state; hidden reasoning and full
chat histories are not shared. Existing project instructions and normal
permissions apply. Work serially; inspect before editing and run relevant tests
when permitted. Do not run destructive Git commands, reset/clean/force-push,
rebase or destructive checkout; do not automatically commit. Do not alter
authentication, providers, payment settings, user policies or account data.
Never fall back to API usage. Do not print, copy or persist secrets. Do not edit
.ai/sessions.json, .ai/logs/, .ai/backups/ or .ai/HANDOFF.md: the bridge owns these.
Return only the requested structured Task, Summary, FilesChanged, Tests,
Decisions, RemainingIssues, RecommendedNextStep. Distinguish actual command
execution from assumptions, permission denial and unavailable evidence.
""", "Project: " + str(project), "Current task:\n" + scrub(task, 32000)]
    if mode == "review":
        sections.append("Review the current Git diff for correctness, regression, security, architecture and missing tests. Fix clear issues only within the requested scope and normal permissions.")
    for name in TEMPLATES:
        data = read_bytes(project / ".ai" / name)
        tail = name != "PROJECT_CONTEXT.md"
        bounded, truncated = bounded_sanitized_text(data, 12000, tail)
        label = " (bounded recent tail)" if tail and truncated else " (bounded prefix)" if truncated else ""
        sections.append(name + label + ":\n" + bounded)
    sections.append("Git status (bounded):\n" + before["status"])
    sections.append("Git diff (bounded; sensitive/log paths excluded):\n" + before["diff"])
    return "\n\n".join(sections)


def signal_name(number):
    try:
        return signal.Signals(number).name
    except ValueError:
        return "SIG" + str(number)


def stderr_code(stderr_bytes):
    return "present_not_recorded" if stderr_bytes else "empty"


def inspect_cli_output(stdout, stdout_bytes, stderr_bytes):
    """Finite diagnostics for CLI streams: byte counts and fixed codes, never text.

    stdout holds at most CLI_STDOUT_LIMIT retained bytes; stdout_bytes is the full count.
    """
    diagnostics = {"stdout_bytes": stdout_bytes, "stderr_bytes": stderr_bytes, "stderr": stderr_code(stderr_bytes)}
    if stdout_bytes > CLI_STDOUT_LIMIT:
        diagnostics["stdout_format"] = "too_large"
        return diagnostics, None
    if not stdout.strip():
        diagnostics["stdout_format"] = "empty"
        return diagnostics, None
    try:
        payload = json.loads(stdout.decode("utf-8"))
    except UnicodeDecodeError:
        diagnostics["stdout_format"] = "not_utf8"
        return diagnostics, None
    except (ValueError, RecursionError):
        diagnostics["stdout_format"] = "malformed"
        return diagnostics, None
    if not isinstance(payload, dict):
        diagnostics["stdout_format"] = "json_non_object"
        return diagnostics, None
    diagnostics["stdout_format"] = "json_object"
    return diagnostics, payload


def safe_tool_name(value):
    return value if isinstance(value, str) and value in KNOWN_DENIAL_TOOLS else "Other"


def final_result_metadata(payload):
    """Denials, models and session status come only from an official final result object.

    Returns (metadata, invalid_denials). A missing field is 'unavailable', never an empty list.
    """
    metadata = {"permission_denials": None, "permission_denials_status": "unavailable",
                "actual_models": [], "actual_models_status": "unavailable",
                "returned_session_id_status": "unavailable"}
    if payload is None or payload.get("type") != "result":
        return metadata, False
    invalid = False
    if "permission_denials" in payload:
        denials = payload["permission_denials"]
        if isinstance(denials, list):
            metadata["permission_denials"] = [safe_tool_name(d.get("tool_name") if isinstance(d, dict) else None)
                                              for d in denials[:RESULT_LIST_LIMIT]]
            metadata["permission_denials_status"] = "listed" if denials else "none_reported"
            if len(denials) > RESULT_LIST_LIMIT:
                metadata["permission_denials_truncated"] = True
        else:
            invalid = True
    usage = payload.get("modelUsage")
    if isinstance(usage, dict):
        names = sorted(name for name in usage if isinstance(name, str) and re.fullmatch(r"claude-[a-z0-9.-]{1,100}", name))
        metadata["actual_models"] = names[:50]
        metadata["actual_models_status"] = "reported" if names else "none_reported"
    returned = payload.get("session_id")
    metadata["returned_session_id_status"] = "absent" if returned is None else "returned" if valid_session(returned) else "invalid"
    return metadata, invalid


def record_official_timings(payload, timings):
    if payload is None or payload.get("type") != "result":
        return
    official = {}
    for key in ("duration_ms", "duration_api_ms"):
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if finite:
                official[key] = value
    if official:
        timings["official_cli"] = {**official, "provenance": "official_cli_result"}


class CliPump:
    """Bounded, nonblocking pipe consumer for one CLI process.

    Writes the prompt while draining stdout and stderr, so neither side can deadlock on a full pipe.
    stderr is only counted. JSON mode retains at most CLI_STDOUT_LIMIT bytes of stdout; stream mode
    retains one frame at a time, keeps counts and whitelisted metadata, and keeps the final result object.
    """

    def __init__(self, proc, prompt, stream):
        self.proc, self.stream, self.prompt, self.offset = proc, stream, prompt, 0
        self.stdout_bytes = self.stderr_bytes = 0
        self.retained, self.line = bytearray(), bytearray()
        self.events = {name: 0 for name in STREAM_EVENT_TYPES + ("other",)}
        self.invalid_lines = self.denial_events = 0
        self.denials, self.final = [], None
        self.ended = None
        # First stop that makes received bytes untrustworthy; stays set even if a different stop came first.
        self.untrusted = None
        self.exit_seen_at = None
        self.selector = selectors.DefaultSelector()
        for name, handle, mode in (("stdin", proc.stdin, selectors.EVENT_WRITE),
                                   ("stdout", proc.stdout, selectors.EVENT_READ),
                                   ("stderr", proc.stderr, selectors.EVENT_READ)):
            os.set_blocking(handle.fileno(), False)
            self.selector.register(handle, mode, name)

    def stop(self, reason):
        if self.ended is None:
            self.ended = reason
        if reason in UNTRUSTED_STOPS and self.untrusted is None:
            self.untrusted = reason

    def release(self, handle):
        with contextlib.suppress(KeyError, ValueError, OSError):
            self.selector.unregister(handle)
        with contextlib.suppress(OSError):
            handle.close()

    def close(self):
        for handle in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            self.release(handle)
        self.selector.close()

    def handle_stdin(self):
        try:
            written = os.write(self.proc.stdin.fileno(), self.prompt[self.offset:self.offset + IO_CHUNK])
        except (BlockingIOError, InterruptedError):
            return
        except OSError:
            # The CLI closed its stdin early; whatever it does next is judged by its output.
            self.release(self.proc.stdin)
            return
        self.offset += written
        if self.offset >= len(self.prompt):
            self.release(self.proc.stdin)

    def read_chunk(self, handle):
        try:
            data = os.read(handle.fileno(), IO_CHUNK)
        except (BlockingIOError, InterruptedError):
            return None
        except OSError:
            data = b""
        if not data:
            self.release(handle)
        return data

    def handle_event(self, name):
        if name == "stdin":
            self.handle_stdin()
        elif name == "stderr":
            data = self.read_chunk(self.proc.stderr)
            if data:
                self.stderr_bytes += len(data)  # counted, never retained
                if self.stderr_bytes > CLI_STDERR_LIMIT:
                    self.stop("stderr_flood")
        else:
            data = self.read_chunk(self.proc.stdout)
            if data:
                self.feed_stdout(data)

    def feed_stdout(self, data):
        self.stdout_bytes += len(data)
        if self.untrusted:
            return
        if not self.stream:
            if self.stdout_bytes > CLI_STDOUT_LIMIT:
                self.stop("oversized")
            else:
                self.retained += data
            return
        if self.stdout_bytes > STREAM_TOTAL_LIMIT:
            self.stop("oversized")
            self.line.clear()
            return
        self.line += data
        start = 0
        while not self.untrusted:
            end = self.line.find(b"\n", start)
            if end < 0:
                break
            if end - start > STREAM_FRAME_LIMIT:
                self.stop("frame_too_large")
                break
            self.frame(bytes(self.line[start:end]))
            start = end + 1
        del self.line[:start]
        if len(self.line) > STREAM_FRAME_LIMIT:
            self.stop("frame_too_large")
        if self.untrusted:
            self.line.clear()

    def frame(self, raw):
        """One newline-delimited event: counted and, for two official shapes only, acted on."""
        if not raw.strip():
            return
        try:
            event = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, RecursionError):
            event = None
        if not isinstance(event, dict):
            # An unparseable line may have been the denial or the final result: fail closed.
            self.invalid_lines += 1
            self.stop("critical_frame")
            return
        kind = event.get("type")
        self.events[kind if kind in STREAM_EVENT_TYPES else "other"] += 1
        if kind == "system" and event.get("subtype") == "permission_denied":
            # Only this exact top-level shape counts; text mentioning a denial never does.
            self.denial_events += 1
            if len(self.denials) < RESULT_LIST_LIMIT:
                self.denials.append(safe_tool_name(event.get("tool_name")))
            self.stop("permission_denied")
        elif kind == "result":
            if self.final is not None:
                self.invalid_lines += 1
                self.stop("critical_frame")
            else:
                self.final = event

    def finish_stream(self):
        """Judge the unterminated trailing frame at EOF; may add an untrusted stop."""
        if self.stream and self.line.strip() and not self.untrusted:
            if len(self.line) > STREAM_FRAME_LIMIT:
                self.stop("frame_too_large")
            else:
                self.frame(bytes(self.line))
        self.line.clear()

    def pump(self, deadline, draining=False):
        """Run until EOF on both output pipes, a stop reason, or the monotonic deadline."""
        while self.selector.get_map():
            now = time.monotonic()
            if now >= deadline:
                return "deadline"
            if not draining and self.ended is not None:
                return "stopped"
            if self.proc.poll() is not None:
                if self.exit_seen_at is None:
                    self.exit_seen_at = now
                elif now - self.exit_seen_at >= EXIT_DRAIN_GRACE:
                    return "pipes_held_after_exit"
            for key, _mask in self.selector.select(min(deadline - now, 0.25)):
                self.handle_event(key.data)
        return "eof"


def terminate_group(proc):
    """SIGTERM the whole process group, wait a bounded time, then SIGKILL and reap."""
    def send(number):
        with contextlib.suppress(OSError):
            os.killpg(proc.pid, number)
    sent = "SIGTERM"
    send(signal.SIGTERM)
    limit = time.monotonic() + TERMINATE_GRACE
    while proc.poll() is None and time.monotonic() < limit:
        time.sleep(0.02)
    if proc.poll() is None:
        sent = "SIGKILL"
    send(signal.SIGKILL)  # stragglers that ignored SIGTERM or outlived the leader
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=TERMINATE_GRACE)
    return sent


FORCED_FAILURES = {"oversized": "claude_output_too_large", "frame_too_large": "claude_stream_frame_too_large",
                   "critical_frame": "claude_stream_malformed_frame", "stderr_flood": "claude_stderr_too_large"}
TERMINATION_REASONS = {"timeout": "timeout", "oversized": "oversized_stdout", "frame_too_large": "oversized_stream_frame",
                       "critical_frame": "malformed_stream_frame", "stderr_flood": "stderr_flood",
                       "permission_denied": "permission_denied_event"}


def run_inference(command, prompt, project, timeout, stream=False):
    started = time.monotonic()
    timings = {"provenance": "bridge_monotonic"}
    def finish(outcome, session=None):
        timings.update(cli_finished_at=timestamp(), cli_wall_ms=round((time.monotonic() - started) * 1000, 3))
        outcome["timings"] = timings
        return outcome, session
    try:
        proc = subprocess.Popen(command, cwd=str(project), env=cli_environment(),
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
    except OSError:
        return finish({"status": "failed", "claude_exit_code": None, "reason": "claude_launch_failed",
                       **final_result_metadata(None)[0]})
    timings["cli_spawned_at"] = timestamp()
    deadline = time.monotonic() + timeout
    pump = CliPump(proc, prompt.encode("utf-8"), stream)
    state = pump.pump(deadline)
    if state == "eof" and proc.poll() is None:
        # Output pipes closed but the process lives on: still bounded by the same deadline.
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=max(0.0, deadline - time.monotonic()))
        if proc.poll() is None:
            state = "deadline"
    ended = pump.ended or ("timeout" if state == "deadline" else "pipes_held_after_exit" if state == "pipes_held_after_exit" else None)
    signal_sent = None
    if ended is not None:
        signal_sent = terminate_group(proc)
        # Bytes the CLI had already written (possibly a complete final result) are still collected.
        pump.pump(time.monotonic() + DRAIN_GRACE, draining=True)
    pump.finish_stream()
    pump.close()
    # The trailing frame is judged only now: refresh the primary reason, but never override a
    # known timeout or permission-denied stop. An EOF-only finding sends no signal.
    if pump.ended is not None and ended in (None, "pipes_held_after_exit"):
        ended = pump.ended
    returned = proc.returncode
    if stream:
        stdout_format = ("too_large" if pump.untrusted in ("oversized", "frame_too_large") else "stream_malformed" if pump.untrusted == "critical_frame"
                         else "empty" if pump.stdout_bytes == 0 else "stream_json")
        diagnostics = {"stdout_bytes": pump.stdout_bytes, "stderr_bytes": pump.stderr_bytes,
                       "stderr": stderr_code(pump.stderr_bytes), "stdout_format": stdout_format}
        payload = pump.final
    else:
        diagnostics, payload = inspect_cli_output(bytes(pump.retained), pump.stdout_bytes, pump.stderr_bytes)
    if pump.untrusted:
        payload = None  # whatever stop came first, nothing received is trusted as a final result
    if ended == "pipes_held_after_exit":
        diagnostics["descendants_held_pipes"] = True
    metadata, invalid_denials = final_result_metadata(payload)
    sid = payload.get("session_id") if metadata["returned_session_id_status"] == "returned" else None
    outcome = {"claude_exit_code": returned, "cli_output": diagnostics, **metadata}
    if stream:
        outcome["stream_events"] = {"events": pump.events, "invalid_lines": pump.invalid_lines,
                                    "permission_denied_events": pump.denial_events,
                                    "final_result_seen": pump.final is not None,
                                    "final_result_trusted": pump.final is not None and not pump.untrusted}
    record_official_timings(payload, timings)
    if ended is not None and ended != "pipes_held_after_exit":
        outcome["termination"] = {
            "reason": TERMINATION_REASONS[ended], "signal_sent": signal_sent,
            "exit_code": returned if returned is not None and returned >= 0 else None,
            "exit_signal": signal_name(-returned) if returned is not None and returned < 0 else None,
            "completion": "incomplete" if ended == "permission_denied" else "unknown"}
        if ended == "timeout":
            outcome["termination"]["timeout_seconds"] = timeout
    if ended == "timeout":
        # Forced termination is never completion, even if a complete final result was delivered.
        outcome.update(status="timeout", reason="Completion unknown after timeout; no automatic retry.")
        return finish(outcome, sid)
    if ended == "permission_denied":
        # Conservative: the first explicit official denial ends the batch; no silent retry.
        outcome.update(status="needs_permission", permission_denials=pump.denials, permission_denials_status="listed",
                       reason="Official permission_denied event; stopped at the first explicit denial; task not complete.")
        if pump.denial_events > len(pump.denials):
            outcome["permission_denials_truncated"] = True
        return finish(outcome, sid)
    if ended in FORCED_FAILURES:
        outcome.update(status="failed", reason=FORCED_FAILURES[ended])
        return finish(outcome)
    if payload is None:
        stdout_format = diagnostics["stdout_format"]
        if stdout_format == "too_large":
            reason = "claude_output_too_large"
        elif stream and returned == 0:
            reason = "claude_stream_final_result_unavailable"
        elif stdout_format == "json_non_object" or returned == 0:
            reason = "claude_result_json_unavailable"
        else:
            reason = "claude_nonzero; no automatic retry or API fallback"
        outcome.update(status="failed", reason=reason)
        return finish(outcome)
    if invalid_denials:
        outcome.update(status="failed", reason="invalid_permission_denials_metadata")
        return finish(outcome, sid)
    if returned != 0:
        outcome.update(status="failed", reason="claude_nonzero; no automatic retry or API fallback")
        return finish(outcome, sid)
    if metadata["permission_denials_status"] == "listed":
        outcome.update(status="needs_permission", reason="Normal Claude Code permission denied; task not complete.")
        return finish(outcome, sid)
    if payload.get("type") != "result" or payload.get("subtype") != "success" or payload.get("is_error") is not False:
        outcome.update(status="failed", reason="claude_reported_error_or_unrecognized_result")
        return finish(outcome, sid)
    structured = payload.get("structured_output")
    if not isinstance(structured, dict):
        try:
            structured = json.loads(payload.get("result", ""))
        except (ValueError, TypeError, RecursionError):
            structured = None
    if not isinstance(structured, dict) or any(key not in structured for key in RESULT_FIELDS):
        outcome.update(status="failed", reason="structured_result_unavailable")
        return finish(outcome, sid)
    safe_result, truncated = {}, []
    for key in RESULT_FIELDS:
        value = structured[key]
        if key in LIST_FIELDS:
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                outcome.update(status="failed", reason="structured_result_schema_invalid")
                return finish(outcome, sid)
            scrubbed = [scrub(v, limit=None) for v in value[:RESULT_LIST_LIMIT]]
            if any(len(v) > RESULT_STRING_LIMIT for v in scrubbed):
                truncated.append(key + "[element]")
            if len(value) > RESULT_LIST_LIMIT:
                truncated.append(key + "[entries]")
            safe_result[key] = [v[:RESULT_STRING_LIMIT] for v in scrubbed]
        else:
            if not isinstance(value, str):
                outcome.update(status="failed", reason="structured_result_schema_invalid")
                return finish(outcome, sid)
            scrubbed = scrub(value, limit=None)
            if len(scrubbed) > RESULT_STRING_LIMIT:
                truncated.append(key)
            safe_result[key] = scrubbed[:RESULT_STRING_LIMIT]
    if metadata["returned_session_id_status"] == "invalid":
        outcome.update(status="failed", reason="returned_session_id_invalid")
        return finish(outcome)
    # CLI completion stays distinct from delivery: truncated fields mean an incomplete result.
    outcome.update(status="complete", result=safe_result, result_complete=not truncated,
                   truncated_result_fields=truncated,
                   model_tests_independently_verified=False, session_available=sid is not None)
    return finish(outcome, sid)


def record_run(project, outcome, mode, version, session, before, after, started=None):
    ai = validate_ai(project)
    stamp = timestamp()
    metadata = {"timestamp": stamp, "mode": mode, "claude_version": version,
                "status": outcome["status"], "claude_exit_code": outcome.get("claude_exit_code"),
                "status_basis": "CLI result at evidence-write attempt; final local evidence/session/cache completion is reported by the run outcome.",
                "session_id": session,
                # An absent final-result field is unavailable evidence, never an implicit empty list.
                "permission_denials": outcome.get("permission_denials"),
                "permission_denials_status": outcome.get("permission_denials_status", "unavailable"),
                "actual_models": outcome.get("actual_models", []),
                "git_before": public_snapshot(before), "git_after": public_snapshot(after)}
    metadata.update({key: outcome[key] for key in EFFORT_AUDIT_FIELDS if key in outcome})
    metadata.update({key: outcome[key] for key in CONSULT_LOG_FIELDS if key in outcome})
    metadata.update({key: outcome[key] for key in RUN_LOG_FIELDS if key in outcome})
    metadata.setdefault("actual_models_status", "unavailable")
    directory = ai / "logs"
    secure_directory(directory)
    filename = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S") + "." + uuid.uuid4().hex[:8] + ".json"
    atomic_write(directory / filename, json.dumps(metadata, indent=2).encode("utf-8") + b"\n")
    handoff = ai / "HANDOFF.md"
    original = read_bytes(handoff)
    backup(ai, "HANDOFF", original)
    denial_status = outcome.get("permission_denials_status", "unavailable")
    denials = outcome.get("permission_denials") or []
    denial_text = denial_status + (" (" + ", ".join(denials) + ")" if denials else
                                   " (no final-result denial field; not treated as none)" if denial_status == "unavailable" else "")
    models_status = outcome.get("actual_models_status", "unavailable")
    block = ["", "<!-- claude-bridge:" + uuid.uuid4().hex + " -->",
             "## Claude Bridge evidence — " + stamp, "", "Current Status: " + outcome["status"],
             "Last Agent: Claude Code (" + mode + ", " + version + ")",
             "Requested effort: " + outcome.get("requested_effort", "unknown"),
             "Effort selection source: " + outcome.get("effort_source", "unknown"),
             "Effort selection reason: " + outcome.get("effort_reason", "not supplied"),
             "Effective effort: unknown (requested flag is not proof of the model's internal reasoning or silently applied caps).",
             "Effort local-file policy metadata: " + json.dumps(outcome.get("effort_policy", {}), sort_keys=True),
             "Actual model names from CLI: " + (", ".join(outcome.get("actual_models", [])) or "unknown") + " (" + models_status + ")",
             "Claude CLI exit code: " + str(outcome.get("claude_exit_code")),
             "Completion: " + ("CLI completed; project outcome needs independent verification." if outcome["status"] == "complete" else "Task not complete; final work state unknown until independently checked."),
             "Permission denials: " + denial_text,
             ("Session returned by CLI final result: " + session + " (reported; not saved unless status is complete)") if session
             else "Session returned by CLI final result: none; previous successful state retained",
             "Session persistence: sessions.json is authoritative; saved only after a successful evidence write.",
             "Git before: " + json.dumps(public_snapshot(before), sort_keys=True),
             "Git after: " + json.dumps(public_snapshot(after), sort_keys=True)]
    if outcome.get("cli_output"):
        block.append("CLI output diagnostics (counts and fixed codes only): " + json.dumps(outcome["cli_output"], sort_keys=True))
    if outcome.get("stream_events"):
        block.append("Stream events (counts only; no event text kept): " + json.dumps(outcome["stream_events"], sort_keys=True))
    if outcome.get("termination"):
        block.append("Forced termination: " + json.dumps(outcome["termination"], sort_keys=True))
    if "declared_outputs" in outcome:
        block.append("Declared outputs (observation only; no overwrite prevention, no file bodies): " + ", ".join(
            item["path"] + " " + item["change"] for item in outcome["declared_outputs"]))
        block.append("Declared output static Edit-rule check: " + ", ".join(
            item["path"] + " " + item["status"] for item in outcome["output_permission_preflight"]["targets"])
            + "; native CLI enforces effective permission.")
    if outcome.get("truncated_result_fields"):
        block.append("Result delivery: INCOMPLETE; truncated fields: " + ", ".join(outcome["truncated_result_fields"])
                     + ". Put long documents in files, not structured strings.")
    if outcome.get("result"):
        labels = {"Task": "Current Goal (Claude-reported)", "Summary": "Work Completed (Claude-reported)",
                  "FilesChanged": "Files Changed (Claude-reported)", "Tests": "Model-reported tests; not independently verified",
                  "Decisions": "Decisions Made (Claude-reported)", "RemainingIssues": "Known Issues (Claude-reported)",
                  "RecommendedNextStep": "Next Recommended Action (Claude-reported)"}
        for key in RESULT_FIELDS:
            value = outcome["result"][key]
            block.extend(["", "### " + labels[key]])
            block.extend(["- " + item for item in value] if isinstance(value, list) and value else [value if isinstance(value, str) and value else "none reported"])
    else:
        block.extend(["Known Issues: " + outcome.get("reason", "unknown"),
                      "Tests: unknown; no independent project test evidence.",
                      "Next Recommended Action: GPT inspect actual files and permissions; do not retry automatically."])
    block.append("<!-- /claude-bridge -->\n")
    atomic_write(handoff, original + (b"\n" if original and not original.endswith(b"\n") else b"") + "\n".join(block).encode("utf-8"))
    if outcome["status"] == "complete" and session:
        state = {"schema_version": 1, "project": str(project), "claude": {"session_id": session}}
        atomic_write(state_path(project), json.dumps(state, indent=2).encode("utf-8") + b"\n")
        # A later timing-log/cache write can fail after this successful save.
        # Keep its actual persistence distinct from whole-record completion.
        outcome["session_saved"] = True
    if started is not None:
        outcome["timings"]["total_through_record_ms"] = round((time.monotonic() - started) * 1000, 3)
        metadata["timings"] = outcome["timings"]
        metadata["session_saved"] = outcome.get("session_saved", False)
        # The endpoint measures completion of the evidence/session record above.
        # Persist that observed time afterward; do not invent first-token timing.
        atomic_write(directory / filename, json.dumps(metadata, indent=2).encode("utf-8") + b"\n")


def effort_request(args):
    if args.effort_source is not None and args.effort is None:
        raise Blocked("effort_source_requires_explicit_effort")
    effort = args.effort or "medium"
    source = args.effort_source or ("user" if args.effort is not None else "direct_default")
    if source == "auto" and effort not in {"medium", "high"}:
        raise Blocked("auto_effort_must_be_medium_or_high")
    raw_reason = args.effort_reason
    if raw_reason is not None:
        if len(raw_reason) > 160 or any(ord(char) < 32 or ord(char) == 127 or char in "\u2028\u2029" for char in raw_reason):
            raise Blocked("effort_reason_must_be_short_single_line")
        reason = scrub(raw_reason.strip(), 160)
    else:
        reason = ""
    if not reason:
        reason = {"direct_default": "Direct CLI default; no semantic effort selection supplied.",
                  "user": "Explicit effort selection.",
                  "auto": "Codex supplied the effort choice; no short reason supplied."}[source]
    return {"requested_effort": effort, "effort_source": source, "effort_reason": reason,
            "effective_effort": "unknown"}


def credits_guard(config, workflow):
    if config.get("subscription_usage_credits_disabled") is not True:
        raise Blocked("subscription_usage_credits_status_unconfirmed", {
            "next_step": "User must confirm extra usage credits are disabled before a subscription inference task."})
    if workflow == "consult":
        record = config.get("usage_credits_confirmation")
        try:
            valid = (isinstance(record, dict) and record.get("source") == "user"
                     and isinstance(record.get("date"), str)
                     and datetime.date.fromisoformat(record["date"]).isoformat() == record["date"])
        except ValueError:
            valid = False
        if not valid:
            raise Blocked("consult_usage_credits_user_confirmation_required")


def progress(args, event, **metadata):
    if args.progress:
        print(json.dumps({"event": event, "timestamp": timestamp(), **metadata},
                         ensure_ascii=False, separators=(",", ":")), file=sys.stderr, flush=True)


def validate_bounds(args):
    low, high = MAX_TURNS_RANGE
    if not low <= args.max_turns <= high:
        raise Blocked("max_turns_out_of_bounds", {"allowed_range": str(low) + ".." + str(high)})
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= TIMEOUT_MAX_SECONDS:
        raise Blocked("timeout_out_of_bounds", {"allowed_range": "0<seconds<=" + str(TIMEOUT_MAX_SECONDS)})


def execute(project, runtime, args):
    started = time.monotonic()
    validate_bounds(args)
    stream = bool(getattr(args, "stream_events", False))
    if stream and args.workflow == "consult":
        raise Blocked("stream_events_not_allowed_in_consult_workflow")
    outputs = validate_outputs(project, getattr(args, "outputs", None) or [], args.workflow)
    effort = effort_request(args)
    config, executable = runtime_config(runtime)
    validate_ai(project)
    if args.workflow == "consult":
        consult_cache_path(project)
    routes = route_guard(project)
    effort["effort_policy"] = routes["effort_policy"]
    previous = session_for(project, args.new_session)
    model = {"default": None, "sonnet": "sonnet", "opus": "opus", "review": "sonnet"}[args.mode]
    if args.dry_run:
        native_selection = "Claude Code native model selection"
        if previous:
            native_selection += "; resumed session may retain its prior model"
        before = git_snapshot(project, args.workflow == "consult", getattr(args, "task_path", None))
        if args.workflow == "consult":
            baseline = consult_cache(project, previous, args.mode)
            preview, _, delivery, changed, truncated = make_consult_prompt(project, args.task, args.mode, before, baseline)
        else:
            preview = make_prompt(project, args.task, args.mode, before)
            delivery, changed, truncated = "full", list(TEMPLATES) + ["Git"], []
        preview_result = {"status": "dry_run", "project": str(project), "mode": args.mode,
                "workflow": args.workflow,
                "context_delivery": delivery, "changed_context_names": changed,
                "truncated_context_names": truncated,
                "unavailable_context_names": ["Git"] if not before["available"] else [],
                "prompt_bytes": len(preview.encode("utf-8")), "resumed_session": previous,
                "model": model or native_selection, "resume_session": previous,
                "inference": False, "routing": routes, "prompt_sent": False, **effort}
        if stream:
            preview_result["stream_events"] = True
        if outputs:
            # Read-only static report; a real run blocks on an unready preflight.
            preview_result.update(declared_outputs=outputs,
                                  output_permission_preflight=output_permission_preflight(project, outputs))
        return preview_result, 0
    credits_guard(config, args.workflow)
    # Hold an advisory writer lock throughout validation, inference, and atomic state writes.
    with project_lock(project):
        # Recheck after obtaining the writer lock in case a preceding Bridge
        # task changed applicable settings after the initial preview scan.
        routes = route_guard(project)
        effort["effort_policy"] = routes["effort_policy"]
        previous = session_for(project, args.new_session)
        output_preflight = None
        if outputs:
            # Missing static coverage blocks before any CLI probe or inference.
            output_preflight = output_permission_preflight(project, outputs)
            if not output_preflight["ready"]:
                raise Blocked("declared_output_edit_permission_unconfirmed", {
                    "declared_outputs": outputs, "output_permission_preflight": output_preflight})
        baseline = consult_cache(project, previous, args.mode) if args.workflow == "consult" else None
        # Delete before attempting delivery: a crash, failed resume or partial
        # reply must never imply that the resumed model received this context.
        invalidate_consult_cache(project)
        command = [executable, "--print", "--output-format", "stream-json" if stream else "json", "--permission-mode", "manual",
                   "--permission-prompts", "none", "--max-turns", str(args.max_turns),
                   "--effort", effort["requested_effort"],
                   "--json-schema", json.dumps(SCHEMA, separators=(",", ":"))]
        if model:
            command += ["--model", model]
        if previous:
            command += ["--resume", previous]
        if args.workflow == "consult":
            command += ["--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                        "--system-prompt-snapshot", "off"]
        if stream:
            command.append("--verbose")  # official requirement for stream-json with --print
        version, unsupported = cli_info(executable, config, project, args.workflow, stream)
        if unsupported:
            raise Blocked("required_cli_flags_unverified", {"unsupported_flags": unsupported})
        auth = auth_status(executable, project)
        if not (auth["loggedIn"] and auth["authMethod"] == "claude.ai" and auth["subscriptionType"] in {"pro", "max"}):
            raise Blocked("native_pro_or_max_authentication_required", {"auth": auth})
        if args.workflow == "consult":
            ensure_ignore_patterns(project / ".ai", ("consult.json", "requests/"))
        before = git_snapshot(project, args.workflow == "consult", getattr(args, "task_path", None))
        fingerprints = None
        if args.workflow == "consult":
            prompt, fingerprints, delivery, changed, truncated = make_consult_prompt(project, args.task, args.mode, before, baseline)
            consult_request(project, args.task, args.mode, before, effort)
        else:
            prompt = make_prompt(project, args.task, args.mode, before)
            delivery, changed, truncated = "full", list(TEMPLATES) + ["Git"], []
        preflight = {"preflight_finished_at": timestamp(),
                     "preflight_wall_ms": round((time.monotonic() - started) * 1000, 3)}
        progress(args, "claude_start", workflow=args.workflow, mode=args.mode,
                 context_delivery=delivery, prompt_bytes=len(prompt.encode("utf-8")), resumed=bool(previous))
        outputs_before = observe_outputs(project, outputs) if outputs else None
        outcome, session = run_inference(command, prompt, project, args.timeout, stream)
        if outputs:
            # Observation only: no restore, no retry, no overwrite prevention, no sandbox.
            outcome.update(declared_outputs=output_observations(outputs, outputs_before, observe_outputs(project, outputs)),
                           output_permission_preflight=output_preflight,
                           output_observation={"kind": "observation_only", "restores_or_prevents_overwrites": False,
                                               "contents_recorded": False,
                                               "note": "Existence, bytes and bounded hashes only; existing declared outputs may be intentionally edited."})
        outcome.update(effort)
        outcome["timings"].update(preflight)
        outcome.update(workflow=args.workflow, context_delivery=delivery,
                       changed_context_names=changed, prompt_bytes=len(prompt.encode("utf-8")),
                       truncated_context_names=truncated,
                       unavailable_context_names=["Git"] if not before["available"] else [],
                       resumed_session=previous)
        after = before
        state_updated = False
        cache_saved = False
        outcome["session_saved"] = False
        original_status = outcome["status"]
        try:
            after = git_snapshot(project, args.workflow == "consult", getattr(args, "task_path", None))
            record_run(project, outcome, args.mode, version, session, before, after, started)
            state_updated = True
            if args.workflow == "consult" and original_status == "complete" and session:
                cache = {"schema_version": 1, "project": str(project), "mode": args.mode,
                         "session_id": session, "fingerprints": fingerprints}
                atomic_write(consult_cache_path(project), json.dumps(cache, indent=2).encode("utf-8") + b"\n")
                cache_saved = True
        except (Blocked, OSError, ValueError):
            outcome.update(status="state_update_failed",
                           inference_status=original_status,
                           reason="Model inference ran but local evidence/state/cache could not be saved; do not retry automatically.")
            try:
                invalidate_consult_cache(project)
            except (Blocked, OSError):
                outcome["cache_invalidation_failed"] = True
        outcome["timings"].setdefault("total_through_record_ms", round((time.monotonic() - started) * 1000, 3))
        outcome.update(project=str(project), mode=args.mode, claude_version=version,
                       auth=auth, session_id=session, resumed_session=previous,
                       git_before=public_snapshot(before), git_after=public_snapshot(after),
                       billing_source="native Claude.ai authentication; extra usage disabled per user confirmation",
                       api_fallback=False, inference=True, state_updated=state_updated,
                       session_saved=outcome["session_saved"],
                       consult_cache_saved=cache_saved,
                       status_basis="CLI result and local state writes; task and model-reported tests require independent verification")
        progress(args, "claude_finish", workflow=args.workflow, status=outcome["status"],
                 cli_wall_ms=outcome["timings"]["cli_wall_ms"],
                 total_through_record_ms=outcome["timings"]["total_through_record_ms"])
        return outcome, 0 if outcome["status"] == "complete" else 4


def parser():
    p = argparse.ArgumentParser(description="Native-subscription Claude Code bridge; no API fallback.")
    p.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME,
                   help="Runtime config with a pinned absolute Claude Code executable path.")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("init", "doctor", "run"):
        item = sub.add_parser(name)
        item.add_argument("--project", required=True, help="Explicit project directory; never inferred from CWD.")
        if name == "run":
            item.add_argument("--mode", choices=("default", "sonnet", "opus", "review"), default="default")
            item.add_argument("--workflow", choices=("standard", "consult"), default="standard")
            task = item.add_mutually_exclusive_group(required=True)
            task.add_argument("--task")
            task.add_argument("--task-file", help="UTF-8 regular file inside the explicit project; relative to project, no symlinks.")
            item.add_argument("--effort", choices=EFFORT_LEVELS,
                              help="Explicit native CLI effort request; direct CLI default is medium.")
            item.add_argument("--effort-source", choices=("auto", "user"),
                              help="Codex auto choice or explicit user choice; requires --effort.")
            item.add_argument("--effort-reason", help="Short audit reason: one line, at most 160 characters; no task text or secrets.")
            item.add_argument("--new-session", action="store_true", help="Explicit fresh session; no silent retry.")
            item.add_argument("--output", action="append", dest="outputs", metavar="PATH",
                              help="Host-declared output file, relative to the project; repeatable; standard workflow only. "
                                   "Needs a static exact Edit rule in confirmed local settings. Observed, not sandboxed.")
            item.add_argument("--stream-events", action="store_true",
                              help="Opt-in, standard workflow only: official stream-json (needs --verbose). Stops at the first "
                                   "explicit permission_denied event; keeps event counts only, never event text.")
            item.add_argument("--max-turns", type=int, default=3,
                              help="Integer 1..20 (default 3); other values are refused before inference.")
            item.add_argument("--timeout", type=float, default=120,
                              help="Finite seconds, 0<seconds<=3600 (default 120); other values are refused before inference.")
            item.add_argument("--dry-run", action="store_true", help="No inference, auth probe, prompt output or project writes.")
            item.add_argument("--progress", action="store_true", help="Safe start/finish metadata on stderr; stdout remains final JSON.")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        project = resolve_project(args.project)
        if args.command == "init":
            result, code = initialize(project), 0
        elif args.command == "doctor":
            result, code = doctor(project, args.runtime), 0
        else:
            args.task = task_text(project, args)
            result, code = execute(project, args.runtime, args)
        emit(result)
        return code
    except Blocked as error:
        emit({"status": "blocked", "reason": error.reason, **error.metadata,
              "inference": False, "api_fallback": False})
        return 3
    except (OSError, ValueError):
        # Filesystem exceptions and JSON errors can embed contents/credentials;
        # only fixed classifications are emitted.
        emit({"status": "blocked", "reason": "local_file_operation_failed",
              "inference": False, "api_fallback": False})
        return 3


if __name__ == "__main__":
    sys.exit(main())
