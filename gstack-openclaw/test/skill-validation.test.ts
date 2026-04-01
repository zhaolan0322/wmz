import { describe, test, expect } from 'bun:test';
import { validateSkill } from './helpers/skill-parser';
import * as fs from 'fs';
import * as path from 'path';

const ROOT = path.resolve(import.meta.dir, '..');
const BUN_BIN = process.execPath;
const OPENCLAW_DIR = path.join(ROOT, '.openclaw', 'skills');

describe('OpenClaw skill validation', () => {
  const skillFiles = [
    path.join(ROOT, 'SKILL.md'),
    path.join(ROOT, 'browse', 'SKILL.md'),
    path.join(ROOT, 'qa', 'SKILL.md'),
    path.join(ROOT, 'qa-only', 'SKILL.md'),
    path.join(ROOT, 'review', 'SKILL.md'),
    path.join(ROOT, 'ship', 'SKILL.md'),
    path.join(ROOT, 'land-and-deploy', 'SKILL.md'),
    path.join(ROOT, 'openclaw', 'skills', 'build', 'SKILL.md'),
  ];

  for (const file of skillFiles) {
    test(`${path.relative(ROOT, file)} has valid browse commands`, () => {
      const result = validateSkill(file);
      expect(result.invalid).toHaveLength(0);
      expect(result.snapshotFlagErrors).toHaveLength(0);
    });
  }

  test('OpenClaw wrapper assets exist', () => {
    expect(fs.existsSync(path.join(ROOT, 'openclaw', 'skills', 'build', 'SKILL.md'))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, 'openclaw', 'agents', 'leader', 'AGENTS.md'))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, 'openclaw', 'agents', 'builder', 'AGENTS.md'))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, 'openclaw', 'agents', 'reviewer', 'AGENTS.md'))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, 'openclaw', 'agents', 'qa', 'AGENTS.md'))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, 'openclaw', 'agents', 'deploy', 'AGENTS.md'))).toBe(true);
  });

  test('OpenClaw generated skills can be produced on demand', () => {
    const result = Bun.spawnSync([BUN_BIN, 'run', 'scripts/gen-skill-docs.ts'], {
      cwd: ROOT,
      stdout: 'pipe',
      stderr: 'pipe',
    });
    expect(result.exitCode).toBe(0);
    expect(fs.existsSync(OPENCLAW_DIR)).toBe(true);
  });

  test('OpenClaw generated skills have no non-OpenClaw install roots', () => {
    const dirs = fs.readdirSync(OPENCLAW_DIR);
    expect(dirs.length).toBeGreaterThan(0);
    for (const dir of dirs) {
      const skillMd = path.join(OPENCLAW_DIR, dir, 'SKILL.md');
      if (!fs.existsSync(skillMd)) continue;
      const content = fs.readFileSync(skillMd, 'utf-8');
      expect(content).not.toContain('.claude/skills');
      expect(content).not.toContain('.agents/skills');
      expect(content).not.toContain('~/.codex/skills');
      expect(content).not.toContain('CLAUDE.md');
      expect(content).not.toContain('/codex review');
    }
  });
});
