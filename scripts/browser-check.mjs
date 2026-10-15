import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { chromium } = require('playwright');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const evidence = process.env.EVIDENCE_DIR || path.join(root, 'evidence');
await fs.mkdir(evidence, { recursive: true });

const base = process.env.APP_URL || 'http://127.0.0.1:3000';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));

const patientName = `Browser verification ${Date.now()}`;
let createdId;
const passed = [];

// The appointment form needs at least one doctor; make sure the clinic roster is present.
async function ensureDoctor() {
  const response = await context.request.get(`${base}/api/doctors`);
  const roster = await response.json();
  if (roster.length) return roster[0].id;
  const created = await context.request.post(`${base}/api/doctors`, {
    data: {
      full_name: 'Dr. Browser Check',
      department: 'general',
      specialization: 'Automated verification',
      active: true,
    },
  });
  assert.equal(created.status(), 201, 'seed doctor for the browser check');
  return (await created.json()).id;
}

async function loaded() {
  await page.getByRole('heading', { name: 'Appointment queue' }).waitFor();
  await page.getByRole('button', { name: 'Refresh appointments' }).waitFor();
  await page.waitForFunction(() => {
    const refresh = document.querySelector('button[aria-label="Refresh appointments"]');
    return refresh && !refresh.disabled && !document.querySelector('.queue-section [role="alert"]');
  });
}

