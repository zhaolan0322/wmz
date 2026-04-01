#!/usr/bin/env bun
import { validateSkill } from '../test/helpers/skill-parser';
import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

const ROOT = path.resolve(import.meta.dir, '..');
const OPENCLAW_DIR = path.join(ROOT, '.openclaw', 'skills');
const BUN_BIN = process.execPath;

const SKILL_FILES = [
  'SKILL.md',
  'browse/SKILL.md',
  'qa/SKILL.md',
  'qa-only/SKILL.md',
  'ship/SKILL.md',
  'review/SKILL.md',
  'retro/SKILL.md',
  'plan-ceo-review/SKILL.md',
  'plan-eng-review/SKILL.md',
  'plan-design-review/SKILL.md',
  'design-review/SKILL.md',
  'design-consultation/SKILL.md',
  'office-hours/SKILL.md',
  'investigate/SKILL.md',
  'document-release/SKILL.md',
  'benchmark/SKILL.md',
  'canary/SKILL.md',
  'land-and-deploy/SKILL.md',
  'setup-browser-cookies/SKILL.md',
  'setup-deploy/SKILL.md',
  'gstack-upgrade/SKILL.md',
  'cso/SKILL.md',
  'openclaw/skills/build/SKILL.md',
].filter(file => fs.existsSync(path.join(ROOT, file)));

let hasErrors = false;

console.log('  Skills:');
for (const file of SKILL_FILES) {
  const result = validateSkill(path.join(ROOT, file));
  if (result.warnings.length > 0) {
    console.log(`  ⚠️  ${file.padEnd(30)} — ${result.warnings.join(', ')}`);
    continue;
  }

  if (result.invalid.length > 0 || result.snapshotFlagErrors.length > 0) {
    hasErrors = true;
    console.log(`  ❌ ${file.padEnd(30)} — ${result.invalid.length} invalid, ${result.snapshotFlagErrors.length} snapshot errors`);
    continue;
  }

  console.log(`  ✅ ${file.padEnd(30)} — ${result.valid.length} commands, all valid`);
}

console.log('\n  OpenClaw Skills (.openclaw/skills/):');
if (!fs.existsSync(OPENCLAW_DIR)) {
  hasErrors = true;
  console.log('  ❌ .openclaw/skills/ not found (run: bun run gen:skill-docs)');
} else {
  const generated = fs.readdirSync(OPENCLAW_DIR).sort();
  let count = 0;
  for (const dir of generated) {
    const skillMd = path.join(OPENCLAW_DIR, dir, 'SKILL.md');
    if (!fs.existsSync(skillMd)) {
      hasErrors = true;
      console.log(`  ❌ ${dir.padEnd(30)} — SKILL.md missing`);
      continue;
    }

    count++;
    const content = fs.readFileSync(skillMd, 'utf-8');
    if (content.includes('.claude/skills') || content.includes('.agents/skills') || content.includes('~/.codex/skills')) {
      hasErrors = true;
      console.log(`  ❌ ${dir.padEnd(30)} — contains non-OpenClaw path references`);
    } else {
      console.log(`  ✅ ${dir.padEnd(30)} — OK`);
    }
  }
  console.log(`  Total: ${count} skills`);
}

console.log('\n  Freshness (OpenClaw):');
try {
  execSync(`"${BUN_BIN}" run scripts/gen-skill-docs.ts --dry-run`, { cwd: ROOT, stdio: 'pipe' });
  console.log('  ✅ All generated files are fresh');
} catch (err: any) {
  hasErrors = true;
  const output = err.stdout?.toString() || '';
  console.log('  ❌ Generated files are stale:');
  for (const line of output.split('\n').filter((l: string) => l.startsWith('STALE'))) {
    console.log(`      ${line}`);
  }
  console.log('      Run: bun run gen:skill-docs');
}

console.log('');
process.exit(hasErrors ? 1 : 0);
