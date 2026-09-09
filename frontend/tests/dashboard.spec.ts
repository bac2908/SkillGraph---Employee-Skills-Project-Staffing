import { expect, test } from '@playwright/test';
import { mockApi } from './fixtures';
import type { DashboardOverview } from '../src/types';

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test('initial dashboard has a fixed request shape, no catalogue or per-project fan-out', async ({
  page,
}) => {
  const paths: string[] = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith('/api/') && !url.pathname.startsWith('/api/auth/'))
      paths.push(url.pathname);
  });
  // Large totals must come from the overview, not the five displayed people.
  await page.route('**/api/dashboard', (route) =>
    route.fulfill({
      json: {
        generated_at: new Date().toISOString(),
        summary: {
          employee_count: 1250,
          available_employee_count: 400,
          project_count: 250,
          active_project_count: 120,
          skill_count: 500,
        },
        capacity: [
          {
            employee_id: 'EMP001',
            name: 'Nguyen Van Bac',
            title: 'Engineer',
            total_allocation: 80,
            remaining_allocation: 20,
          },
        ],
        default_project: {
          project_id: 'PROJ001',
          name: 'E-commerce Platform',
          description: 'Test project',
          status: 'ACTIVE',
        },
      } satisfies DashboardOverview,
    }),
  );
  await page.goto('/');
  await expect(page.locator('.stat-card strong')).toHaveText(['1250', '400', '120', '500']);
  await expect(page.locator('.capacity-person')).toHaveCount(1);
  await expect(page.locator('.capacity-person')).toContainText('80%');
  await expect(page.locator('.coverage-number')).toHaveText('80%');
  await expect(page.locator('.candidate-card')).toHaveCount(2);
  expect([...new Set(paths)].sort()).toEqual([
    '/api/dashboard',
    '/api/projects/PROJ001/recommendations',
    '/api/projects/PROJ001/skill-gap',
  ]);
});

test('project picker paginates and searches beyond the first 100 projects', async ({
  page,
}, info) => {
  const requests: URL[] = [];
  const projects = Array.from({ length: 125 }, (_, index) => ({
    project_id: `PROJ${String(index + 1).padStart(3, '0')}`,
    name: `Dự án ${String(index + 1).padStart(3, '0')}`,
    description: 'Project picker test',
    status: 'ACTIVE',
  }));
  await page.route('**/api/projects?*', (route) => {
    const url = new URL(route.request().url());
    requests.push(url);
    const offset = Number(url.searchParams.get('offset'));
    const limit = Number(url.searchParams.get('limit'));
    const q = url.searchParams.get('q')?.toLowerCase() || '';
    const filtered = projects.filter((p) => `${p.project_id} ${p.name}`.toLowerCase().includes(q));
    return route.fulfill({
      json: {
        items: filtered.slice(offset, offset + limit),
        total: filtered.length,
        offset,
        limit,
      },
    });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const trigger = page.getByRole('button', { name: 'Chọn dự án phân tích' });
  await trigger.click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.locator('.project-search-result')).toHaveCount(10);
  await expect(dialog.getByLabel('Trang trước')).toBeDisabled();
  await dialog.getByLabel('Trang sau').click();
  await expect(dialog.getByRole('button', { name: 'Chọn Dự án 011' })).toBeVisible();
  await dialog.getByLabel('Tìm dự án phân tích').fill('PROJ125');
  await expect(dialog.locator('.project-search-result')).toHaveCount(1);
  await expect(dialog.getByRole('button', { name: 'Chọn Dự án 125' })).toBeVisible();
  await expect(dialog.getByLabel('Trang trước')).toBeDisabled();
  await expect(dialog.getByLabel('Trang sau')).toBeDisabled();
  expect(await dialog.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('project-picker-mobile.png'), fullPage: true });
  await dialog.getByRole('button', { name: 'Chọn Dự án 125' }).click();
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toContainText('Dự án 125');
  await expect(trigger).toBeFocused();
  await expect(page.getByLabel('Mở chi tiết dự án')).toHaveAttribute('href', '/projects/PROJ125');
  expect(requests.every((url) => url.searchParams.get('limit') === '10')).toBe(true);
  expect(requests.some((url) => url.searchParams.get('offset') === '10')).toBe(true);
  expect(
    requests.find((url) => url.searchParams.get('q') === 'PROJ125')?.searchParams.get('offset'),
  ).toBe('0');
});

