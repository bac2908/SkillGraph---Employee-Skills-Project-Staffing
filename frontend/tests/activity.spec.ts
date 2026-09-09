import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mockApi } from './fixtures';

test('assignment edit records actor and before/after in project activity', async ({
  page,
}, info) => {
  await mockApi(page);
  await page.goto('/projects/PROJ001?tab=assignments');
  await page.getByRole('button', { name: 'Sửa phân công An Nguyen' }).click();
  await page.getByRole('dialog').getByLabel('Phân bổ (%)').fill('70');
  await page.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('tab', { name: 'Hoạt động', exact: true }).click();
  const item = page.locator('.activity-item').first();
  await expect(item).toContainText('Admin SkillGraph');
  await expect(item).toContainText('Đã cập nhật');
  await expect(item).toContainText('PROJ001/EMP002');
  await item.getByText('Xem thay đổi', { exact: true }).click();
  const row = item.getByRole('row').filter({ hasText: 'Phân bổ (%)' });
  await expect(row.getByRole('cell')).toHaveText(['80', '70']);
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: info.outputPath('project-activity-desktop.png'), fullPage: true });
});

test('history survives project deletion and filters work from the global page', async ({
  page,
}) => {
  await mockApi(page);
  await page.goto('/projects');
  await page.getByRole('button', { name: 'Thêm dự án' }).click();
  await page.getByLabel('Mã dự án').fill('PROJ999');
  await page.getByLabel('Tên dự án').fill('Audit demo');
  await page.getByLabel('Mô tả').fill('Activity lifecycle test');
  await page.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await page.getByRole('button', { name: 'Xóa Audit demo', exact: true }).click();
  await page.getByRole('button', { name: 'Xác nhận xóa' }).click();
  await page.getByRole('navigation').getByRole('link', { name: 'Hoạt động', exact: true }).click();
  await expect(page.locator('.activity-item')).toHaveCount(2);
  await page.getByLabel('Mã dự án', { exact: true }).fill('PROJ999');
  await page.getByRole('combobox', { name: 'Hành động', exact: true }).selectOption('DELETED');
  await page.getByLabel('Người thực hiện').fill('Admin');
  await page.getByRole('button', { name: 'Áp dụng bộ lọc' }).click();
  await expect(page.locator('.activity-item')).toHaveCount(1);
  await page.getByText('Xem thay đổi', { exact: true }).click();
  await expect(page.getByRole('row').filter({ hasText: 'Tên dự án' })).toContainText('Audit demo');
  await page.getByRole('button', { name: 'Xóa bộ lọc' }).click();
  await expect(page.locator('.activity-item')).toHaveCount(2);
});

for (const role of ['MANAGER', 'VIEWER'] as const) {
  test(`${role} cannot view history or trigger its API from UI`, async ({ page }) => {
    await mockApi(page, { role });
    const historyRequests: string[] = [];
    page.on('request', (request) => {
      if (request.url().includes('/api/activity')) historyRequests.push(request.url());
    });
    await page.goto('/projects/PROJ001?tab=activity');
    await expect(page.getByRole('tab', { name: 'Hoạt động', exact: true })).toHaveCount(0);
    await expect(
      page.getByRole('navigation').getByRole('link', { name: 'Hoạt động', exact: true }),
    ).toHaveCount(0);
    await page.goto('/activity');
    await expect(page.getByRole('heading', { name: 'Bạn không có quyền truy cập' })).toBeVisible();
    expect(historyRequests).toEqual([]);
  });
}

test('cursor navigation, time validation, mobile layout and escaped text', async ({
  page,
}, info) => {
  const fixture = await mockApi(page);
  fixture.activities.push(
    ...Array.from({ length: 23 }, (_, index) => ({
      event_id: `00000000-0000-0000-0000-${String(100 - index).padStart(12, '0')}`,
      occurred_at: new Date(Date.UTC(2026, 8, 10, 12, 0, 23 - index)).toISOString(),
      actor_id: 'USER001',
      actor_name: 'Admin SkillGraph',
      project_id: 'PROJ001',
      action: 'UPDATED' as const,
      resource_type: 'PROJECT' as const,
      resource_id: 'PROJ001',
      before: { name: `Version ${index}`, description: 'Old' },
      after: { name: 'New', description: '<img src=x onerror=alert(1)>' },
    })),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/activity');
  await expect(page.locator('.activity-item')).toHaveCount(20);
  await page.getByLabel('Hoạt động cũ hơn').click();
  await expect(page.locator('.activity-item')).toHaveCount(3);
  await expect(page.getByLabel('Hoạt động cũ hơn')).toBeDisabled();
  await page.getByLabel('Hoạt động mới hơn').click();
  await expect(page.locator('.activity-item')).toHaveCount(20);
  await page.locator('.activity-item').first().getByText('Xem thay đổi', { exact: true }).click();
  await expect(page.locator('.activity-item').first()).toContainText(
    '<img src=x onerror=alert(1)>',
  );
  await expect(page.locator('.activity-item img')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('activity-mobile.png'), fullPage: false });
  await page.getByLabel('Từ thời điểm').fill('2026-09-11T00:00');
  await page.getByLabel('Đến thời điểm').fill('2026-09-10T00:00');
  await page.getByRole('button', { name: 'Áp dụng bộ lọc' }).click();
  await expect(page.getByRole('alert')).toContainText('Thời gian bắt đầu');
  await page.getByRole('button', { name: 'Xóa bộ lọc' }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('empty history and database failure are explicit with retry', async ({ page }) => {
  await mockApi(page);
  let failing = true;
  await page.route('**/api/activity?*', (route) =>
    failing ? route.fulfill({ status: 503, body: 'Unavailable' }) : route.fallback(),
  );
  await page.goto('/activity');
  await expect(page.getByRole('alert')).toContainText('Kiểm tra backend');
  await expect(page.getByRole('heading', { name: 'Chưa có hoạt động phù hợp' })).toHaveCount(0);
  failing = false;
  await page.getByRole('button', { name: 'Thử lại' }).click();
  await expect(page.getByRole('heading', { name: 'Chưa có hoạt động phù hợp' })).toBeVisible();
  await expect(page.getByLabel('Hoạt động cũ hơn')).toBeDisabled();
});
