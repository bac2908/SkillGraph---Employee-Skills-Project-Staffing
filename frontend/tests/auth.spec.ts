import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mockApi } from './fixtures';

const password = 'Test-only password 2026!';

test('login protects deep links, validates credentials, persists on reload and logs out', async ({
  page,
}, info) => {
  await mockApi(page, { authenticated: false });
  await page.goto('/projects/PROJ001?tab=assignments');
  await expect(page.getByRole('heading', { name: 'Đăng nhập không gian của bạn' })).toBeVisible();
  await expect(page.locator('.sidebar')).toHaveCount(0);
  await page.screenshot({ path: info.outputPath('login-desktop.png'), fullPage: true });
  expect(
    (
      await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    ).violations.map((v) => v.id),
  ).toEqual([]);
  await page.getByLabel('Email', { exact: true }).fill('admin@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('wrong');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('không đúng');
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Hiện mật khẩu' }).click();
  await expect(page.getByLabel('Mật khẩu', { exact: true })).toHaveAttribute('type', 'text');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/\/projects\/PROJ001\?tab=assignments$/);
  await expect(page.getByRole('tab', { name: 'Đội ngũ' })).toHaveAttribute('aria-selected', 'true');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Phân công', exact: true })).toBeVisible();
  expect(
    await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
  ).toEqual({ local: 0, session: 0 });
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.locator('.sidebar')).toHaveCount(0);
});

test('viewer cannot see write controls or account administration', async ({ page }) => {
  await mockApi(page, { role: 'VIEWER' });
  await page.goto('/');
  await expect(page.locator('.coverage-number')).toHaveText('80%');
  await expect(page.getByRole('button', { name: 'Xem & phân công' })).toHaveCount(0);
  await expect(
    page.getByRole('navigation').getByRole('link', { name: 'Tài khoản', exact: true }),
  ).toHaveCount(0);
  await page.goto('/employees');
  await expect(page.locator('tbody tr')).toHaveCount(10);
  await expect(page.getByRole('button', { name: /^(Thêm|Sửa|Xóa)/ })).toHaveCount(0);
  await page.goto('/projects/PROJ001?tab=assignments');
  await expect(page.locator('tbody tr')).toHaveCount(2);
  await expect(page.getByRole('button', { name: /[Pp]hân công/ })).toHaveCount(0);
  await page.goto('/users');
  await expect(page.getByRole('heading', { name: 'Bạn không có quyền truy cập' })).toBeVisible();
});

test('manager controls only granted projects', async ({ page }) => {
  await mockApi(page, { role: 'MANAGER' });
  await page.goto('/projects');
  await expect(page.getByRole('button', { name: 'Sửa E-commerce Platform' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sửa Cloud Gaming Platform' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /^(Thêm|Xóa)/ })).toHaveCount(0);
  await page.goto('/projects/PROJ001?tab=assignments');
  await expect(page.getByRole('button', { name: 'Phân công', exact: true })).toBeVisible();
  await page.goto('/projects/PROJ002?tab=assignments');
  await expect(page.locator('tbody tr').first()).toBeVisible();
  await expect(page.getByRole('button', { name: /[Pp]hân công/ })).toHaveCount(0);
  await page.goto('/employees/EMP001');
  await expect(page.getByRole('heading', { name: 'Hồ sơ kỹ năng' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Gán kỹ năng' })).toHaveCount(0);
});

test('admin creates accounts, scopes grants, disables and resets passwords', async ({
  page,
}, info) => {
  await mockApi(page);
  await page.goto('/users');
  await page.getByRole('button', { name: 'Thêm tài khoản' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Họ tên').fill('Manager Demo');
  await dialog.getByLabel('Email').fill('manager@example.com');
  await dialog.getByLabel('Mật khẩu tạm').fill(password);
  await dialog.getByLabel('Quyền truy cập').selectOption('MANAGER');
  await dialog.getByRole('checkbox', { name: /E-commerce Platform/ }).check();
  expect(
    (
      await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    ).violations.map((v) => v.id),
  ).toEqual([]);
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  const row = page.getByRole('row').filter({ hasText: 'manager@example.com' });
  await expect(row).toContainText('PROJ001');
  await page.screenshot({ path: info.outputPath('user-administration.png'), fullPage: true });
  await page.getByRole('button', { name: 'Phân quyền Manager Demo' }).click();
  await dialog.getByLabel('Trạng thái tài khoản').selectOption('false');
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(row).toContainText('Đã khóa');
  await page.getByRole('button', { name: 'Đặt lại mật khẩu Manager Demo' }).click();
  await dialog.getByLabel('Mật khẩu tạm').fill('New temporary test password!');
  await dialog.getByRole('button', { name: 'Đặt lại mật khẩu', exact: true }).click();
  await expect(dialog).not.toBeVisible();
});

test('initial password must be changed before accessing workspace', async ({ page }) => {
  await mockApi(page, { mustChangePassword: true });
  const businessRequests: string[] = [];
  page.on('request', (req) => {
    if (req.url().includes('/api/') && !req.url().includes('/api/auth/'))
      businessRequests.push(req.url());
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Tạo mật khẩu riêng của bạn' })).toBeVisible();
  expect(businessRequests).toEqual([]);
  await page.getByLabel('Mật khẩu hiện tại').fill(password);
  await page.getByLabel('Mật khẩu mới', { exact: true }).fill('My new private test password!');
  await page.getByLabel('Nhập lại mật khẩu mới').fill('My new private test password!');
  await page.getByRole('button', { name: 'Đổi mật khẩu & đăng xuất' }).click();
  await expect(page.getByRole('status')).toContainText('Đã đổi mật khẩu');
  await expect(page).toHaveURL(/\/login$/);
});

test('expired session clears workspace and requests login', async ({ page }) => {
  const server = await mockApi(page);
  await page.goto('/employees');
  await expect(page.locator('tbody tr')).toHaveCount(10);
  server.expire();
  await page.getByRole('button', { name: 'Làm mới dữ liệu' }).click();
  await expect(page.getByRole('heading', { name: 'Đăng nhập không gian của bạn' })).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(0);
});

test('mobile login and account page fit viewport', async ({ page }, info) => {
  await mockApi(page, { authenticated: false });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/login');
  await expect(page.getByLabel('Email', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('login-mobile.png'), fullPage: true });
  await page.getByLabel('Email', { exact: true }).fill('admin@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await page.getByRole('link', { name: 'Tài khoản cá nhân', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'An toàn bắt đầu từ bạn' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
