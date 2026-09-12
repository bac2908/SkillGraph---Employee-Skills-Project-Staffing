import { expect, test, type Page } from '@playwright/test';

// Synthetic credentials exist only in the isolated server's temporary SQLite.
const origin = 'http://127.0.0.1:5174';
const adminEmail = 'browser-admin@example.com';
const adminPassword = 'Browser-only initial password!';
const password = 'RBAC-only personal password 2026!';
const temporary = 'RBAC-only temporary password 2026!';
const finalPassword = 'RBAC-only changed password 2026!';

async function uiLogin(page: Page, email: string, secret = password, destination = '/projects') {
  await page.goto(destination);
  await expect(page.getByRole('heading', { name: 'Đăng nhập không gian của bạn' })).toBeVisible();
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(secret);
  const completed = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/auth/login') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  expect((await completed).status()).toBe(200);
}

async function authHeaders(page: Page) {
  const response = await page.request.get('/api/auth/me');
  expect(response.status()).toBe(200);
  return { Origin: origin, 'X-CSRF-Token': (await response.json()).csrf_token as string };
}

async function write(page: Page, method: string, path: string, data?: unknown) {
  return page.request.fetch(path, {
    method,
    headers: await authHeaders(page),
    ...(data === undefined ? {} : { data }),
  });
}

test.beforeEach(async ({ page }) => {
  // No page.route/mockApi: every /api request crosses Vite to real FastAPI.
  page.on('pageerror', (error) => {
    throw error;
  });
});

test('R01 anonymous: UI redirects and direct business API calls return 401', async ({ page }) => {
  await page.goto('/projects/PROJ101?tab=assignments');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.locator('.sidebar')).toHaveCount(0);
  for (const [method, path] of [
    ['GET', '/api/employees'],
    ['GET', '/api/projects'],
    ['GET', '/api/skills'],
    ['GET', '/api/dashboard'],
    ['GET', '/api/activity'],
    ['GET', '/api/auth/users'],
    ['POST', '/api/projects'],
    ['PATCH', '/api/projects/PROJ101'],
    ['DELETE', '/api/projects/PROJ101'],
  ]) {
    expect(
      (await page.request.fetch(path, { method, headers: { Origin: origin }, data: {} })).status(),
      `${method} ${path}`,
    ).toBe(401);
  }
});

