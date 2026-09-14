import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

// No HTTP interception, service stubs, auth overrides or direct graph seeding.
const origin = 'http://127.0.0.1:5175';
const run = process.env.SKILLGRAPH_E2E_RUN!;
const secret = process.env.SKILLGRAPH_E2E_PASSWORD!;
const name = (label: string) => `E2E ${run} ${label}`;
const id = (prefix: string, index: number) => `${prefix}${run}${String(index).padStart(2, '0')}`;
const emp = (index: number) => id('EMP', index);
const skill = (index: number) => id('SK', index);
const project = (index: number) => id('PROJ', index);
const employees = ['Member', 'Both', 'Collaborator', 'Higher', 'Tie', 'Unavailable', 'Low', 'Race'];
const skills = ['Covered', 'Gap', 'Missing'];
const projects = ['Main', 'Shared', 'Race A', 'Race B'];

async function read(api: APIRequestContext, path: string) {
  const response = await api.get(path);
  expect(response.status(), `GET ${path}`).toBe(200);
  return response.json();
}

async function write(api: APIRequestContext, method: string, path: string, data?: unknown) {
  const me = await read(api, '/api/auth/me');
  return api.fetch(path, {
    method,
    headers: { Origin: origin, 'X-CSRF-Token': me.csrf_token },
    ...(data === undefined ? {} : { data }),
  });
}

async function submit(
  page: Page,
  method: string,
  path: string,
  status = 201,
  button = 'Lưu thay đổi',
) {
  const response = page.waitForResponse(
    (r) => new URL(r.url()).pathname === path && r.request().method() === method,
  );
  await page.getByRole('dialog').getByRole('button', { name: button, exact: true }).click();
  expect((await response).status(), `${method} ${path}`).toBe(status);
  if (status < 400) await expect(page.getByRole('dialog')).not.toBeVisible();
}

async function login(page: Page, email: string, password: string) {
  await page.goto('/projects');
  await expect(page.getByRole('heading', { name: 'Đăng nhập không gian của bạn' })).toBeVisible();
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.locator('.sidebar')).toBeVisible();
}

