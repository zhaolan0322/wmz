import { describe, test, expect } from 'bun:test';
import { COMMAND_DESCRIPTIONS } from '../browse/src/commands';
import { SNAPSHOT_FLAGS } from '../browse/src/snapshot';
import * as fs from 'fs';
import * as path from 'path';

const ROOT = path.resolve(import.meta.dir, '..');
const BUN_BIN = process.execPath;
const OPENCLAW_DIR = path.join(ROOT, '.openclaw', 'skills');

const ALL_SKILLS = (() => {
  const skills: Array<{ dir: string; output: string }> = [];
  if (fs.existsSync(path.join(ROOT, 'SKILL.md.tmpl'))) {
    skills.push({ dir: '.', output: 'gstack' });
  }
  for (const entry of fs.readdirSync(ROOT, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith('.') || entry.name === 'node_modules' || entry.name === 'codex') continue;
    if (fs.existsSync(path.join(ROOT, entry.name, 'SKILL.md.tmpl'))) {
      const output = entry.name.startsWith('gstack-') ? entry.name : `gstack-${entry.name}`;
      skills.push({ dir: entry.name, output });
    }
  }
  return skills;
})();

describe('OpenClaw skill generation', () => {
  test('root generated SKILL.md contains browse command categories', () => {
    const content = fs.readFileSync(path.join(ROOT, 'SKILL.md'), 'utf-8');
    const categories = new Set(Object.values(COMMAND_DESCRIPTIONS).map(d => d.category));
    for (const category of categories) {
      expect(content).toContain(`### ${category}`);
    }
  });

  test('root generated SKILL.md contains snapshot flags', () => {
    const content = fs.readFileSync(path.join(ROOT, 'SKILL.md'), 'utf-8');
    for (const flag of SNAPSHOT_FLAGS) {
      expect(content).toContain(flag.short);
    }
  });

  test('OpenClaw output directory is generated for every skill template except codex', () => {
    for (const skill of ALL_SKILLS) {
      const skillMd = path.join(OPENCLAW_DIR, skill.output, 'SKILL.md');
      expect(fs.existsSync(skillMd)).toBe(true);
    }
  });

  test('generated OpenClaw skills do not contain legacy host markers', () => {
    for (const skill of ALL_SKILLS) {
      const content = fs.readFileSync(path.join(OPENCLAW_DIR, skill.output, 'SKILL.md'), 'utf-8');
      expect(content).not.toContain('~/.claude/skills');
      expect(content).not.toContain('.claude/skills');
      expect(content).not.toContain('~/.codex/skills');
      expect(content).not.toContain('.agents/skills');
      expect(content).not.toContain('CLAUDE.md');
      expect(content).not.toContain('/codex review');
    }
  });

  test('dry-run freshness passes for OpenClaw generation', () => {
    const result = Bun.spawnSync([BUN_BIN, 'run', 'scripts/gen-skill-docs.ts', '--dry-run'], {
      cwd: ROOT,
      stdout: 'pipe',
      stderr: 'pipe',
    });
    expect(result.exitCode).toBe(0);
    const output = result.stdout.toString().replaceAll('\\', '/');
    for (const skill of ALL_SKILLS) {
      expect(output).toContain(`FRESH: .openclaw/skills/${skill.output}/SKILL.md`);
    }
  });

  test('setup script is OpenClaw-only', () => {
    const content = fs.readFileSync(path.join(ROOT, 'setup'), 'utf-8');
    expect(content).toContain('expected openclaw');
    expect(content).toContain('$HOME/.openclaw/skills');
    expect(content).not.toContain('~/.claude/skills');
    expect(content).not.toContain('~/.codex/skills');
    expect(content).not.toContain('kiro');
  });
});
