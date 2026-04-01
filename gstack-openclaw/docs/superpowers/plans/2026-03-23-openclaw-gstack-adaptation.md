# OpenClaw Gstack Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt `gstack` for OpenClaw with minimal divergence from upstream so OpenClaw can install gstack skills, expose a `/build` orchestration entrypoint, and run the existing gstack planning/review/QA/deploy workflow against Web app projects.

**Architecture:** Keep upstream gstack skills and generation flow intact. Extend the existing host-aware skill generator/setup script with a new `openclaw` host, then add an OpenClaw-only wrapper layer under `openclaw/` for `/build` and multi-agent configuration templates. The wrapper must reference and sequence existing gstack skills instead of replacing them.

**Tech Stack:** Bun TypeScript generator/tests, Bash setup script, OpenClaw AgentSkills-compatible `SKILL.md`, OpenClaw multi-agent config templates.

---

### Task 1: Add OpenClaw host generation support

**Files:**
- Modify: `E:\skill\gstack\scripts\gen-skill-docs.ts`
- Modify: `E:\skill\gstack\test\gen-skill-docs.test.ts`
- Modify: `E:\skill\gstack\test\skill-validation.test.ts`

- [ ] **Step 1: Write the failing tests for OpenClaw host generation**

Add tests that assert:
- `--host openclaw` is accepted.
- generated output lands under an OpenClaw-specific skill root.
- generated `SKILL.md` content uses `~/.openclaw/skills/gstack` / `skills/gstack` path semantics instead of Claude/Codex paths.

- [ ] **Step 2: Run the generator tests to verify they fail**

Run: `bun test test/gen-skill-docs.test.ts test/skill-validation.test.ts`
Expected: FAIL because `openclaw` host is not yet supported.

- [ ] **Step 3: Implement OpenClaw host support in the generator**

Update `scripts/gen-skill-docs.ts` to:
- add `openclaw` to the host union and parser
- define host path mappings
- generate OpenClaw runtime preamble variables
- emit OpenClaw output paths without disturbing Claude/Codex behavior

- [ ] **Step 4: Re-run the focused tests**