test('picker empty result, failure and retry do not reset the selected project', async ({
  page,
}) => {
  await page.goto('/');
  const trigger = page.getByRole('button', { name: 'Chọn dự án phân tích' });
  await trigger.click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Tìm dự án phân tích').fill('no-matching-project');
  await expect(dialog.getByRole('heading', { name: 'Không tìm thấy dự án' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await expect(trigger).toContainText('E-commerce Platform');
  let failing = true;
  await page.route('**/api/projects?*', (route) =>
    failing ? route.fulfill({ status: 503, body: 'Unavailable' }) : route.fallback(),
  );
  await trigger.click();
  await dialog.getByLabel('Tìm dự án phân tích').fill('Cloud');
  await expect(dialog.getByRole('alert')).toBeVisible();
  failing = false;
  await dialog.getByRole('button', { name: 'Thử lại' }).click();
  await dialog.getByRole('button', { name: 'Chọn Cloud Gaming Platform' }).click();
  await expect(trigger).toContainText('Cloud Gaming Platform');
});

test('empty overview shows real zeros and does not fetch analysis', async ({ page }) => {
  const analysis: string[] = [];
  page.on('request', (request) => {
    if (/\/(skill-gap|recommendations)$/.test(request.url())) analysis.push(request.url());
  });
  await page.route('**/api/dashboard', (route) =>
    route.fulfill({
      json: {
        generated_at: new Date().toISOString(),
        summary: {
          employee_count: 0,
          available_employee_count: 0,
          project_count: 0,
          active_project_count: 0,
          skill_count: 0,
        },
        capacity: [],
        default_project: null,
      } satisfies DashboardOverview,
    }),
  );
  await page.goto('/');
  await expect(page.locator('.stat-card strong')).toHaveText(['0', '0', '0', '0']);
  await expect(page.getByRole('heading', { name: 'Dự án đầu tiên bắt đầu từ đây' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Chưa có nhân viên' })).toBeVisible();
  expect(analysis).toEqual([]);
});

test('failed overview retries without zero fallback and manual refresh refetches', async ({
  page,
}) => {
  let failing = true;
  let count = 0;
  await page.route('**/api/dashboard', (route) => {
    count++;
    return failing ? route.fulfill({ status: 503, body: 'Unavailable' }) : route.fallback();
  });
  await page.goto('/');
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.locator('.stat-card strong')).toHaveText(['—', '—', '—', '—']);
  failing = false;
  await page.getByRole('button', { name: 'Thử lại' }).click();
  await expect(page.locator('.stat-card strong').first()).toHaveText('12');
  await expect(page.locator('.capacity-person')).toHaveCount(5);
  const before = count;
  await page.getByRole('button', { name: 'Làm mới', exact: true }).click();
  await expect.poll(() => count).toBeGreaterThan(before);
});

test('saving a staffing change refreshes the overview without changing focus', async ({ page }) => {
  let count = 0;
  page.on('response', (response) => {
    if (new URL(response.url()).pathname === '/api/dashboard' && response.ok()) count++;
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Xem & phân công' }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.locator('.capacity-note strong')).toHaveText('20%');
  await dialog.getByLabel('Phân bổ (%)').fill('20');
  const before = count;
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(dialog).not.toBeVisible();
  await expect.poll(() => count).toBeGreaterThan(before);
  await expect(page.getByRole('button', { name: 'Chọn dự án phân tích' })).toContainText(
    'E-commerce Platform',
  );
});
