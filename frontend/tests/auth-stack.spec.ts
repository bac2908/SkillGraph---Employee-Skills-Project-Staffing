import { expect, test } from '@playwright/test';

test('real FastAPI cookie + CSRF + account lifecycle through Vite proxy', async ({
  page,
  context,
}) => {
  test.setTimeout(60000);
  const origin = 'http://127.0.0.1:5174';
  await page.goto('/users');
  await page.getByLabel('Email', { exact: true }).fill('browser-admin@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('Browser-only initial password!');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Đúng người, đúng quyền' })).toBeVisible();
  expect((await page.request.get('/api/activity')).status()).toBe(200);
  const cookie = (await context.cookies()).find((item) => item.name === 'skillgraph_session');
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe('Lax');
  expect(await page.evaluate(() => document.cookie)).not.toContain('skillgraph_session');
  const noCsrf = await page.request.post('/api/auth/logout', { headers: { Origin: origin } });
  expect(noCsrf.status()).toBe(403);
  const adminMe = await (await page.request.get('/api/auth/me')).json();
  const forged = await page.request.post('/api/auth/logout', {
    headers: { Origin: 'https://evil.example', 'X-CSRF-Token': adminMe.csrf_token },
  });
  expect(forged.status()).toBe(403);
  await page.getByRole('button', { name: 'Thêm tài khoản' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Họ tên').fill('Viewer Test');
  await dialog.getByLabel('Email').fill('browser-viewer@example.com');
  await dialog.getByLabel('Mật khẩu tạm').fill('Browser-only temporary password!');
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(
    page.getByRole('row').filter({ hasText: 'browser-viewer@example.com' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  expect((await page.request.get('/api/auth/me')).status()).toBe(401);
  await page.getByLabel('Email', { exact: true }).fill('browser-viewer@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('Browser-only temporary password!');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Tạo mật khẩu riêng của bạn' })).toBeVisible();
  await page.getByLabel('Mật khẩu hiện tại').fill('Browser-only temporary password!');
  await page.getByLabel('Mật khẩu mới', { exact: true }).fill('Browser-only personal password!');
  await page.getByLabel('Nhập lại mật khẩu mới').fill('Browser-only personal password!');
  await page.getByRole('button', { name: 'Đổi mật khẩu & đăng xuất' }).click();
  await expect(page.getByRole('status')).toContainText('Đã đổi mật khẩu');
  await page.getByLabel('Email', { exact: true }).fill('browser-viewer@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('Browser-only personal password!');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Đúng người. Đúng cơ hội.' })).toBeVisible();
  await expect(page.locator('.stat-card strong')).toHaveText(['0', '0', '0', '0']);
  const overview = await page.request.get('/api/dashboard');
  expect(overview.status()).toBe(200);
  expect((await overview.json()).default_project).toBeNull();
  const me = await (await page.request.get('/api/auth/me')).json();
  const denied = await page.request.post('/api/employees', {
    headers: { Origin: origin, 'X-CSRF-Token': me.csrf_token },
    data: {},
  });
  expect(denied.status()).toBe(403);
  expect((await page.request.get('/api/auth/users')).status()).toBe(403);
  expect((await page.request.get('/api/activity')).status()).toBe(403);
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  expect((await page.request.get('/api/employees')).status()).toBe(401);
  expect((await page.request.get('/api/dashboard')).status()).toBe(401);
});
