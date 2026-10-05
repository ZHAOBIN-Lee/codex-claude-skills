# Portable instructions and platform adapters

[简体中文](../COMPATIBILITY.md) · [English](COMPATIBILITY.md)

The goal is one Skill, preference convention, and tutorial set, with execution adapted by platform. Shared text does not establish runtime compatibility.

## Current implementation

The Bridge uses Python's standard library, `fcntl` locks, POSIX process groups and file permissions, and a macOS managed-settings path. The optional orchestrator uses its own YAML subset without a runtime PyYAML dependency. The declared Python minimum is 3.9; coverage of candidate versions needs the matrix below.

The official CLI tested in the existing environment is 2.1.285. Establish version, architecture, and integrity on each user's machine. Do not copy the author's ARM binary hash or call an arbitrary PATH executable official merely because its hash was calculated.

## Adapter work still required

| Capability | macOS / Linux approach | Native Windows work | Acceptance |
| --- | --- | --- | --- |
| Locate Python and CLI | Explicit installation paths, no author directories | Local absolute Python and official-CLI paths | Spaces, Unicode, symlinks, origin evidence |
| Project exclusion | POSIX locks | Windows locking adapter | Concurrent-call rejection and crash release |
| Timeout and cleanup | POSIX process groups | Windows process-tree handling | No orphan child processes or duplicate unknown-result retries |
| Private configuration | Unix permissions and no-symlink rules | ACL and reparse-point handling | Preserve existing protection |
| Managed settings | Applicable paths for each platform | Official Windows paths | Provider, authentication, and effort overrides |
| Time and paths | Explicit time zones and local path handling | Time-zone data and native paths | Do not assume a friend's location matches the author's |

**This is an implementation plan, not completed cross-platform support.** Do not label the current POSIX script native-Windows compatible. WSL needs its own path, project-scope, and host-call checks and does not establish native-Windows support.

## Validation matrix

1. Test failures, locks, paths, permissions, timeouts, and saving offline on each platform.
2. Check flags, subscription authentication, actual models, and session recovery for each candidate official-CLI version.
3. Install only the Skill directory from a fresh checkout and verify program, templates, license, and tutorials.
4. Record a user-authorized real consultation and follow-up separately on macOS, Linux/WSL, and native Windows.
5. Check tutorial/help routing in a fresh chat.

Offline CI does not establish real CLI or desktop acceptance. Do not bypass existing checks for an unknown CLI version merely because a user agrees; verify its capabilities first. See [official CLI setup](https://code.claude.com/docs/en/setup).
