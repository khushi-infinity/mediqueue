// Capture the running dashboards as real browser screenshots.
//
//   PROMETHEUS_URL   default http://localhost:9090
//   ARGO_URL         default http://argocd.localhost:8088
//   ARGO_PASSWORD    required for the Argo CD pages (scripts/argocd-password.sh)
//   APP_URL          default http://mediqueue.localhost:8088
//   DASHBOARD_DIR    default evidence/dashboards
//   DASHBOARDS       comma-separated subset of prometheus,app,argo,github (default all)
//   GITHUB_REPO      default khushi-infinity/mediqueue, for the github section
//   GITHUB_RUN_ID    optional Actions run id to screenshot in detail
//
// Run a load test at the same time and the Prometheus graphs and Grafana
// panels show live traffic instead of a flat line. Capture 'argo' on its own
// afterwards: Argo CD serves a large JavaScript bundle, and a saturating load
// test on a single-node cluster can starve it past the timeouts.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { chromium } = require('playwright');

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = process.env.DASHBOARD_DIR || path.join(root, 'evidence', 'dashboards');
await fs.mkdir(outDir, { recursive: true });

const PROM = process.env.PROMETHEUS_URL || 'http://localhost:9090';
const ARGO = process.env.ARGO_URL || 'http://argocd.localhost:8088';
const APP = process.env.APP_URL || 'http://mediqueue.localhost:8088';
const argoUser = process.env.ARGO_USER || 'admin';
const argoPassword = process.env.ARGO_PASSWORD;

const sections = (process.env.DASHBOARDS || 'prometheus,app,argo,github')
  .split(',')
  .map(value => value.trim())
  .filter(Boolean);
const enabled = name => sections.includes('all') || sections.includes(name);

const results = [];
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1680, height: 1050 },
  deviceScaleFactor: 2,
});
const page = await context.newPage();

async function shot(file, label, url, prepare) {
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    if (prepare) await prepare();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(outDir, file), fullPage: true });
    results.push({ file, label, url, ok: true });
    console.log(`ok   ${file}`);
  } catch (error) {
    const reason = String(error).split('\n')[0];
    results.push({ file, label, url, ok: false, error: reason });
    console.warn(`FAIL ${file}: ${reason}`);
  }
}

const text = (value, timeout = 45000) =>
  page.getByText(value, { exact: false }).first().waitFor({ timeout });

// --- Prometheus -----------------------------------------------------------
if (enabled('prometheus')) {
  await shot('prometheus-targets.png', 'Prometheus /targets', `${PROM}/targets`, async () => {
    // Wait for an actual target row: the job group can render before its rows.
    await page.locator('tbody tr').first().waitFor({ timeout: 60000 });
    await text('mediqueue', 30000);
  });

  await shot(
    'prometheus-graph.png',
    'Prometheus /graph, request rate by route',
    `${PROM}/graph?g0.expr=${encodeURIComponent(
      'sum by (route) (rate(mediqueue_http_requests_total[5m]))',
    )}&g0.range_input=30m&g0.tab=0`,
    async () => {
      await text('Graph', 45000);
      await page.waitForTimeout(6000);
    },
  );

  await shot('prometheus-alerts.png', 'Prometheus /alerts', `${PROM}/alerts`, async () => {
    await text('MediQueue', 60000);
  });

  await shot('prometheus-rules.png', 'Prometheus /rules', `${PROM}/rules`, async () => {
    await text('MediQueueBackendUnavailable', 60000);
  });
}

// --- The application served through the Ingress ---------------------------
if (enabled('app')) {
  await shot('app-ingress.png', 'Application through the Ingress', `${APP}/`, async () => {
    await text('MediQueue', 60000);
    await page.waitForTimeout(3000);
  });
}

// --- Argo CD --------------------------------------------------------------
if (enabled('argo')) {
  if (!argoPassword) {
    console.warn('ARGO_PASSWORD not set: skipping the Argo CD pages');
  } else {
    let loggedIn = false;
    try {
      await page.goto(`${ARGO}/login`, { waitUntil: 'domcontentloaded', timeout: 90000 });
      // The login inputs carry no type attribute, so the CSS selector
      // input[type="text"] does not match the username field even though the
      // DOM property reads "text" (that is just the default). Match by role.
      await page.getByRole('textbox').first().fill(argoUser, { timeout: 90000 });
      await page.locator('input[type="password"]').first().fill(argoPassword, { timeout: 30000 });
      await page.getByRole('button', { name: /sign in/i }).click();
      await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 90000 });
      loggedIn = true;
    } catch (error) {
      console.warn(`Argo CD login failed: ${String(error).split('\n')[0]}`);
    }

    if (loggedIn) {
      await shot('argocd-applications.png', 'Argo CD applications', `${ARGO}/applications`, async () => {
        await text('mediqueue', 90000);
        await text('Synced', 90000);
      });

      await shot('argocd-mediqueue.png', 'Argo CD application detail', `${ARGO}/applications`, async () => {
        await text('mediqueue', 90000);
        // Argo CD renders the tiles with click handlers rather than anchors,
        // so there is no link role to target.
        await page.getByText('mediqueue', { exact: true }).first().click({ timeout: 60000 });
        await text('Synced', 90000);
        await text('Healthy', 90000);
        await page.waitForTimeout(5000);
      });
    }
  }
}

// --- GitHub ---------------------------------------------------------------
// The repository is public, so the run pages render without a session.
if (enabled('github')) {
  const ghRepo = process.env.GITHUB_REPO || 'khushi-infinity/mediqueue';
  const ghRunId = process.env.GITHUB_RUN_ID;

  await shot('github-repo.png', 'GitHub repository home', `https://github.com/${ghRepo}`, async () => {
    await text('MediQueue', 60000);
    await page.waitForTimeout(2500);
  });

  await shot('github-actions.png', 'GitHub Actions runs', `https://github.com/${ghRepo}/actions`, async () => {
    await text('MediQueue CI/CD', 60000);
    await page.waitForTimeout(2500);
  });

  if (ghRunId) {
    await shot(
      'github-run.png',
      'GitHub Actions run',
      `https://github.com/${ghRepo}/actions/runs/${ghRunId}`,
      async () => {
        await text('build-scan-deploy', 60000);
        await page.waitForTimeout(3000);
      },
    );
  }

  // Packages are private by default even for a public repository, so this one
  // is expected to need a session and is allowed to fail.
  await shot(
    'github-packages.png',
    'GHCR packages',
    `https://github.com/${ghRepo}/pkgs/container/mediqueue-backend`,
    async () => {
      await text('mediqueue-backend', 20000);
      await page.waitForTimeout(2000);
    },
  );
}

await browser.close();
await fs.writeFile(
  path.join(outDir, 'capture-results.json'),
  JSON.stringify({ capturedAt: new Date().toISOString(), results }, null, 2),
);
const failed = results.filter(r => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} dashboards captured into evidence/dashboards/`);
process.exit(failed === results.length ? 1 : 0);