async function employeeSkill(
  page: Page,
  employee: number,
  capability: number,
  level: number,
  years = 2.5,
) {
  await page.goto(`/employees/${emp(employee)}`);
  await page.getByRole('button', { name: 'Gán kỹ năng', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Kỹ năng', { exact: true }).selectOption(skill(capability));
  await dialog.getByLabel('Mức thành thạo (1–5)').fill(String(level));
  await dialog.getByLabel('Số năm kinh nghiệm').fill(String(years));
  await submit(page, 'PUT', `/api/employees/${emp(employee)}/skills/${skill(capability)}`);
  const row = page.getByRole('row').filter({ hasText: name(skills[capability - 1]) });
  await expect(row.getByLabel(`Cấp ${level}/5`)).toBeVisible();
  await expect(row).toContainText(`${years} năm`);
  const stored = await read(page.request, `/api/employees/${emp(employee)}/skills`);
  expect(
    stored.items.find((item: { skill_id: string }) => item.skill_id === skill(capability)),
  ).toMatchObject({ level, years_experience: years });
}

async function assign(
  page: Page,
  target: number,
  employee: number,
  allocation: number,
  edit = false,
) {
  await page.goto(`/projects/${project(target)}?tab=assignments`);
  await page
    .getByRole('button', {
      name: edit ? `Sửa phân công ${name(employees[employee - 1])}` : 'Phân công',
      exact: true,
    })
    .click();
  const dialog = page.getByRole('dialog');
  if (!edit) await dialog.getByLabel('Nhân viên').selectOption(emp(employee));
  await dialog.getByLabel('Vai trò trong dự án').fill('E2E Engineer');
  await dialog.getByLabel('Phân bổ (%)').fill(String(allocation));
  await submit(
    page,
    'PUT',
    `/api/projects/${project(target)}/assignments/${emp(employee)}`,
    edit ? 200 : 201,
  );
  await expect(page.getByRole('row').filter({ hasText: emp(employee) })).toContainText(
    `${allocation}%`,
  );
}

async function events(api: APIRequestContext, target = 1) {
  const result = await read(api, `/api/activity?project_id=${project(target)}&limit=100`);
  expect(result.next_cursor).toBeNull();
  return result.items as {
    event_id: string;
    actor_id: string;
    actor_name: string;
    resource_id: string;
    resource_type: string;
    action: string;
    before: { allocation?: number } | null;
    after: { allocation?: number } | null;
  }[];
}

test('real FE → FastAPI → graph: business lifecycle, RBAC, audit and allocation races', async ({
  page,
  browser,
}) => {
  const pageErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await login(page, 'e2e-admin@example.com', secret);
  const admin = (await read(page.request, '/api/auth/me')).user;

  await test.step('01 Create all skills and employees through FE; read committed API values', async () => {
    for (const [index, label] of skills.entries()) {
      await page.goto('/skills');
      await page.getByRole('button', { name: 'Thêm kỹ năng', exact: true }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByLabel('Mã kỹ năng').fill(skill(index + 1));
      await dialog.getByLabel('Tên kỹ năng').fill(name(label));
      await dialog.getByLabel('Nhóm kỹ năng').fill('E2E');
      await submit(page, 'POST', '/api/skills');
      expect((await read(page.request, `/api/skills/${skill(index + 1)}`)).name).toBe(name(label));
    }
    for (const [index, label] of employees.entries()) {
      await page.goto('/employees');
      await page.getByRole('button', { name: 'Thêm nhân viên', exact: true }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByLabel('Mã nhân viên').fill(emp(index + 1));
      await dialog.getByLabel('Họ và tên').fill(name(label));
      await dialog
        .getByLabel('Email', { exact: true })
        .fill(`${emp(index + 1).toLowerCase()}@example.com`);
      await dialog.getByLabel('Chức danh').fill('E2E Engineer');
      await dialog.getByLabel('Địa điểm').fill('Test only');
      await dialog
        .getByLabel('Trạng thái', { exact: true })
        .selectOption(label === 'Unavailable' ? 'UNAVAILABLE' : 'AVAILABLE');
      await submit(page, 'POST', '/api/employees');
      expect((await read(page.request, `/api/employees/${emp(index + 1)}`)).name).toBe(name(label));
    }
  });

  await test.step('02 Assign real HAS_SKILL levels and fractional experience through FE', async () => {
    for (const [employee, capability, level] of [
      [1, 1, 4],
      [1, 2, 2],
      [2, 2, 4],
      [2, 3, 3],
      [3, 2, 3],
      [4, 2, 5],
      [5, 2, 5],
      [6, 2, 5],
      [6, 3, 5],
      [7, 2, 2],
      [7, 3, 1],
    ])
      await employeeSkill(page, employee, capability, level);
  });

  await test.step('03 Create projects and real REQUIRES_SKILL through FE', async () => {
    for (const [index, label] of projects.entries()) {
      await page.goto('/projects');
      await page.getByRole('button', { name: 'Thêm dự án', exact: true }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByLabel('Mã dự án').fill(project(index + 1));
      await dialog.getByLabel('Tên dự án').fill(name(label));
      await dialog.getByLabel('Mô tả').fill('Disposable E2E dataset; no production data.');
      await submit(page, 'POST', '/api/projects');
    }
    for (let capability = 1; capability <= 3; capability++) {
      await page.goto(`/projects/${project(1)}?tab=requirements`);
      await page.getByRole('button', { name: 'Thêm yêu cầu', exact: true }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByLabel('Kỹ năng', { exact: true }).selectOption(skill(capability));
      await dialog.getByLabel('Mức yêu cầu (1–5)').fill('3');
      await dialog
        .getByLabel('Độ ưu tiên')
        .selectOption(['MUST', 'SHOULD', 'NICE'][capability - 1]);
      await submit(page, 'PUT', `/api/projects/${project(1)}/requirements/${skill(capability)}`);
    }
    const requirements = await read(page.request, `/api/projects/${project(1)}/requirements`);
    expect(requirements.total).toBe(3);
    for (let i = 0; i < 3; i++)
      expect(
        requirements.items.find((r: { skill_id: string }) => r.skill_id === skill(i + 1)),
      ).toMatchObject({ min_level: 3, priority: ['MUST', 'SHOULD', 'NICE'][i] });
  });

  await test.step('04 Staff initial team and shared-project collaboration through FE', async () => {
    await assign(page, 1, 1, 40);
    await assign(page, 2, 1, 10);
    await assign(page, 2, 2, 100); // AVAILABLE + fully allocated is still recommended by current rules.
    await assign(page, 2, 3, 5);
  });

  await test.step('05 Check COVERED/GAP/MISSING and exact 33.33% against stored data and UI', async () => {
    const gap = await read(page.request, `/api/projects/${project(1)}/skill-gap`);
    expect(gap.summary).toEqual({
      total: 3,
      covered: 1,
      gap: 1,
      missing: 1,
      coverage_percent: 33.33,
    });
    for (const [index, status, level, count] of [
      [1, 'COVERED', 4, 1],
      [2, 'GAP', 2, 1],
      [3, 'MISSING', 0, 0],
    ] as const)
      expect(
        gap.skills.find((s: { skill_id: string }) => s.skill_id === skill(index)),
      ).toMatchObject({ status, best_team_level: level, employee_count: count, required_level: 3 });
    await page.goto(`/projects/${project(1)}`);
    await expect(page.locator('.coverage-number')).toHaveText('33.33%');
    for (const [label, status] of [
      ['Covered', 'Đáp ứng'],
      ['Gap', 'Cần nâng cấp'],
      ['Missing', 'Chưa có'],
    ])
      await expect(page.locator('.skill-bar-row').filter({ hasText: name(label) })).toContainText(
        status,
      );
  });

  await test.step('06 Candidate ranking: matches, collaboration, level, ID; exclusions and full capacity', async () => {
    const recommendations = await read(page.request, `/api/projects/${project(1)}/recommendations`);
    expect(recommendations.summary).toEqual({ uncovered_skill_count: 2, candidate_count: 4 });
    expect(recommendations.candidates.map((c: { employee_id: string }) => c.employee_id)).toEqual([
      emp(2),
      emp(3),
      emp(4),
      emp(5),
    ]);
    expect(recommendations.candidates.map((c: { rank: number }) => c.rank)).toEqual([1, 2, 3, 4]);
    expect(recommendations.candidates[0]).toMatchObject({
      matched_skill_count: 2,
      collaboration_count: 1,
      collaborators: [name('Member')],
      shared_projects: [name('Shared')],
    });
    expect(recommendations.candidates[1]).toMatchObject({
      matched_skill_count: 1,
      collaboration_count: 1,
    });
    expect(recommendations.candidates[2]).toMatchObject({
      matched_skill_count: 1,
      collaboration_count: 0,
    });
    await expect(page.locator('.candidate-card h3')).toHaveText(
      ['Both', 'Collaborator', 'Higher', 'Tie'].map(name),
    );
  });

  const managerContext = await browser.newContext({ baseURL: origin });
  const viewerContext = await browser.newContext({ baseURL: origin });
  try {
    let managerId = '';
    await test.step('07 Real Manager/Viewer sessions: granted update and denied direct writes', async () => {
      for (const [role, context] of [
        ['MANAGER', managerContext],
        ['VIEWER', viewerContext],
      ] as const) {
        const email = `e2e-${role.toLowerCase()}@example.com`;
        const created = await write(page.request, 'POST', '/api/auth/users', {
          name: name(role),
          email,
          password: secret,
          role,
          project_ids: role === 'MANAGER' ? [project(1), project(3), project(4)] : [],
        });
        expect(created.status()).toBe(201);
        if (role === 'MANAGER') managerId = (await created.json()).user_id;
        expect(
          (
            await context.request.post('/api/auth/login', {
              headers: { Origin: origin },
              data: { email, password: secret },
            })
          ).status(),
        ).toBe(200);
        expect(
          (
            await write(context.request, 'POST', '/api/auth/password', {
              current_password: secret,
              new_password: `${secret}-${role}`,
            })
          ).status(),
        ).toBe(204);
        const rolePage = await context.newPage();
        await login(rolePage, email, `${secret}-${role}`);
        await expect(rolePage.getByRole('button', { name: 'Thêm dự án', exact: true })).toHaveCount(
          0,
        );
        if (role === 'MANAGER') {
          await rolePage.getByRole('button', { name: `Sửa ${name('Main')}`, exact: true }).click();
          await rolePage
            .getByRole('dialog')
            .getByLabel('Mô tả')
            .fill('Updated by scoped E2E Manager');
          await submit(rolePage, 'PATCH', `/api/projects/${project(1)}`, 200);
        }
        const before = await read(context.request, `/api/projects/${project(2)}`);
        expect(
          (
            await write(context.request, 'PATCH', `/api/projects/${project(2)}`, {
              description: 'Forbidden',
            })
          ).status(),
        ).toBe(403);
        expect(await read(context.request, `/api/projects/${project(2)}`)).toEqual(before);
        expect((await context.request.get('/api/activity')).status()).toBe(403);
        expect((await context.request.get('/api/auth/users')).status()).toBe(403);
        await rolePage.close();
      }
      expect(
        (await write(viewerContext.request, 'DELETE', `/api/employees/${emp(1)}`)).status(),
      ).toBe(403);
      const audit = await events(page.request);
      expect(
        audit
          .filter((e) => e.resource_type === 'PROJECT' && e.action === 'UPDATED')
          .map((e) => e.actor_id),
      ).toEqual([managerId]);
    });

    await test.step('08 A stale FE allocation form receives a real 409 and retains input', async () => {
      await page.goto(`/projects/${project(1)}?tab=assignments`);
      await page
        .getByRole('button', { name: `Sửa phân công ${name('Member')}`, exact: true })
        .click();
      const dialog = page.getByRole('dialog');
      await dialog.getByLabel('Phân bổ (%)').fill('80'); // FE saw 10 elsewhere: 90 total.
      expect(
        (
          await write(page.request, 'PUT', `/api/projects/${project(2)}/assignments/${emp(1)}`, {
            role: 'E2E Engineer',
            allocation: 30,
          })
        ).status(),
      ).toBe(200);
      const before = await events(page.request);
      await submit(page, 'PUT', `/api/projects/${project(1)}/assignments/${emp(1)}`, 409);
      await expect(dialog.getByRole('alert')).toContainText('100%');
      await expect(dialog.getByLabel('Phân bổ (%)')).toHaveValue('80');
      expect(await events(page.request)).toEqual(before); // Rejected write must not invent an audit event.
      expect(
        (await read(page.request, `/api/projects/${project(1)}/assignments`)).items[0].allocation,
      ).toBe(40);
      await page.keyboard.press('Escape');
    });

    await test.step('09 Exactly 100 succeeds; 101 is rejected without state/audit changes', async () => {
      await assign(page, 1, 1, 70, true);
      await expect(page.getByRole('row').filter({ hasText: emp(1) })).toContainText(
        '100% · còn 0%',
      );
      const before = await events(page.request, 3);
      const denied = await write(
        page.request,
        'PUT',
        `/api/projects/${project(3)}/assignments/${emp(1)}`,
        { role: 'E2E Engineer', allocation: 1 },
      );
      expect(denied.status()).toBe(409);
      expect((await denied.json()).detail).toContain('101%');
      expect((await read(page.request, `/api/projects/${project(3)}/assignments`)).items).toEqual(
        [],
      );
      expect(await events(page.request, 3)).toEqual(before);
    });

    await test.step('10 Concurrent independent HTTP assignments: only one 60% write wins, three rounds', async () => {
      for (let round = 0; round < 3; round++) {
        const before = [...(await events(page.request, 3)), ...(await events(page.request, 4))];
        const responses = await Promise.all([
          write(page.request, 'PUT', `/api/projects/${project(3)}/assignments/${emp(8)}`, {
            role: 'E2E race Admin',
            allocation: 60,
          }),
          write(
            managerContext.request,
            'PUT',
            `/api/projects/${project(4)}/assignments/${emp(8)}`,
            { role: 'E2E race Manager', allocation: 60 },
          ),
        ]);
        expect(responses.map((r) => r.status()).sort()).toEqual([201, 409]);
        const a = await read(page.request, `/api/projects/${project(3)}/assignments`);
        const b = await read(page.request, `/api/projects/${project(4)}/assignments`);
        expect(a.items.length + b.items.length).toBe(1);
        expect([...a.items, ...b.items][0]).toMatchObject({
          allocation: 60,
          employee_total_allocation: 60,
          employee_remaining_allocation: 40,
        });
        const winner = a.items.length ? 3 : 4;
        const after = [...(await events(page.request, 3)), ...(await events(page.request, 4))];
        const added = after.filter((e) => !before.some((old) => old.event_id === e.event_id));
        expect(added).toHaveLength(1);
        expect(added[0]).toMatchObject({
          actor_id: winner === 3 ? admin.user_id : managerId,
          action: 'CREATED',
          before: null,
          after: { allocation: 60 },
        });
        expect(
          (
            await write(
              page.request,
              'DELETE',
              `/api/projects/${project(winner)}/assignments/${emp(8)}`,
            )
          ).status(),
        ).toBe(204);
      }
    });

    await test.step('11 Update/remove staffing: coverage 100 then 33.33, recommendations refresh', async () => {
      await assign(page, 2, 2, 80, true);
      await assign(page, 1, 2, 20); // Candidate now reaches exactly 100 total.
      await page.getByRole('tab', { name: 'Phân tích & gợi ý', exact: true }).click();
      await expect(page.locator('.coverage-number')).toHaveText('100%');
      await expect(page.getByRole('heading', { name: 'Đội ngũ đã đáp ứng kỹ năng' })).toBeVisible();
      expect((await read(page.request, `/api/projects/${project(1)}/skill-gap`)).summary).toEqual({
        total: 3,
        covered: 3,
        gap: 0,
        missing: 0,
        coverage_percent: 100,
      });
      await page.getByRole('tab', { name: 'Đội ngũ', exact: true }).click();
      await page.getByRole('button', { name: `Gỡ phân công ${name('Both')}`, exact: true }).click();
      await submit(
        page,
        'DELETE',
        `/api/projects/${project(1)}/assignments/${emp(2)}`,
        204,
        'Gỡ phân công',
      );
      await expect(page.getByRole('row').filter({ hasText: emp(2) })).toHaveCount(0);
      await page.getByRole('tab', { name: 'Phân tích & gợi ý', exact: true }).click();
      await expect(page.locator('.coverage-number')).toHaveText('33.33%');
      await expect(page.locator('.candidate-card').first()).toContainText(name('Both'));
    });

    await test.step('12 Audit before/after and actor are persisted and visible', async () => {
      const audit = await events(page.request);
      const update = audit.find(
        (e) => e.resource_id === `${project(1)}/${emp(1)}` && e.action === 'UPDATED',
      );
      expect(update).toMatchObject({
        actor_id: admin.user_id,
        actor_name: name('Admin'),
        before: { allocation: 40 },
        after: { allocation: 70 },
      });
      expect(
        audit.find((e) => e.resource_id === `${project(1)}/${emp(2)}` && e.action === 'DELETED'),
      ).toMatchObject({ actor_id: admin.user_id, before: { allocation: 20 }, after: null });
      expect(new Set(audit.map((e) => e.event_id)).size).toBe(audit.length);
      await page.getByRole('tab', { name: 'Hoạt động', exact: true }).click();
      const item = page
        .locator('.activity-item')
        .filter({ hasText: `${project(1)}/${emp(1)}` })
        .filter({ hasText: 'Đã cập nhật' });
      await expect(item).toHaveCount(1);
      await expect(item).toContainText(name('Admin'));
      await item.getByText('Xem thay đổi', { exact: true }).click();
      await expect(
        item.getByRole('row').filter({ hasText: 'Phân bổ (%)' }).getByRole('cell'),
      ).toHaveText(['40', '70']);
    });

    await test.step('13 Deleting linked Employee/Skill/Project is refused by real backend and shown in FE', async () => {
      for (const [route, key, label] of [
        ['employees', emp(1), 'Member'],
        ['skills', skill(1), 'Covered'],
        ['projects', project(1), 'Main'],
      ]) {
        const before = await read(page.request, `/api/${route}/${key}`);
        await page.goto(`/${route}`);
        await page.getByRole('button', { name: `Xóa ${name(label)}`, exact: true }).click();
        await submit(page, 'DELETE', `/api/${route}/${key}`, 409, 'Xác nhận xóa');
        await expect(page.getByRole('dialog').getByRole('alert')).toContainText(
          'gỡ liên kết trước khi xóa',
        );
        expect(await read(page.request, `/api/${route}/${key}`)).toEqual(before);
        await page.keyboard.press('Escape');
      }
    });
    expect(pageErrors).toEqual([]);
  } finally {
    await managerContext.close();
    await viewerContext.close();
    // Retain graph fixtures and run auth DB, even on failure, for explicit reviewed cleanup.
    await write(page.request, 'POST', '/api/auth/logout');
  }
});
