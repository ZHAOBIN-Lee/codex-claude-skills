# Platform compatibility and adapter plan

[简体中文](../COMPATIBILITY.md) · [English](COMPATIBILITY.md)

The idea is simple: the Skill instructions, preference conventions, and tutorials are shared across platforms, and only the layer that makes the call is adapted per OS. The text works anywhere. Whether the bundled scripts run on a given system has to be checked separately.

## Where things stand

The Bridge uses Python's standard library, `fcntl` file locks, POSIX process groups and file permissions, and it reads the macOS managed-settings path. The optional orchestrator ships its own small YAML-subset parser, so it needs no PyYAML at runtime. The declared Python minimum is 3.9; whether every version in range works is something the matrix below still has to confirm.

The official CLI used in real calls so far is 2.1.285, on the maintainer's macOS machine. Each user binds their own CLI path, version, architecture, and SHA-256 on their own machine:

- Don't copy the hash from the author's ARM machine.
- A hash you compute for some executable on your PATH doesn't show it came from Anthropic. Origin needs its own evidence.

## What each platform still needs

| Capability | macOS / Linux | Native Windows | Done when |
| --- | --- | --- | --- |
| Find Python and the CLI | Call from explicit install paths; no author directories | Absolute paths for local Python and the official CLI | Spaces, Unicode, and symlinks work; origin has evidence |
| One call per project | POSIX locks | A Windows locking adapter | A second concurrent call is refused; the lock is released after a crash |
| Timeout and cleanup | POSIX process groups | Windows process-tree handling | No orphaned children; unknown results aren't retried |
| Private config and permissions | Unix permissions; symlinks not followed | ACL and reparse-point handling | Porting doesn't weaken protection |
| Managed-settings check | The relevant path on each platform | Official Windows paths | Provider, authentication, and effort overrides are covered |
| Time and paths | Explicit time zones; platform path handling | Time-zone data and native paths | Don't assume a friend is in the author's time zone |

Read this table as a to-do list, not a list of what already works. The current POSIX scripts shouldn't be called native-Windows compatible. Running under WSL needs its own check of paths, project scope, and how the host calls the Bridge, and a working WSL setup says nothing about native Windows.

## Validation matrix

1. On each platform, run offline cases for failures, locks, paths, permissions, timeouts, and state saving.
2. For each official CLI version you want to support, check flags, subscription authentication, the model actually returned, and session recovery.
3. Install only the Skill directory from a fresh checkout and confirm the program, templates, license, and tutorials are all there.
4. On macOS, Linux/WSL, and native Windows, run one user-authorized real consultation plus a follow-up, and record each result separately.
5. In a fresh chat, check that a help request like "how do I use this?" reaches the tutorials.

Passing offline CI doesn't mean the real official CLI or the desktop app works. For a CLI version nobody has verified, check what it supports first; a user saying "go ahead" doesn't bypass the existing checks. For the systems the official CLI supports, see its [setup guide](https://code.claude.com/docs/en/setup).
