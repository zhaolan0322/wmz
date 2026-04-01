import { describe, test, expect } from 'bun:test';
import { spawnSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

const ROOT = path.resolve(import.meta.dir, '..');
const BUN_BIN = process.execPath;

describe('runtime smoke', () => {
  test('browse binary exists after build', () => {
    const browseExe = path.join(ROOT, 'browse', 'dist', process.platform === 'win32' ? 'browse.exe' : 'browse');
    expect(fs.existsSync(browseExe)).toBe(true);
  });

  test('browse binary prints help', () => {
    const browseExe = path.join(ROOT, 'browse', 'dist', process.platform === 'win32' ? 'browse.exe' : 'browse');
    const result = spawnSync(browseExe, ['--help'], { encoding: 'utf-8', timeout: 10000 });
    expect(result.status).toBe(0);
    expect(result.stdout).toContain('Usage: browse');
  });

  test('global discover binary prints help', () => {
    const discoverExe = path.join(ROOT, 'bin', process.platform === 'win32' ? 'gstack-global-discover.exe' : 'gstack-global-discover');
    const result = spawnSync(discoverExe, ['--help'], { encoding: 'utf-8', timeout: 10000 });
    expect(result.status).toBe(0);
    expect(`${result.stdout}${result.stderr}`).toContain('Usage: gstack-global-discover');
  });

  test('OpenClaw skill generation is idempotent', () => {
    const result = Bun.spawnSync([BUN_BIN, 'run', 'scripts/gen-skill-docs.ts', '--dry-run'], {
      cwd: ROOT,
      stdout: 'pipe',
      stderr: 'pipe',
    });
    expect(result.exitCode).toBe(0);
    expect(result.stdout.toString()).toContain('FRESH:');
  });
});
