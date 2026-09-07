import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mockApi } from './fixtures';

test.beforeEach(async ({ page }) => { await mockApi(page); });

test('dashboard displays API metrics, switches project and opens staffing dialog', async ({ page }, info) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Đúng người. Đúng cơ hội.' })).toBeVisible();
  await expect(page.locator('.stat-card').first().locator('strong')).toHaveText('12');
  await expect(page.locator('.coverage-number')).toHaveText('80%');
  await expect(page.locator('.candidate-card')).toHaveCount(2);
  await page.screenshot({ path: info.outputPath('dashboard-desktop.png'), fullPage: true });
  await page.getByLabel('Chọn dự án phân tích').selectOption('PROJ002');
  await expect(page.locator('.coverage-number')).toHaveText('100%');
  await expect(page.getByRole('heading', { name: 'Đội ngũ đã đáp ứng kỹ năng' })).toBeVisible();
  await page.getByLabel('Chọn dự án phân tích').selectOption('PROJ001');
  await page.getByRole('button', { name: 'Xem & phân công' }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.locator('.capacity-note strong')).toHaveText('20%');
  await dialog.getByLabel('Phân bổ (%)').fill('20');
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(dialog).not.toBeVisible();
  await page.goto('/projects/PROJ001?tab=assignments');
  await expect(page.getByRole('row').filter({ hasText: 'Nguyen Van Bac' })).toContainText('100%');
  expect(errors).toEqual([]);
});

