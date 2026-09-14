import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mockApi } from './fixtures';

// All fault injection/data below is browser-test-only; never uses live credentials/DB.
test.use({ trace: 'off', screenshot: 'off', video: 'off' });
const password = 'Test-only password 2026!';

async function skillDraft(page: Page) {
  await page.goto('/skills');
  await page.getByRole('button', { name: 'Thêm kỹ năng', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Mã kỹ năng').fill('SK990');
  await dialog.getByLabel('Tên kỹ năng').fill('Draft usability skill');
  await dialog.getByLabel('Nhóm kỹ năng').fill('Test only');
  return dialog;
}

test('login help is for ordinary users; wrong credentials preserve input and focus the error', async ({
  page,
}) => {
  await mockApi(page, { authenticated: false });
  await page.goto('/login');
  await expect(page.locator('.auth-help')).toContainText('quản trị viên');
  await expect(page.locator('.auth-help')).not.toContainText(/python|backend|scripts\./);
  await expect(page.getByRole('status')).toHaveCount(0); // Initial anonymous visit is not an expired session.
  await page.getByLabel('Email', { exact: true }).fill('admin@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('wrong');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Email hoặc mật khẩu không đúng.');
  await expect(page.getByRole('alert')).toBeFocused();
  await expect(page.getByLabel('Email', { exact: true })).toHaveValue('admin@example.com');
  await expect(page.getByLabel('Mật khẩu', { exact: true })).toHaveValue('wrong');
  await expect(page.getByRole('status')).toHaveCount(0);
});

for (const failure of ['network', 'unavailable', 'server'] as const) {
  test(`login ${failure} is not reported as wrong password and never exposes server detail`, async ({
    page,
  }) => {
    await mockApi(page, { authenticated: false });
    await page.goto('/login');
    await page.route('**/api/auth/login', (route) =>
      failure === 'network'
        ? route.abort('failed')
        : route.fulfill({
            status: failure === 'unavailable' ? 503 : 500,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'private-server-detail-must-not-render' }),
          }),
    );
    await page.getByLabel('Email', { exact: true }).fill('admin@example.com');
    await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    const text =
      failure === 'network'
        ? 'Không thể kết nối máy chủ'
        : failure === 'unavailable'
          ? 'tạm thời chưa sẵn sàng'
          : 'Hệ thống gặp lỗi';
    await expect(page.getByRole('alert')).toContainText(text);
    await expect(page.getByRole('alert')).not.toContainText(/không đúng|private-server-detail/);
    await expect(page.getByLabel('Mật khẩu', { exact: true })).toHaveValue(password);
  });
}

