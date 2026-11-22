#!/usr/bin/env node
/**
 * Hand the finished sheet to the judge.
 *
 * render.py is the only thing that draws: it writes entry.png next to itself.
 * This script does the one job Python cannot be trusted with on every
 * platform — copying that file into whatever directory the harness points at
 * ($MAKEFUN_OUTPUT_DIR) — and says so on one line.
 */
import { copyFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, 'entry.png');
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? here;
const target = join(outDir, 'entry.png');

if (!existsSync(source)) {
  console.error(`entry.png not found beside main.ts (${source}); run: python3 render.py`);
  process.exit(1);
}

mkdirSync(outDir, { recursive: true });

if (source !== target) {
  copyFileSync(source, target);
}

const { size } = statSync(target);
console.log(`entry.png → ${target} (${(size / 1024).toFixed(1)} KiB)`);