test('R02 admin: project CRUD and account creation succeed through UI and API', async ({
  page,
}) => {
  await uiLogin(page, adminEmail, adminPassword);
  await expect(page.getByRole('button', { name: 'Thêm dự án', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Thêm dự án', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Mã dự án').fill('PROJ901');
  await dialog.getByLabel('Tên dự án').fill('RBAC Admin Created');
  await dialog.getByLabel('Mô tả').fill('Created through the real authorized API');
  const created = page.waitForResponse(
    (r) => r.url().endsWith('/api/projects') && r.request().method() === 'POST',
  );
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  expect((await created).status()).toBe(201);
  await expect(dialog).not.toBeVisible();
  expect((await (await page.request.get('/api/projects/PROJ901')).json()).name).toBe(
    'RBAC Admin Created',
  );
  await page.getByRole('button', { name: 'Sửa RBAC Admin Created', exact: true }).click();
  await dialog.getByLabel('Mô tả').fill('Updated by Admin');
  const updated = page.waitForResponse(
    (r) => r.url().endsWith('/api/projects/PROJ901') && r.request().method() === 'PATCH',
  );
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  expect((await updated).status()).toBe(200);
  await expect(dialog).not.toBeVisible();
  expect((await (await page.request.get('/api/projects/PROJ901')).json()).description).toBe(
    'Updated by Admin',
  );
  await page.getByRole('button', { name: 'Xóa RBAC Admin Created', exact: true }).click();
  const removed = page.waitForResponse(
    (r) => r.url().endsWith('/api/projects/PROJ901') && r.request().method() === 'DELETE',
  );
  await dialog.getByRole('button', { name: 'Xác nhận xóa' }).click();
  expect((await removed).status()).toBe(204);
  await expect(dialog).not.toBeVisible();
  expect((await page.request.get('/api/projects/PROJ901')).status()).toBe(404);
  await page.goto('/users');
  await page.getByRole('button', { name: 'Thêm tài khoản' }).click();
  await dialog.getByLabel('Họ tên').fill('RBAC Created Manager');
  await dialog.getByLabel('Email').fill('rbac-created-manager@example.com');
  await dialog.getByLabel('Mật khẩu tạm').fill(temporary);
  await dialog.getByLabel('Quyền truy cập').selectOption('MANAGER');
  await dialog.getByRole('checkbox', { name: /RBAC Granted Project/ }).check();
  const accountCreated = page.waitForResponse(
    (r) => r.url().endsWith('/api/auth/users') && r.request().method() === 'POST',
  );
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  const response = await accountCreated;
  expect(response.status()).toBe(201);
  expect(await response.json()).toMatchObject({
    role: 'MANAGER',
    project_ids: ['PROJ101'],
    must_change_password: true,
  });
  await expect(
    page.getByRole('row').filter({ hasText: 'rbac-created-manager@example.com' }),
  ).toContainText('PROJ101');
  await page.goto('/activity');
  await expect(page.getByRole('heading', { name: 'Mỗi thay đổi, một dấu vết.' })).toBeVisible();
  expect((await page.request.get('/api/activity')).status()).toBe(200);
});

test('R03 manager: granted edit succeeds; outside grant and admin pages are denied', async ({
  page,
}) => {
  await uiLogin(page, 'rbac-manager@example.com');
  await expect(
    page.getByRole('button', { name: 'Sửa RBAC Granted Project', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Sửa RBAC Other Project', exact: true }),
  ).toHaveCount(0);
  await expect(page.getByRole('button', { name: /^(Thêm|Xóa)/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Sửa RBAC Granted Project', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Mô tả').fill('Updated by granted Manager');
  const saved = page.waitForResponse(
    (r) => r.url().endsWith('/api/projects/PROJ101') && r.request().method() === 'PATCH',
  );
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  expect((await saved).status()).toBe(200);
  await expect(dialog).not.toBeVisible();
  expect((await (await page.request.get('/api/projects/PROJ101')).json()).description).toBe(
    'Updated by granted Manager',
  );
  const before = await (await page.request.get('/api/projects/PROJ102')).json();
  const denied = await write(page, 'PATCH', '/api/projects/PROJ102', {
    description: 'Forbidden edit',
  });
  expect(denied.status()).toBe(403);
  expect((await denied.json()).detail).toBe('Bạn không có quyền thay đổi dữ liệu này.');
  expect(await (await page.request.get('/api/projects/PROJ102')).json()).toEqual(before);
  for (const path of [
    '/api/projects/PROJ102/assignments/EMP101',
    '/api/projects/PROJ102/requirements/SK101',
  ]) {
    expect(
      (
        await write(
          page,
          'PUT',
          path,
          path.includes('assignments')
            ? { role: 'Developer', allocation: 10 }
            : { min_level: 3, priority: 'MUST' },
        )
      ).status(),
    ).toBe(403);
    expect((await write(page, 'DELETE', path)).status()).toBe(403);
  }
  expect(
    (
      await write(page, 'POST', '/api/projects', {
        project_id: 'PROJ909',
        name: 'Forbidden',
        description: 'Forbidden',
        status: 'PLANNING',
      })
    ).status(),
  ).toBe(403);
  expect((await write(page, 'DELETE', '/api/projects/PROJ101')).status()).toBe(403);
  await page.goto('/projects/PROJ101?tab=assignments');
  await expect(page.getByRole('button', { name: 'Phân công', exact: true })).toBeVisible();
  await page.goto('/projects/PROJ102?tab=assignments');
  await expect(
    page.getByRole('heading', { name: 'RBAC Other Project', exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: 'Phân công', exact: true })).toHaveCount(0);
  await expect(page.getByRole('tab', { name: 'Hoạt động', exact: true })).toHaveCount(0);
  for (const path of ['/users', '/activity']) {
    await page.goto(path);
    await expect(page.getByRole('heading', { name: 'Bạn không có quyền truy cập' })).toBeVisible();
  }
  expect((await page.request.get('/api/auth/users')).status()).toBe(403);
  expect((await page.request.get('/api/activity')).status()).toBe(403);
});

test('R04 viewer: real reads succeed; every business write method is rejected', async ({
  page,
}) => {
  await uiLogin(page, 'rbac-viewer@example.com', password, '/employees');
  await expect(page.getByRole('row').filter({ hasText: 'RBAC Employee' })).toBeVisible();
  await expect(page.getByRole('button', { name: /^(Thêm|Sửa|Xóa)/ })).toHaveCount(0);
  for (const [path, name] of [
    ['/projects', 'RBAC Granted Project'],
    ['/skills', 'RBAC Python'],
  ]) {
    await page.goto(path);
    await expect(page.getByRole('row').filter({ hasText: name })).toBeVisible();
    await expect(page.getByRole('button', { name: /^(Thêm|Sửa|Xóa)/ })).toHaveCount(0);
  }
  for (const path of [
    '/api/employees',
    '/api/skills',
    '/api/projects',
    '/api/dashboard',
    '/api/projects/PROJ101/skill-gap',
    '/api/projects/PROJ101/recommendations',
  ]) {
    expect((await page.request.get(path)).status(), path).toBe(200);
  }
  const before = await (await page.request.get('/api/projects/PROJ101')).json();
  const writes: [string, string, unknown?][] = [
    [
      'POST',
      '/api/employees',
      {
        employee_id: 'EMP909',
        name: 'Blocked',
        email: 'blocked@example.com',
        title: 'Developer',
        location: 'Test',
      },
    ],
    ['PATCH', '/api/employees/EMP101', { name: 'Blocked' }],
    ['DELETE', '/api/employees/EMP101'],
    ['PUT', '/api/employees/EMP101/skills/SK101', { level: 3, years_experience: 2 }],
    ['DELETE', '/api/employees/EMP101/skills/SK101'],
    ['POST', '/api/skills', { skill_id: 'SK909', name: 'Blocked', category: 'Test' }],
    ['PATCH', '/api/skills/SK101', { name: 'Blocked' }],
    ['DELETE', '/api/skills/SK101'],
    ['POST', '/api/projects', { project_id: 'PROJ909', name: 'Blocked', description: 'Blocked' }],
    ['PATCH', '/api/projects/PROJ101', { description: 'Blocked' }],
    ['DELETE', '/api/projects/PROJ101'],
    ['PUT', '/api/projects/PROJ101/assignments/EMP101', { role: 'Developer', allocation: 10 }],
    ['DELETE', '/api/projects/PROJ101/assignments/EMP101'],
    ['PUT', '/api/projects/PROJ101/requirements/SK101', { min_level: 3, priority: 'MUST' }],
    ['DELETE', '/api/projects/PROJ101/requirements/SK101'],
  ];
  for (const [method, path, data] of writes) {
    const response = await write(page, method, path, data);
    expect(response.status(), `${method} ${path}`).toBe(403);
    expect((await response.json()).detail).toBe('Bạn không có quyền thay đổi dữ liệu này.');
  }
  expect(await (await page.request.get('/api/projects/PROJ101')).json()).toEqual(before);
  const me = await (await page.request.get('/api/auth/me')).json();
  expect(
    (
      await write(page, 'PATCH', `/api/auth/users/${me.user.user_id}`, {
        role: 'ADMIN',
        is_active: true,
      })
    ).status(),
  ).toBe(403);
  for (const path of ['/users', '/activity']) {
    await page.goto(path);
    await expect(page.getByRole('heading', { name: 'Bạn không có quyền truy cập' })).toBeVisible();
  }
  expect((await page.request.get('/api/auth/users')).status()).toBe(403);
  expect((await page.request.get('/api/activity')).status()).toBe(403);
});

for (const action of ['locked', 'reset', 'regranted'] as const) {
  test(`R05-${action}: admin action revokes old session and clears the user's UI`, async ({
    page,
    browser,
  }) => {
    await uiLogin(page, `rbac-${action}@example.com`, password, '/employees');
    await expect(page.getByRole('row').filter({ hasText: 'RBAC Employee' })).toBeVisible();
    const before = await (await page.request.get('/api/auth/me')).json();
    const staleHeaders = await authHeaders(page);
    const operator = await browser.newContext({ baseURL: origin });
    try {
      const login = await operator.request.post('/api/auth/login', {
        headers: { Origin: origin },
        data: { email: adminEmail, password: adminPassword },
      });
      expect(login.status()).toBe(200);
      const adminSession = await login.json();
      const headers = { Origin: origin, 'X-CSRF-Token': adminSession.csrf_token };
      const path = `/api/auth/users/${before.user.user_id}`;
      if (action === 'reset') {
        expect(
          (
            await operator.request.post(path + '/password', {
              headers,
              data: { password: temporary },
            })
          ).status(),
        ).toBe(204);
      } else {
        expect(
          (
            await operator.request.patch(path, {
              headers,
              data: { role: 'VIEWER', is_active: action !== 'locked', project_ids: [] },
            })
          ).status(),
        ).toBe(200);
      }
      expect((await page.request.get('/api/auth/me')).status()).toBe(401);
      expect((await page.request.get('/api/employees')).status()).toBe(401);
      expect(
        (
          await page.request.patch('/api/projects/PROJ101', {
            headers: staleHeaders,
            data: { description: 'Stale session write' },
          })
        ).status(),
      ).toBe(401);
      await page.getByRole('button', { name: 'Làm mới dữ liệu', exact: true }).click();
      await expect(
        page.getByRole('heading', { name: 'Đăng nhập không gian của bạn' }),
      ).toBeVisible();
      await expect(page.locator('tbody tr')).toHaveCount(0);
      await expect(page.locator('.sidebar')).toHaveCount(0);
      if (action === 'locked' || action === 'reset') {
        const denied = await page.request.post('/api/auth/login', {
          headers: { Origin: origin },
          data: { email: before.user.email, password },
        });
        expect(denied.status()).toBe(401);
      } else {
        await uiLogin(page, before.user.email);
        await expect(page.getByRole('button', { name: /^(Thêm|Sửa|Xóa)/ })).toHaveCount(0);
        expect((await (await page.request.get('/api/auth/me')).json()).user.role).toBe('VIEWER');
        expect(
          (
            await write(page, 'PATCH', '/api/projects/PROJ101', { description: 'Old grant' })
          ).status(),
        ).toBe(403);
      }
    } finally {
      await operator.close();
    }
  });
}

for (const role of ['admin', 'manager', 'viewer']) {
  test(`R06-${role}: mandatory password change blocks UI and API until completed`, async ({
    page,
  }) => {
    const business: string[] = [];
    page.on('request', (request) => {
      if (request.url().includes('/api/') && !request.url().includes('/api/auth/'))
        business.push(request.url());
    });
    const email = `rbac-forced-${role}@example.com`;
    await uiLogin(page, email, temporary, '/projects/PROJ101?tab=assignments');
    await expect(page.getByRole('heading', { name: 'Tạo mật khẩu riêng của bạn' })).toBeVisible();
    await expect(page.locator('.sidebar')).toHaveCount(0);
    expect(business).toEqual([]);
    expect((await page.request.get('/api/projects')).status()).toBe(403);
    expect((await page.request.get('/api/auth/users')).status()).toBe(403);
    expect(
      (
        await write(page, 'PATCH', '/api/projects/PROJ101', { description: 'Before change' })
      ).status(),
    ).toBe(403);
    await page.getByLabel('Mật khẩu hiện tại').fill(temporary);
    await page.getByLabel('Mật khẩu mới', { exact: true }).fill(finalPassword);
    await page.getByLabel('Nhập lại mật khẩu mới').fill(finalPassword);
    await page.getByRole('button', { name: 'Đổi mật khẩu & đăng xuất' }).click();
    await expect(page.getByRole('status')).toContainText('Đã đổi mật khẩu');
    expect((await page.request.get('/api/auth/me')).status()).toBe(401);
    await uiLogin(page, email, finalPassword);
    await expect(page.getByRole('row').filter({ hasText: 'RBAC Granted Project' })).toBeVisible();
    expect((await page.request.get('/api/projects')).status()).toBe(200);
    const response = await (await page.request.get('/api/auth/me')).json();
    expect(response.user.must_change_password).toBe(false);
    expect(response.user.role).toBe(role.toUpperCase());
  });
}
