import { expect, test } from '@playwright/test';

test('read-only smoke test against running FastAPI and CognoDB', async ({ page }, info) => {
  test.setTimeout(90000);
  const errors: string[] = []; const writes: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', req => { if (req.url().includes('/api/') && req.method() !== 'GET') writes.push(req.url()); });
  await page.goto('/');
  await expect(page.locator('.stat-card').first().locator('strong')).toHaveText(/^\d+$/, { timeout: 45000 });
  await expect(page.locator('.coverage-number')).toBeVisible({ timeout: 45000 });
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.screenshot({ path: info.outputPath('live-dashboard.png'), fullPage: true });
  await page.getByLabel('Mở chi tiết dự án').click();
  await expect(page.getByRole('tab', { name: 'Đội ngũ' })).toBeVisible();
  await page.getByRole('tab', { name: 'Đội ngũ', exact: true }).click();
  await expect(page.locator('tbody tr').first()).toBeVisible();
  await page.getByRole('tab', { name: 'Yêu cầu kỹ năng', exact: true }).click();
  await expect(page.locator('tbody tr').first()).toBeVisible();
  await page.getByRole('navigation').getByRole('link', { name: 'Nhân viên' }).click();
  await expect(page.locator('tbody tr').first()).toBeVisible();
  await page.locator('.entity-link').first().click();
  await expect(page.getByRole('heading', { name: 'Hồ sơ kỹ năng' })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(errors).toEqual([]); expect(writes).toEqual([]);
});
