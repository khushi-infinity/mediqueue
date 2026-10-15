// Capture the provisioned Grafana dashboard as evidence.
// Requires GRAFANA_URL (default http://localhost:3001) and GRAFANA_PASSWORD.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { chromium } = require('playwright');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const evidence = process.env.EVIDENCE_DIR || path.join(root, 'evidence');
await fs.mkdir(evidence, { recursive: true });

const base = process.env.GRAFANA_URL || 'http://localhost:3001';
const password = process.env.GRAFANA_PASSWORD;
if (!password) {
  console.error('Set GRAFANA_PASSWORD (see scripts/grafana-password.sh) before running this capture.');
  process.exit(1);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
try {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
  await page.fill('input[name="user"]', 'admin');
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.goto(`${base}/d/mediqueue/mediqueue-service-health?from=now-30m&to=now&refresh=10s`, {
    waitUntil: 'domcontentloaded',
  });
  await page.getByText('Healthy backend replicas').waitFor({ timeout: 60000 });
  await page.waitForTimeout(8000);
  await page.screenshot({ path: path.join(evidence, 'grafana-dashboard.png'), fullPage: true });
  console.log(`Captured ${path.join(evidence, 'grafana-dashboard.png')}`);
} finally {
  await browser.close();
}
