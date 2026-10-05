---
id: TASK-000
title: Short imperative title
kind: task                  # task | rework
status: pending             # pending | ready | executing | validating | ready_for_review | reviewing | rework_required | blocked | done
risk: medium                # low | medium | high
complexity: 4               # 1-10
domains: []                 # e.g. [auth, payments]; checked against risk.force_strong_for
executor_tier: efficient    # Architect hint; only `strong` is honored as an upgrade
reviewer_tier: strong
auto_execute: true
rework_of: null             # parent task id for kind: rework
dependencies: []
---

# Objective

# Context
Files, modules and ADRs the Executor must read first (paths, not summaries).

# Scope
Allowed to modify:
-

Allowed to add:
-

# Non-Scope
Must not modify:
-

# Requirements
1.

# Implementation Guidance
-

# Acceptance Criteria
-

# Validation
```bash
# exact commands, run from the project root
```

# Escalation Conditions
Stop and escalate (write BLOCKERS.md) if:
-
