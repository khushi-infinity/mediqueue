// Render the captured transcripts in evidence/*.txt as terminal-style PNGs.
//
// The rubrics ask for screenshots of command output. The .txt files are the
// source of truth; these images are plain renderings of exactly that text, so a
// reviewer can see the output without opening a file. Nothing is retyped.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { chromium } = require('playwright');

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const evidence = path.join(root, 'evidence');
const outDir = path.join(evidence, 'screenshots');
await fs.mkdir(outDir, { recursive: true });

// Long outputs are capped so the image stays readable; the .txt keeps everything.
const MAX_LINES = 45;
const files = [
  'pytest.txt',
  'ruff.txt',
  'compose.txt',
  'compose-build.txt',
  'non-root.txt',
  'terraform-validate.txt',
  'helm.txt',
  'kubernetes.txt',
  'metrics.txt',
  'prometheus-targets.txt',
  'troubleshooting.txt',
  'argocd.txt',
  'commit-history.txt',
];

const escape = text =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function page(title, body, source) {
  return `<!doctype html>
<html><head><meta charset="utf-8"><style>
  * { box-sizing: border-box; }
  body { margin: 0; background: #08222a; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
  .win { width: 1120px; background: #0d2f36; border-radius: 12px; overflow: hidden; }
  .bar { height: 40px; display: flex; align-items: center; gap: 8px; padding: 0 16px; background: #12414a; }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .title { margin-left: 10px; color: #a7ded3; font: 13px ui-monospace, SFMono-Regular, Menlo, monospace; }
  pre { margin: 0; padding: 18px 20px; color: #e2f5f1;
        font: 13px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; white-space: pre-wrap; word-break: break-word; }
  .note { padding: 0 20px 16px; color: #7fb7ac; font: 12px ui-monospace, Menlo, monospace; }
</style></head><body>
  <div class="win">
    <div class="bar">
      <span class="dot" style="background:#ff5f57"></span>
      <span class="dot" style="background:#febc2e"></span>
      <span class="dot" style="background:#28c840"></span>
      <span class="title">${escape(title)}</span>
    </div>
    <pre>${escape(body)}</pre>
    <div class="note">rendered from evidence/${escape(source)}</div>
  </div>
</body></html>`;
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1160, height: 900 }, deviceScaleFactor: 2 });
const tab = await context.newPage();

const written = [];
for (const file of files) {
  const full = path.join(evidence, file);
  let text;
  try {
    text = await fs.readFile(full, 'utf8');
  } catch {
    console.warn(`skipping ${file}: not captured yet`);
    continue;
  }
  const lines = text.replace(/\s+$/, '').split('\n');
  const capped = lines.slice(0, MAX_LINES);
  const truncated = lines.length > MAX_LINES;
  const body = truncated
    ? `${capped.join('\n')}\n\n… ${lines.length - MAX_LINES} more lines in evidence/${file}`
    : capped.join('\n');

  const command = /^Command:\s*(.+)$/m.exec(text);
  const title = command ? command[1].trim() : file;

  await tab.setContent(page(title, body, file), { waitUntil: 'load' });
  const png = path.join(outDir, file.replace(/\.txt$/, '.png'));
  await tab.locator('.win').screenshot({ path: png });
  written.push(path.relative(root, png));
}

await browser.close();
console.log(`Rendered ${written.length} screenshots into evidence/screenshots/`);
for (const p of written) console.log(`  ${p}`);