try {
  const doctorId = await ensureDoctor();
  await page.goto(base);
  await loaded();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(evidence, 'application-desktop.png'), fullPage: true });
  assert(await page.locator('.clinic-image').evaluate(img => img.complete && img.naturalWidth > 0));
  passed.push('desktop render', 'clinic illustration loaded');

  await page.locator('.page-title').getByRole('button', { name: 'Book appointment', exact: true }).click();
  await page.getByLabel('Patient name', { exact: true }).fill(patientName);
  await page.getByLabel('Contact number', { exact: true }).fill('+91 90000 11111');
  await page.getByRole('combobox', { name: 'Doctor', exact: true }).selectOption(String(doctorId));
  await page.getByLabel('Date and time', { exact: true }).fill('2026-06-01T09:30');
  await page.getByRole('combobox', { name: 'Urgency', exact: true }).selectOption('urgent');
  await page.getByLabel('Reason for visit', { exact: true }).fill('Created and removed during a real Playwright CRUD check.');
  await page.screenshot({ path: path.join(evidence, 'appointment-create.png') });

  const created = page.waitForResponse(r => r.url().endsWith('/api/appointments') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirm booking', exact: true }).click();
  createdId = (await (await created).json()).id;
  await page.getByText('Appointment booked', { exact: true }).waitFor();
  passed.push('real create');

  await page.getByLabel('Search appointments').fill(patientName);
  await page.getByRole('button', { name: patientName, exact: true }).click();
  await page.getByRole('combobox', { name: 'Status', exact: true }).selectOption('completed');
  await page.getByLabel('Front-desk notes', { exact: true }).fill('Verified by the browser regression suite.');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.getByText('Appointment updated', { exact: true }).waitFor();
  passed.push('edit saved');

  await page.getByRole('button', { name: patientName, exact: true }).click();
  assert.equal(await page.getByRole('combobox', { name: 'Status', exact: true }).inputValue(), 'completed');
  passed.push('edit persisted');

  await page.getByRole('button', { name: 'Delete appointment', exact: true }).click();
  await page.locator('.delete-confirm').getByRole('button', { name: 'Delete appointment', exact: true }).click();
  await page.getByText('Appointment deleted', { exact: true }).waitFor();
  createdId = undefined;
  await page.getByRole('heading', { name: 'No matching appointments' }).waitFor();
  passed.push('delete');
  await page.getByLabel('Search appointments').fill('');
  await loaded();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByLabel('Search appointments').blur();
  await page.locator('.toast').waitFor({ state: 'hidden' });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: path.join(evidence, 'application-mobile.png'), fullPage: true });
  await page.locator('.page-title').getByRole('button', { name: 'Book appointment', exact: true }).click();
  assert(await page.locator('dialog').evaluate(el => el.getBoundingClientRect().right <= innerWidth));
  await page.screenshot({ path: path.join(evidence, 'appointment-mobile.png') });
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await page.locator('dialog').waitFor({ state: 'detached' });
  passed.push('mobile layout', 'mobile dialog', 'Escape-free dialog dismissal');

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.route('**/api/appointments?**', route => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Simulated outage for browser test' }),
  }));
  await page.getByRole('button', { name: 'Refresh appointments' }).click();
  await page.getByRole('heading', { name: 'Appointments could not be loaded' }).waitFor();
  assert(await page.getByRole('button', { name: 'Next page', exact: true }).isDisabled());
  await page.unroute('**/api/appointments?**');
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await loaded();
  assert.equal(await page.getByRole('heading', { name: 'Appointments could not be loaded' }).count(), 0);
  passed.push('error state, retry and disabled pagination on failure');

  // Pagination fixtures are intercepted test data, never deployment evidence.
  const rows = Array.from({ length: 24 }, (_, i) => ({
    id: 1000 + i,
    patient_name: `Pagination fixture ${i + 1}`,
    patient_phone: '+91 90000 00000',
    doctor_id: 1,
    doctor_name: 'Dr. Fixture',
    doctor_department: 'general',
    scheduled_for: '2026-01-01T00:00:00Z',
    reason: '',
    status: 'scheduled',
    urgency: 'routine',
    notes: '',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }));
  await page.route('**/api/appointments?**', route => {
    const params = new URL(route.request().url()).searchParams;
    const offset = Number(params.get('offset'));
    const limit = Number(params.get('limit'));
    return route.fulfill({ json: rows.slice(offset, offset + limit) });
  });
  await page.getByRole('button', { name: 'Refresh appointments' }).click();
  await page.getByRole('button', { name: 'Pagination fixture 1', exact: true }).waitFor();
  assert.equal(await page.locator('tbody tr').count(), 12);
  assert(await page.getByRole('button', { name: 'Next page', exact: true }).isEnabled());
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  await page.getByRole('button', { name: 'Pagination fixture 13', exact: true }).waitFor();
  assert.equal(await page.locator('tbody tr').count(), 12);
  assert(await page.getByRole('button', { name: 'Next page', exact: true }).isDisabled());
  await page.getByRole('button', { name: 'Previous page', exact: true }).click();
  await page.getByRole('button', { name: 'Pagination fixture 1', exact: true }).waitFor();
  await page.unroute('**/api/appointments?**');
  await page.getByRole('button', { name: 'Refresh appointments' }).click();
  await loaded();
  passed.push('pagination boundary (mocked rows)');

  for (const width of [320, 768, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    if (width === 768) {
      assert.equal(
        await page.getByRole('navigation', { name: 'Appointment navigation' })
          .getByRole('button', { name: 'All appointments', exact: true }).count(),
        1,
      );
    }
  }
  passed.push('320/768/1920px layout', 'accessible tablet navigation');

  await page.route('**/api/appointments?**', route => route.fulfill({ json: [] }));
  await page.getByRole('button', { name: 'Refresh appointments' }).click();
  await page.getByRole('heading', { name: 'The queue is clear', exact: true }).waitFor();
  assert.equal(await page.getByRole('button', { name: 'Book appointment', exact: true }).count(), 2);
  await page.locator('.page-title').getByRole('button', { name: 'Book appointment', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm booking', exact: true }).click();
  assert(await page.getByLabel('Patient name', { exact: true }).evaluate(input => !input.validity.valid));
  await page.keyboard.press('Escape');
  await page.locator('dialog').waitFor({ state: 'detached' });
  await page.unroute('**/api/appointments?**');
  passed.push('empty-queue actions', 'required-field validation', 'Escape closes dialog');

  assert.deepEqual(errors, []);
  passed.push('no JavaScript exceptions');

  const result = {
    capturedAt: new Date().toISOString(),
    base,
    passed,
    mocked: ['outage response', 'pagination rows', 'empty list'],
  };
  await fs.writeFile(path.join(evidence, 'browser-results.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  await page.screenshot({ path: path.join(evidence, 'browser-failure.png'), fullPage: true });
  throw error;
} finally {
  if (createdId) await context.request.delete(`${base}/api/appointments/${createdId}`);
  await browser.close();
}
