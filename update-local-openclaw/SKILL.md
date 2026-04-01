---
name: update-local-openclaw
description: Safely analyze and update a local OpenClaw installation with dry-run gates, background-friendly no-restart flow, restart fallback, rollback, and staged cleanup. Use when asked to check OpenClaw updates, perform one-click update, run update in background while keeping chat responsive, verify post-update health, or recover from failed upgrade.
---

# Update Local OpenClaw

Use this skill to update OpenClaw with stronger preflight gates, web + Telegram health checks, dry-run gating, restart fallback, rollback, and audit artifacts.

## What changed in this hardened version

Compared with the earlier version, this skill now adds:

- baseline safety gate: block if install method is unknown or mixed
- doctor hard-blocker gate before apply
- web health checks before apply / after apply / after restart
- stricter restart success criteria: Telegram + web must both recover
- clearer summary states: `SUCCESS | PARTIAL | BLOCKED | ROLLED_BACK`

## Quick start

Run full pipeline (foreground):

```bash
scripts/full_auto.sh --restart
```

Run full pipeline in background (recommended when user wants to keep chatting):

```bash
scripts/full_auto_bg.sh --restart
# then read progress from <run_dir>/progress.log
```

Analyze-only (no install changes):

```bash
RUN_DIR="$HOME/.openclaw/update-local-openclaw/runs/analyze-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN_DIR"
scripts/check_install_method.sh "$RUN_DIR"
scripts/assert_baseline_safe.sh "$RUN_DIR"
scripts/check_doctor_gate.sh "$RUN_DIR"
scripts/check_web_health.sh "$RUN_DIR" pre
python3 scripts/fetch_releases.py "$RUN_DIR"
scripts/run_update.sh --mode dry-run --run-dir "$RUN_DIR"
```

## Safety defaults

- Run analysis + dry-run before apply.
- Block update if install method is unknown/mixed unless manually fixed first.
- Block update if `openclaw doctor` exposes hard blockers.
- Apply updates with `--no-restart` first.
- Restart only after explicit confirmation unless user requested fully automatic mode.
- On restart failure, execute fallback (`restart -> stop/start -> doctor --fix -> rollback -> force-start gateway`).
- If `openclaw update` is skipped on package installs, auto-fallback to package-manager update (`pnpm`/`npm`) and run `openclaw doctor`.
- If bot comms are degraded, wait/retry until comms recover before continuing.
- During long-running steps, proactively report progress using stage markers from `progress.log`.

## Required health gates

### Telegram gate

The pipeline requires all Telegram bot accounts online:

- `baozi`
- `fugui`
- `rescue`

Checks run at:

- pre-update
- mid-update (`--no-restart` stage)
- post-restart

### Web gate

The pipeline also checks web gateway reachability:

- pre-update
- mid-update
- postcheck / restart validation

If Telegram or web gate fails, the pipeline must not report `SUCCESS`.

## Doctor hard blockers

Current hard blockers include matches such as:

- `token missing`
- `entrypoint missing`
- `service config mismatch`
- `multiple gateways`
- `state dir migration skipped`
- `target already exists`
- `config mismatch`

If any hard blocker is detected, the run exits as `BLOCKED` before apply.

## Fixed release sources

- Primary: `https://github.com/openclaw/openclaw/releases`
- Backup: `https://api.github.com/repos/openclaw/openclaw/releases`

If latest tags mismatch, stop unless `--force` is provided.

## Main command and flags

For interactive chats, prefer `full_auto_bg.sh` so the assistant can keep responding while update runs in background.

Preferred command:

```bash
scripts/full_auto.sh --restart
```

Useful flags:

- `--channel stable|beta|dev`
- `--tag <version-or-tag>`
- `--force`
- `--observe-minutes 10`
- `--comms-wait-seconds 600`
- `--comms-retry-interval 15`

## Manual pipeline (equivalent)

1. `scripts/check_install_method.sh <run_dir>`
2. `scripts/assert_baseline_safe.sh <run_dir>`
3. `scripts/check_doctor_gate.sh <run_dir>`
4. `scripts/check_bot_comms.sh <run_dir> pre`
5. `scripts/check_web_health.sh <run_dir> pre`
6. `python3 scripts/fetch_releases.py <run_dir>`
7. `scripts/snapshot.sh <run_dir>`
8. `scripts/run_update.sh --mode dry-run --run-dir <run_dir>`
9. `scripts/run_update.sh --mode apply --run-dir <run_dir> --no-restart`
10. `scripts/check_bot_comms.sh <run_dir> mid`
11. `scripts/check_web_health.sh <run_dir> mid`
12. `scripts/postcheck.sh <run_dir> <target_version> pending`
13. `scripts/restart_with_fallback.sh <run_dir>`
14. `scripts/postcheck.sh <run_dir> <target_version> done 10`
15. `scripts/check_bot_comms.sh <run_dir> post`
16. `scripts/run_summary.sh <run_dir>`
17. `scripts/cleanup.sh --mode now` then later `scripts/cleanup.sh --mode final`

## Artifacts

Stored in `~/.openclaw/update-local-openclaw/runs/<timestamp>/`:

- `baseline.json`
- `doctor-gate.json`
- `release-info.json`
- `dryrun.log`
- `update.log`
- `postcheck.json`
- `restart-state.json`
- `rollback-manifest.json`
- `comms-pre.json`
- `comms-mid.json`
- `comms-post.json`
- `web-pre.json`
- `web-mid.json`
- `web-postcheck.json`
- `web-restart.json`
- `cleanup-report.json`
- `run-summary.md`
- `progress.log`
- `progress.jsonl`
- `background.out.log` (when using bg launcher)
- `background.pid` (when using bg launcher)

## Completion criteria

Require all pass:

- target version reached
- `openclaw status` healthy
- `openclaw health` healthy
- smoke checks pass
- web health checks pass
- restart state is `done` or `rolled_back` (never plain failed)
- post-restart observation pass
- comms checks pass for pre/mid/post
- no doctor hard blocker before apply

If not all pass, return `PARTIAL`, `BLOCKED`, or `ROLLED_BACK`.

## Output format

Return concise summary:

- Status: `SUCCESS | PARTIAL | BLOCKED | ROLLED_BACK`
- From -> To version
- Risk level: `safe | caution | breaking`
- Restart state: `done | pending | failed | rolled_back`
- Comms: `pre/mid/post`
- Web: `pre/mid/post`
- Next action: one command