test('initial auth service unavailable blocks workspace and can retry without a false login failure', async ({
  page,
}) => {
  await mockApi(page, { authenticated: false });
  let unavailable = true;
  await page.route('**/api/auth/me', (route) =>
    unavailable ? route.fulfill({ status: 503, body: 'Unavailable' }) : route.fallback(),
  );
  await page.goto('/employees');
  await expect(page.getByRole('heading', { name: 'Kết nối không gian' })).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('tạm thời chưa sẵn sàng');
  await expect(page.locator('.sidebar')).toHaveCount(0);
  await expect(page.getByLabel('Mật khẩu', { exact: true })).toHaveCount(0);
  unavailable = false;
  await page.getByRole('button', { name: 'Thử lại', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Đăng nhập không gian của bạn' })).toBeVisible();
});

test('transient session check failure keeps an open draft; a later 401 still clears it', async ({
  page,
}) => {
  const fixture = await mockApi(page);
  const dialog = await skillDraft(page);
  let failed = true;
  await page.route('**/api/auth/me', (route) =>
    failed ? route.fulfill({ status: 503, body: 'Unavailable' }) : route.fallback(),
  );
  const checked = page.waitForResponse(
    (r) => r.url().endsWith('/api/auth/me') && r.status() === 503,
  );
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await checked;
  await expect(page.locator('#main > .error-notice')).toContainText('tạm thời chưa sẵn sàng');
  await expect(dialog.getByLabel('Tên kỹ năng')).toHaveValue('Draft usability skill');
  await expect(dialog.getByLabel('Nhóm kỹ năng')).toHaveValue('Test only');
  failed = false;
  const recovered = page.waitForResponse(
    (r) => r.url().endsWith('/api/auth/me') && r.status() === 200,
  );
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await recovered;
  await expect(page.locator('#main > .error-notice')).toHaveCount(0);
  await expect(dialog.getByLabel('Tên kỹ năng')).toHaveValue('Draft usability skill');
  fixture.expire();
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(page.getByRole('heading', { name: 'Đăng nhập không gian của bạn' })).toBeVisible();
  await expect(page.getByRole('status')).toContainText('hết hạn hoặc bị thu hồi');
  await expect(page.locator('.auth-notice')).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
});

for (const failure of ['conflict', 'validation', 'unavailable', 'network'] as const) {
  test(`save ${failure} keeps all draft fields, avoids automatic retries and supports deliberate retry`, async ({
    page,
  }) => {
    await mockApi(page);
    let count = 0;
    let fail = true;
    await page.route('**/api/skills', (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      count++;
      if (!fail) return route.fallback();
      if (failure === 'network') return route.abort('failed');
      return route.fulfill({
        status: failure === 'conflict' ? 409 : failure === 'validation' ? 422 : 503,
        contentType: 'application/json',
        body: JSON.stringify({
          detail:
            failure === 'conflict'
              ? 'Tên kỹ năng đã tồn tại.'
              : failure === 'validation'
                ? 'Vui lòng kiểm tra tên kỹ năng.'
                : 'private-detail',
        }),
      });
    });
    const dialog = await skillDraft(page);
    await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
    await expect(dialog.getByRole('alert')).toBeVisible();
    await expect(dialog.getByRole('alert')).toBeFocused();
    await expect(dialog.getByLabel('Mã kỹ năng')).toHaveValue('SK990');
    await expect(dialog.getByLabel('Tên kỹ năng')).toHaveValue('Draft usability skill');
    await expect(dialog.getByLabel('Nhóm kỹ năng')).toHaveValue('Test only');
    if (failure === 'unavailable' || failure === 'network')
      await expect(dialog.getByRole('alert')).toContainText('Chưa xác nhận được kết quả ghi');
    expect(count).toBe(1);
    fail = false;
    await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByRole('row').filter({ hasText: 'Draft usability skill' })).toHaveCount(1);
    expect(count).toBe(2);
  });
}

test('a timed-out write reports an unknown result, preserves input and does not retry itself', async ({
  page,
}) => {
  await mockApi(page);
  const dialog = await skillDraft(page);
  await page.clock.install();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let writes = 0;
  await page.route('**/api/skills', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    writes++;
    await gate;
    await route.abort('failed');
  });
  try {
    await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
    await expect.poll(() => writes).toBe(1);
    await page.clock.fastForward(31000);
    await expect(dialog.getByRole('alert')).toContainText('quá thời gian chờ');
    await expect(dialog.getByRole('alert')).toContainText('Chưa xác nhận được kết quả ghi');
    await expect(dialog.getByLabel('Tên kỹ năng')).toHaveValue('Draft usability skill');
    expect(writes).toBe(1);
  } finally {
    release();
  }
});

test('rapid saves submit once; pending fields, close and Escape stay locked', async ({ page }) => {
  await mockApi(page);
  const dialog = await skillDraft(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let writes = 0;
  await page.route('**/api/skills', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    writes++;
    await gate;
    await route.fallback();
  });
  try {
    await dialog.locator('form').evaluate((form: HTMLFormElement) => {
      form.requestSubmit();
      form.requestSubmit();
    });
    await expect.poll(() => writes).toBe(1);
    await expect(dialog.getByLabel('Tên kỹ năng')).toBeDisabled();
    await expect(dialog.getByRole('button', { name: 'Đang lưu…' })).toBeDisabled();
    await expect(dialog.getByRole('button', { name: 'Đóng biểu mẫu' })).toBeDisabled();
    await page.keyboard.press('Escape');
    await expect(dialog).toBeVisible();
  } finally {
    release();
  }
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: 'Draft usability skill' })).toHaveCount(1);
  expect(writes).toBe(1);
});

test('rapid login submits once and keeps credentials disabled until the response', async ({
  page,
}) => {
  await mockApi(page, { authenticated: false });
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('admin@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let logins = 0;
  await page.route('**/api/auth/login', async (route) => {
    logins++;
    await gate;
    await route.fallback();
  });
  try {
    await page.locator('.auth-form').evaluate((form: HTMLFormElement) => {
      form.requestSubmit();
      form.requestSubmit();
    });
    await expect.poll(() => logins).toBe(1);
    await expect(page.getByLabel('Mật khẩu', { exact: true })).toBeDisabled();
  } finally {
    release();
  }
  await expect(page.locator('.sidebar')).toBeVisible();
  expect(logins).toBe(1);
});

test('delete requires confirmation, Escape/Cancel are safe and linked-record errors are understandable', async ({
  page,
}) => {
  await mockApi(page);
  let deletes = 0;
  await page.route('**/api/skills/SK001', (route) => {
    if (route.request().method() !== 'DELETE') return route.fallback();
    deletes++;
    return route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: "Skill 'SK001' is connected by 2 relationship(s) and cannot be deleted.",
      }),
    });
  });
  await page.goto('/skills');
  const trigger = page.getByRole('button', { name: 'Xóa Python', exact: true });
  await trigger.click();
  await expect(page.getByRole('dialog')).toContainText('Xóa Python?');
  expect(deletes).toBe(0);
  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByRole('dialog').getByRole('button', { name: 'Hủy', exact: true }).click();
  expect(deletes).toBe(0);
  await trigger.click();
  await page.getByRole('dialog').getByRole('button', { name: 'Xác nhận xóa' }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('2 liên kết');
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText(
    'gỡ liên kết trước khi xóa',
  );
  expect(deletes).toBe(1);
});

