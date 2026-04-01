# OpenClaw adaptation

This directory is the thin OpenClaw shell around upstream gstack.

What it adds:
- `/build` as the OpenClaw user entrypoint
- role templates for `leader`, `builder`, `reviewer`, `qa`, `deploy`
- a starter `openclaw.example.json`

What it does **not** do:
- replace `office-hours`, `plan-ceo-review`, `plan-eng-review`, `review`, `qa`,
  `ship`, or `land-and-deploy`
- fork the upstream gstack workflow into a new methodology

## Install

1. Run:

```bash
./setup --host openclaw
```

2. Merge `openclaw/config/openclaw.example.json` into your OpenClaw config.

3. Create the agent workspaces and place the matching `AGENTS.md` in each
   agent workspace root:
- `leader`
- `builder`
- `reviewer`
- `qa`
- `deploy`

Suggested bootstrap commands:

```bash
openclaw agents add leader
openclaw agents add builder
openclaw agents add reviewer
openclaw agents add qa
openclaw agents add deploy
```

4. Restart OpenClaw so it reloads `~/.openclaw/skills`.

## Runtime model

Expected flow:

1. User runs `/build <goal>`
2. `leader` produces a spec using the installed gstack planning skills
3. User approves the spec
4. `leader` delegates build -> review -> qa -> deploy
5. Final delivery returns a public URL under `*.wangmz.dpdns.org`

## Current scope

Phase 1 supports publicly deployable Web apps only.