test('skill create, edit, search and delete remain in sync with the API', async ({ page }) => {
  await page.goto('/skills');
  await page.getByRole('button', { name: 'Thêm kỹ năng' }).click();
  let dialog = page.getByRole('dialog');
  await dialog.getByLabel('Mã kỹ năng').fill('SK9001');
  await dialog.getByLabel('Tên kỹ năng').fill('Kubernetes');
  await dialog.getByLabel('Nhóm kỹ năng').fill('Cloud');
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(dialog).not.toBeVisible();
  await page.getByLabel('Tìm kỹ năng').fill('Kubernetes');
  const row = page.getByRole('row').filter({ hasText: 'Kubernetes' });
  await expect(row).toContainText('Cloud');
  await page.getByRole('button', { name: 'Sửa Kubernetes', exact: true }).click();
  dialog = page.getByRole('dialog');
  await expect(dialog.getByLabel('Mã kỹ năng')).toBeDisabled();
  await dialog.getByLabel('Nhóm kỹ năng').fill('DevOps');
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(row).toContainText('DevOps');
  await page.getByRole('button', { name: 'Xóa Kubernetes', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Xác nhận xóa' }).click();
  await expect(page.getByRole('heading', { name: 'Không có kết quả' })).toBeVisible();
});

test('employee and project forms, pagination and filters work', async ({ page }) => {
  await page.goto('/employees');
  await expect(page.locator('tbody tr')).toHaveCount(10);
  await page.getByLabel('Trang sau').click(); await expect(page.locator('tbody tr')).toHaveCount(2);
  await page.getByLabel('Lọc trạng thái').selectOption('AVAILABLE');
  await expect(page.locator('tbody tr')).toHaveCount(6);
  await page.getByRole('button', { name: 'Thêm nhân viên' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Mã nhân viên').fill('EMP999');
  await dialog.getByLabel('Họ và tên').fill('Test Engineer');
  await dialog.getByLabel('Email').fill('engineer@example.com');
  await dialog.getByLabel('Chức danh').fill('Platform Engineer');
  await dialog.getByLabel('Địa điểm').fill('Da Nang');
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(dialog).not.toBeVisible();
  await page.getByLabel('Tìm nhân viên').fill('Test Engineer');
  await page.getByRole('link', { name: 'Test Engineer', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Test Engineer' })).toBeVisible();
  await page.goto('/projects');
  await page.getByRole('button', { name: 'Thêm dự án' }).click();
  await page.getByLabel('Mã dự án').fill('PROJ999');
  await page.getByLabel('Tên dự án').fill('Developer Platform');
  await page.getByLabel('Mô tả').fill('Workspace integration project.');
  await page.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await page.getByRole('link', { name: 'Developer Platform', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Developer Platform' })).toBeVisible();
});

test('employee skills and project requirements create, update and remove', async ({ page }) => {
  for (const kind of ['employee', 'project']) {
    await page.goto(kind === 'employee' ? '/employees/EMP001' : '/projects/PROJ001?tab=requirements');
    await page.getByRole('button', { name: kind === 'employee' ? 'Gán kỹ năng' : 'Thêm yêu cầu', exact: true }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('Kỹ năng', { exact: false }).first().selectOption('SK007');
    await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
    await expect(dialog).not.toBeVisible();
    const row = page.getByRole('row').filter({ hasText: 'Docker' });
    await expect(row).toBeVisible();
    await row.getByRole('button', { name: 'Sửa Docker' }).click();
    await page.getByRole('dialog').getByRole('spinbutton').first().fill('4');
    await page.getByRole('dialog').getByRole('button', { name: 'Lưu thay đổi' }).click();
    await expect(row.getByLabel('Cấp 4/5')).toBeVisible();
    await row.getByRole('button', { name: 'Gỡ Docker' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Gỡ kỹ năng' }).click();
    await expect(row).not.toBeVisible();
  }
});

test('server allocation conflict keeps form values and supports retry', async ({ page }) => {
  await page.goto('/projects/PROJ001?tab=assignments');
  await page.getByRole('button', { name: 'Phân công', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Nhân viên').selectOption('EMP001');
  await dialog.getByLabel('Vai trò trong dự án').fill('Advisor');
  await dialog.getByLabel('Phân bổ (%)').fill('20');
  // Another request can consume capacity after the form fetched it.
  await page.route('**/api/projects/PROJ001/assignments/EMP001', async route => {
    if (route.request().method() === 'PUT') return route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ detail: 'Employee would exceed 100% allocation.' }) });
    return route.fallback();
  });
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(dialog.getByRole('alert')).toContainText('100%');
  await expect(dialog.getByLabel('Vai trò trong dự án')).toHaveValue('Advisor');
  await expect(dialog.getByRole('button', { name: 'Lưu thay đổi' })).toBeEnabled();
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await page.getByRole('button', { name: 'Sửa phân công An Nguyen' }).click();
  await expect(page.getByRole('dialog').getByLabel('Phân bổ (%)')).toHaveValue('80');
  await page.getByRole('dialog').getByLabel('Phân bổ (%)').fill('70');
  await page.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(page.getByRole('row').filter({ hasText: 'An Nguyen' })).toContainText('90%');
  await page.getByRole('button', { name: 'Gỡ phân công An Nguyen' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Gỡ phân công', exact: true }).click();
  await expect(page.getByRole('row').filter({ hasText: 'An Nguyen' })).not.toBeVisible();
});

test('mobile navigation, keyboard dialog and layout remain usable', async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.locator('.coverage-number')).toHaveText('80%');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('dashboard-mobile.png'), fullPage: true });
  await page.getByLabel('Mở menu').click();
  await page.getByRole('navigation').getByRole('link', { name: 'Kỹ năng' }).click();
  await page.getByRole('button', { name: 'Thêm kỹ năng' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => document.querySelector('dialog')?.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('backend failure is explicit, without fabricated dashboard data', async ({ page }) => {
  await page.route('**/api/**', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.goto('/');
  await expect(page.getByRole('alert').first()).toContainText('Kiểm tra backend');
  await expect(page.locator('.stat-card').first().locator('strong')).toHaveText('—');
  await expect(page.getByRole('button', { name: 'Thử lại' }).first()).toBeVisible();
});

test('dashboard and form pass automated accessibility checks', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.candidate-card')).toHaveCount(2);
  const check = async () => {
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(result.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => ({ target: n.target, summary: n.failureSummary })) }))).toEqual([]);
  };
  await check();
  await page.goto('/employees');
  await page.getByRole('button', { name: 'Thêm nhân viên' }).click();
  await check();
});
