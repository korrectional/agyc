---
description: Universal safeguards for autonomous coding agents, multi-instance concurrency, and Git workflows
trigger: always_on
---

# Autonomous Agent Safety & Concurrency Guidelines

## 1. Git Commit Ownership (No Host Background Commit Timers)
- **Agent Self-Commitments**: Never rely on a host-level periodic background timer to commit working directories while an agent is actively coding. Blind timer commits capture half-written files, dirty feature branches, and cause race conditions.
- **Prompt Mandate**: Instruct the agent explicitly in its prompt to stage, commit, and push its own work upon completing verified milestones:
  `git add . && git commit -m "<type>(<scope>): <summary>" && git push`
- **Stale Lock Recovery**: In automated Git pipelines, inspect for `.git/index.lock` before executing Git commands. If a lock is older than 10 seconds (abandoned by a killed or crashed process), purge it automatically before proceeding.

## 2. Resource-Aware Concurrency on Lightweight Machines
- **CPU & Memory Budgeting**: When orchestrating multi-instance agents on modest hardware (e.g. <= 4 vCPUs, <= 4GB RAM):
  - Avoid launching unthrottled simultaneous compiles or test suites.
  - Constrain build parallelism in compiler environments (e.g., set `CARGO_BUILD_JOBS=1`, `MAKEFLAGS="-j1"`, or `--jobs 1`).
  - Stagger worker initialization rather than dispatching 3+ heavy compiler tasks concurrently.
- **PTY & Non-Interactive Safety**: Always run terminal commands with `--no-pager` (e.g., `git --no-pager log`, `systemctl --no-pager`) and strict timeouts to prevent indefinite CLI hangs.

## 3. Atomic State Persistence & Crash Resiliency
- **Atomic Disk Writes**: Never overwrite state files directly with `open(..., "w")` followed by `json.dump()`. Sudden power loss, OOM kills, or Ctrl+C will truncate the file to 0 bytes.
- **Atomic Pattern**: Always write to a temporary file (`<file>.tmp`), flush buffers (`f.flush()`), sync to disk (`os.fsync(f.fileno())`), and replace atomically (`os.replace()`).
- **Resilient Loaders**: State loaders must gracefully recover if a file is missing or corrupted, falling back to `.tmp` or a safe default without crashing the host service.