Run: `bun test test/gen-skill-docs.test.ts test/skill-validation.test.ts`
Expected: PASS for new OpenClaw host coverage.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-skill-docs.ts test/gen-skill-docs.test.ts test/skill-validation.test.ts
git commit -m "feat: add openclaw host skill generation"
```

### Task 2: Extend setup for OpenClaw installs

**Files:**
- Modify: `E:\skill\gstack\setup`
- Modify: `E:\skill\gstack\README.md`
- Test: `E:\skill\gstack\test\gen-skill-docs.test.ts`

- [ ] **Step 1: Write the failing setup/install assertions**

Add/extend tests to assert:
- `setup --host openclaw` is accepted.
- setup contains an OpenClaw install branch.
- setup links/generated skills into an OpenClaw runtime root.

- [ ] **Step 2: Run the relevant tests to verify they fail**

Run: `bun test test/gen-skill-docs.test.ts`
Expected: FAIL on missing `openclaw` setup/install logic.

- [ ] **Step 3: Implement OpenClaw setup support**

Update `setup` to:
- recognize `--host openclaw`
- detect `openclaw` in auto mode
- generate OpenClaw skill docs when needed
- create/link an OpenClaw runtime root under `~/.openclaw/skills/gstack`
- install the generated OpenClaw skills beside that runtime root

- [ ] **Step 4: Document the OpenClaw install flow**

Update `README.md` with:
- global OpenClaw install instructions
- local/OpenClaw-oriented adaptation note
- `/build` wrapper availability note once added

- [ ] **Step 5: Re-run the focused tests**

Run: `bun test test/gen-skill-docs.test.ts`
Expected: PASS on setup/install coverage.

- [ ] **Step 6: Commit**

```bash
git add setup README.md test/gen-skill-docs.test.ts
git commit -m "feat: support openclaw setup flow"
```

### Task 3: Add OpenClaw wrapper layer for `/build`

**Files:**
- Create: `E:\skill\gstack\openclaw\skills\build\SKILL.md`
- Create: `E:\skill\gstack\openclaw\agents\leader\AGENTS.md`
- Create: `E:\skill\gstack\openclaw\agents\builder\AGENTS.md`
- Create: `E:\skill\gstack\openclaw\agents\reviewer\AGENTS.md`
- Create: `E:\skill\gstack\openclaw\agents\qa\AGENTS.md`
- Create: `E:\skill\gstack\openclaw\agents\deploy\AGENTS.md`
- Create: `E:\skill\gstack\openclaw\config\openclaw.example.json`
- Create: `E:\skill\gstack\openclaw\README.md`

- [ ] **Step 1: Write the wrapper skill and agent template expectations**

Define the required behaviors in tests or checklist form before implementation:
- `/build` is user-invocable.
- it explicitly requires spec approval before implementation.
- it tells the leader to read and sequence existing gstack skills (`office-hours`, `plan-ceo-review`, `plan-eng-review`, `plan-design-review`, `review`, `qa`, `ship`, `land-and-deploy`) instead of replacing them.
- it uses OpenClaw `sessions_spawn` for builder/reviewer/qa/deploy delegation.

- [ ] **Step 2: Implement the `/build` skill**

Create an OpenClaw-only wrapper skill that:
- accepts raw build goals
- generates a spec using gstack planning skills first
- blocks for explicit approval
- after approval, delegates to the configured agents in order
- requires Cloudflare deployment and final public URL handoff

- [ ] **Step 3: Implement agent role templates**

Create per-agent `AGENTS.md` files that enforce hard role boundaries:
- leader: orchestration and approval gate
- builder: implementation only
- reviewer: blocking review gate
- qa: runtime/browser validation gate
- deploy: publish to Cloudflare and return URL

- [ ] **Step 4: Add a starter OpenClaw config**

Create `openclaw.example.json` with:
- agent list for `leader`, `builder`, `reviewer`, `qa`, `deploy`
- cross-agent spawn allowlists
- shared workspace/agentDir defaults
- comments for Cloudflare credentials and domain usage

- [ ] **Step 5: Add OpenClaw usage docs**

Document:
- where to place the wrapper skill/agent templates
- required OpenClaw config wiring
- expected `/build` lifecycle and approval checkpoint

- [ ] **Step 6: Commit**

```bash
git add openclaw
git commit -m "feat: add openclaw build orchestration wrapper"
```

### Task 4: Verify and regenerate

**Files:**
- Modify if needed: generated skill outputs
- Test: `E:\skill\gstack\test\gen-skill-docs.test.ts`
- Test: `E:\skill\gstack\test\skill-validation.test.ts`

- [ ] **Step 1: Regenerate host outputs**

Run:
- `bun run gen:skill-docs`
- `bun run gen:skill-docs --host codex`
- `bun run gen:skill-docs --host openclaw`

Expected: no generator errors.

- [ ] **Step 2: Run the non-eval test suite**

Run: `bun test browse/test/ test/ --ignore 'test/skill-e2e-*.test.ts' --ignore test/skill-llm-eval.test.ts --ignore test/skill-routing-e2e.test.ts --ignore test/codex-e2e.test.ts --ignore test/gemini-e2e.test.ts`
Expected: PASS.

- [ ] **Step 3: Smoke-check setup output**

Run:
- `bash ./setup --host openclaw`

Expected:
- OpenClaw runtime root created
- generated skills linked
- no Claude/Codex regressions in setup output

- [ ] **Step 4: Record any environment blockers**

If `bun`, Playwright, or OpenClaw binaries are unavailable, document the exact blocker and the unverified commands.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "test: verify openclaw gstack adaptation"
```

### Notes

- Keep upstream gstack skill bodies unchanged unless OpenClaw path/runtime assumptions make a direct fix unavoidable.
- Prefer adding OpenClaw-specific files under `openclaw/` over forking existing skill directories.
- Do not promise “arbitrary app types” in docs or wrapper prompts; first-phase scope is publicly deployable Web apps.
- Cloudflare deployment remains a wrapper concern; do not hardwire deploy secrets into upstream gstack templates.