test('allocation conflict translates the real backend message without losing role or percentage', async ({
  page,
}) => {
  await mockApi(page);
  await page.route('**/api/projects/PROJ001/assignments/EMP001', (route) =>
    route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({
        detail:
          "Employee 'EMP001' would reach 110% total allocation: 90% outside Project 'PROJ001' plus 20% requested. The maximum is 100%.",
      }),
    }),
  );
  await page.goto('/projects/PROJ001?tab=assignments');
  await page.getByRole('button', { name: 'Phân công', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Nhân viên', { exact: true }).selectOption('EMP001');
  await dialog.getByLabel('Vai trò trong dự án').fill('Advisor');
  await dialog.getByLabel('Phân bổ (%)').fill('20');
  await dialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
  await expect(dialog.getByRole('alert')).toContainText('Tổng phân bổ sẽ là 110%');
  await expect(dialog.getByRole('alert')).toContainText('Giới hạn là 100%');
  await expect(dialog.getByLabel('Vai trò trong dự án')).toHaveValue('Advisor');
  await expect(dialog.getByLabel('Phân bổ (%)')).toHaveValue('20');
});

test('mobile candidate may be AVAILABLE but fully allocated: explain it and block saving', async ({
  page,
}, info) => {
  await mockApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/projects/PROJ002/assignments', (route) =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        total: 1,
        items: [
          {
            employee_id: 'EMP001',
            employee_name: 'Nguyen Van Bac',
            project_id: 'PROJ002',
            project_name: 'Cloud Gaming Platform',
            role: 'Developer',
            allocation: 100,
            employee_total_allocation: 100,
            employee_remaining_allocation: 0,
          },
        ],
      }),
    }),
  );
  await page.goto('/');
  await expect(page.locator('.recommendations .workflow-note')).toContainText(
    'Gợi ý chưa lọc theo allocation còn lại',
  );
  await page.getByRole('button', { name: 'Kiểm tra phân bổ' }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.locator('.capacity-note strong')).toHaveText('0%');
  await expect(dialog).toContainText('Nhân viên đã được phân bổ đủ 100%');
  await expect(dialog.getByRole('button', { name: 'Lưu thay đổi' })).toBeDisabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: info.outputPath('capacity-mobile.png'), fullPage: true });
  await page.keyboard.press('Escape');
  await page.goto('/employees/EMP001');
  await expect(page.locator('.profile-heading')).toContainText('Sẵn sàng');
  await expect(page.locator('.profile-meta')).toContainText('100% đã phân bổ · còn 0%');
  await expect(page.locator('.workflow-note')).toContainText(
    'không đồng nghĩa còn dung lượng nhận việc',
  );
});

test('employee selection updates capacity and allows choosing another person without losing typed role', async ({
  page,
}) => {
  await mockApi(page);
  await page.goto('/projects/PROJ003?tab=assignments');
  await page.getByRole('button', { name: 'Phân công', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Nhân viên', { exact: true }).selectOption('EMP002');
  await expect(dialog.locator('.capacity-note strong')).toHaveText('0%');
  await expect(dialog.getByRole('button', { name: 'Lưu thay đổi' })).toBeDisabled();
  await dialog.getByLabel('Vai trò trong dự án').fill('Draft advisor');
  await dialog.getByLabel('Nhân viên', { exact: true }).selectOption('EMP001');
  await expect(dialog.locator('.capacity-note strong')).toHaveText('20%');
  await expect(dialog.getByLabel('Nhân viên', { exact: true })).toBeEnabled();
  await expect(dialog.getByLabel('Phân bổ (%)')).toHaveAttribute('max', '20');
  await expect(dialog.getByLabel('Vai trò trong dự án')).toHaveValue('Draft advisor');
  await expect(dialog.getByRole('button', { name: 'Lưu thay đổi' })).toBeEnabled();
});

test('small mobile login and failed form remain usable with keyboard and no horizontal overflow', async ({
  page,
}, info) => {
  await mockApi(page, { authenticated: false });
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('admin@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  await page.screenshot({ path: info.outputPath('login-small-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByLabel('Mật khẩu', { exact: true }).press('Enter');
  await expect(page.locator('.stat-card').first()).toBeVisible();
  const dialog = await skillDraft(page);
  await page.route('**/api/skills', (route) =>
    route.request().method() === 'POST'
      ? route.fulfill({ status: 503, body: 'Unavailable' })
      : route.fallback(),
  );
  await dialog.getByLabel('Nhóm kỹ năng').press('Enter');
  await expect(dialog.getByRole('alert')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(dialog.getByRole('button', { name: 'Hủy', exact: true })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: info.outputPath('failed-form-small-mobile.png'), fullPage: true });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Thêm kỹ năng', exact: true })).toBeFocused();
});
