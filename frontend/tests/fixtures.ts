import type { Page as BrowserPage } from '@playwright/test';
import type { Role, User } from '../src/auth';
import type { ActivityEvent } from '../src/types';

// Browser-only fixtures. The application itself always uses the real API.
export async function mockApi(
  page: BrowserPage,
  options: { role?: Role; authenticated?: boolean; mustChangePassword?: boolean } = {},
) {
  const csrf = 'browser-test-csrf-token';
  let authenticated = options.authenticated ?? true;
  let current: User = {
    user_id: 'USER001',
    email: 'admin@example.com',
    name: 'Admin SkillGraph',
    role: options.role || 'ADMIN',
    is_active: true,
    must_change_password: options.mustChangePassword ?? false,
    project_ids: options.role === 'MANAGER' ? ['PROJ001'] : [],
  };
  const users: User[] = [current];
  const passwords = new Map([[current.email, 'Test-only password 2026!']]);
  const employees = Array.from({ length: 12 }, (_, i) => ({
    employee_id: `EMP${String(i + 1).padStart(3, '0')}`,
    name: [
      'Nguyen Van Bac',
      'An Nguyen',
      'Minh Tran',
      'Lan Le',
      'Huy Pham',
      'Mai Vo',
      'Khoa Nguyen',
      'Thao Tran',
      'Linh Pham',
      'Bao Le',
      'Nam Tran',
      'Nhi Ho',
    ][i],
    email: `person${i}@example.com`,
    title: i === 3 ? 'DevOps Engineer' : 'Backend Developer',
    seniority: 'Middle',
    status: i % 2 ? 'ASSIGNED' : 'AVAILABLE',
    location: 'Ho Chi Minh City',
  }));
  const skills = [
    'Python',
    'FastAPI',
    'Java',
    'Spring Boot',
    'MySQL',
    'PostgreSQL',
    'Docker',
    'React',
    'TypeScript',
    'AWS',
    'Linux',
    'Redis',
  ].map((name, i) => ({
    skill_id: `SK${String(i + 1).padStart(3, '0')}`,
    name,
    category: i === 6 ? 'DevOps' : 'Backend',
  }));
  const projects = ['E-commerce Platform', 'Cloud Gaming Platform', 'Analytics Platform'].map(
    (name, i) => ({
      project_id: `PROJ00${i + 1}`,
      name,
      description: 'Kết nối năng lực đội ngũ để xây dựng sản phẩm tốt hơn.',
      status: i === 2 ? 'PLANNING' : 'ACTIVE',
    }),
  );
  const database: Record<string, any[]> = { employees, skills, projects };
  const activities: ActivityEvent[] = [];
  let activitySequence = 0;
  function track(
    kind: ActivityEvent['resource_type'],
    projectId: string,
    resourceId: string,
    before: any,
    after: any,
  ) {
    const allowed =
      kind === 'PROJECT'
        ? ['project_id', 'name', 'description', 'status']
        : kind === 'WORKS_ON'
          ? ['project_id', 'employee_id', 'role', 'allocation']
          : ['project_id', 'skill_id', 'min_level', 'priority'];
    const snapshot = (value: any) =>
      value == null
        ? null
        : Object.fromEntries(allowed.filter((key) => key in value).map((key) => [key, value[key]]));
    const previous = snapshot(before);
    const next = snapshot(after);
    if (JSON.stringify(previous) === JSON.stringify(next)) return;
    activities.unshift({
      event_id: `00000000-0000-0000-0000-${String(++activitySequence).padStart(12, '0')}`,
      occurred_at: new Date().toISOString(),
      actor_id: current.user_id,
      actor_name: current.name,
      project_id: projectId,
      resource_type: kind,
      resource_id: resourceId,
      action: previous === null ? 'CREATED' : next === null ? 'DELETED' : 'UPDATED',
      before: previous,
      after: next,
    });
  }
  const relations: Record<string, any[]> = {
    '/api/projects/PROJ001/assignments': [
      assignment('PROJ001', 'EMP002', 80),
      assignment('PROJ001', 'EMP003', 60),
    ],
    '/api/projects/PROJ002/assignments': [
      assignment('PROJ002', 'EMP001', 80),
      assignment('PROJ002', 'EMP002', 20),
    ],
    '/api/projects/PROJ003/assignments': [assignment('PROJ003', 'EMP004', 40)],
  };
  function assignment(projectId: string, employeeId: string, allocation: number) {
    return {
      project_id: projectId,
      project_name: projects.find((p) => p.project_id === projectId)?.name,
      employee_id: employeeId,
      employee_name: employees.find((e) => e.employee_id === employeeId)?.name,
      role: 'Backend Developer',
      allocation,
    };
  }
  function allocationItems(items: any[]) {
    return items.map((item) => {
      const total = Object.entries(relations)
        .filter(([key]) => key.endsWith('/assignments'))
        .flatMap(([, list]) => list)
        .filter((a) => a.employee_id === item.employee_id)
        .reduce((sum, a) => sum + a.allocation, 0);
      return {
        ...item,
        employee_total_allocation: total,
        employee_remaining_allocation: 100 - total,
      };
    });
  }
  function gap(projectId: string) {
    const isMain = projectId === 'PROJ001';
    const items = (
      isMain
        ? ['Docker', 'Java', 'MySQL', 'React', 'Spring Boot']
        : ['Python', 'FastAPI', 'PostgreSQL']
    ).map((name) => ({
      skill_id: skills.find((s) => s.name === name)!.skill_id,
      skill: name,
      required_level: name === 'React' ? 2 : 3,
      best_team_level: name === 'Docker' ? 2 : 4,
      employee_count: 2,
      priority: name === 'Docker' ? 'SHOULD' : 'MUST',
      status: name === 'Docker' ? 'GAP' : 'COVERED',
    }));
    return {
      project_id: projectId,
      summary: {
        total: items.length,
        covered: items.length - (isMain ? 1 : 0),
        gap: isMain ? 1 : 0,
        missing: 0,
        coverage_percent: isMain ? 80 : 100,
      },
      skills: items,
    };
  }
  await page.route('**/api/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const parts = url.pathname.split('/').filter(Boolean);
    const [, resource, id, relation, relatedId] = parts;
    const method = req.method();
    const body = method === 'GET' || method === 'DELETE' ? null : req.postDataJSON();
    const json = (value: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: 'application/json',
        body: status === 204 ? undefined : JSON.stringify(value),
      });
    if (resource === 'auth') {
      if (id === 'login') {
        const user = users.find((u) => u.email === body.email?.trim().toLowerCase());
        if (!user?.is_active || passwords.get(user.email) !== body.password)
          return json({ detail: 'Email hoặc mật khẩu không đúng.' }, 401);
        current = user;
        authenticated = true;
        return json({ user: current, csrf_token: csrf });
      }
      if (!authenticated) return json({ detail: 'Vui lòng đăng nhập.' }, 401);
      if (method !== 'GET' && req.headers()['x-csrf-token'] !== csrf)
        return json({ detail: 'Invalid CSRF token.' }, 403);
      if (id === 'me') return json({ user: current, csrf_token: csrf });
      if (id === 'logout') {
        authenticated = false;
        return json(null, 204);
      }
      if (id === 'password') {
        if (passwords.get(current.email) !== body.current_password)
          return json({ detail: 'Mật khẩu hiện tại không đúng.' }, 400);
        passwords.set(current.email, body.new_password);
        current.must_change_password = false;
        authenticated = false;
        return json(null, 204);
      }
      if (current.role !== 'ADMIN') return json({ detail: 'Admin only.' }, 403);
      if (id === 'users' && !relation && method === 'GET')
        return json({ items: users, total: users.length, limit: 20, offset: 0 });
      if (id === 'users' && !relation && method === 'POST') {
        const user: User = {
          ...body,
          user_id: `USER${users.length + 1}`,
          is_active: true,
          must_change_password: true,
        };
        passwords.set(user.email, body.password);
        delete (user as unknown as Record<string, unknown>).password;
        users.push(user);
        return json(user, 201);
      }
      const user = users.find((u) => u.user_id === relation);
      if (!user) return json({ detail: 'Not found' }, 404);
      if (relatedId === 'password') {
        passwords.set(user.email, body.password);
        user.must_change_password = true;
        return json(null, 204);
      }
      if (method === 'PATCH') {
        Object.assign(user, body);
        return json(user);
      }
      return json({ detail: 'Not found' }, 404);
    }
    if (!authenticated) return json({ detail: 'Phiên đăng nhập đã hết hạn.' }, 401);
    if (resource === 'activity') {
      if (current.role !== 'ADMIN') return json({ detail: 'Admin only.' }, 403);
      if (method !== 'GET') return json({ detail: 'Method not allowed' }, 405);
      let filtered = activities.filter((item) => {
        for (const key of ['project_id', 'action', 'resource_type'] as const)
          if (url.searchParams.get(key) && item[key] !== url.searchParams.get(key)) return false;
        const actor = url.searchParams.get('actor')?.toLowerCase();
        if (actor && !item.actor_name.toLowerCase().includes(actor) && item.actor_id !== actor)
          return false;
        const since = url.searchParams.get('since');
        const until = url.searchParams.get('until');
        return (
          (!since || new Date(item.occurred_at) >= new Date(since)) &&
          (!until || new Date(item.occurred_at) <= new Date(until))
        );
      });
      const cursor = url.searchParams.get('cursor');
      if (cursor)
        filtered = filtered.slice(filtered.findIndex((item) => item.event_id === cursor) + 1);
      const limit = Number(url.searchParams.get('limit') || 20);
      return json({
        items: filtered.slice(0, limit),
        next_cursor: filtered.length > limit ? filtered[limit - 1].event_id : null,
      });
    }
    if (method !== 'GET') {
      if (req.headers()['x-csrf-token'] !== csrf)
        return json({ detail: 'Invalid CSRF token.' }, 403);
      if (
        current.role !== 'ADMIN' &&
        !(
          current.role === 'MANAGER' &&
          resource === 'projects' &&
          current.project_ids.includes(id) &&
          (method === 'PATCH' || ['assignments', 'requirements'].includes(relation))
        )
      )
        return json({ detail: 'Không có quyền.' }, 403);
    }
    if (resource === 'dashboard' && method === 'GET') {
      const capacity = allocationItems(employees).map((employee) => ({
        employee_id: employee.employee_id,
        name: employee.name,
        title: employee.title,
        total_allocation: employee.employee_total_allocation,
        remaining_allocation: employee.employee_remaining_allocation,
      }));
      capacity.sort(
        (a, b) =>
          a.total_allocation - b.total_allocation ||
          a.name.localeCompare(b.name) ||
          a.employee_id.localeCompare(b.employee_id),
      );
      const defaults = [...projects].sort(
        (a, b) =>
          Number(b.status === 'ACTIVE') - Number(a.status === 'ACTIVE') ||
          a.project_id.localeCompare(b.project_id),
      );
      return json({
        generated_at: new Date().toISOString(),
        summary: {
          employee_count: employees.length,
          available_employee_count: employees.filter((e) => e.status === 'AVAILABLE').length,
          project_count: projects.length,
          active_project_count: projects.filter((p) => p.status === 'ACTIVE').length,
          skill_count: skills.length,
        },
        capacity: capacity.slice(0, 5),
        default_project: defaults[0] || null,
      });
    }
    if (relation === 'skill-gap') return json(gap(id));
    if (relation === 'recommendations')
      return json({
        project_id: id,
        summary: {
          uncovered_skill_count: id === 'PROJ001' ? 1 : 0,
          candidate_count: id === 'PROJ001' ? 2 : 0,
        },
        uncovered_skills: gap(id).skills.filter((s) => s.status !== 'COVERED'),
        candidates:
          id !== 'PROJ001'
            ? []
            : [employees[0], employees[3]].map((e, i) => ({
                ...e,
                status: 'AVAILABLE',
                rank: i + 1,
                matched_skill_count: 1,
                matched_skills: [
                  { skill_id: 'SK007', skill: 'Docker', level: i + 3, required_level: 3 },
                ],
                collaboration_count: i ? 0 : 1,
                collaborators: i ? [] : ['An Nguyen'],
                shared_projects: i ? [] : ['Cloud Gaming Platform'],
              })),
      });
    if (relation) {
      const key = `/api/${resource}/${id}/${relation}`;
      const items = (relations[key] ||= []);
      const relatedField = relation === 'assignments' ? 'employee_id' : 'skill_id';
      if (method === 'GET')
        return json({
          items: relation === 'assignments' ? allocationItems(items) : items,
          total: items.length,
        });
      const found = items.findIndex((item) => item[relatedField] === relatedId);
      if (method === 'DELETE') {
        if (found < 0) return json({ detail: 'Không tìm thấy liên kết.' }, 404);
        if (resource === 'projects')
          track(
            relation === 'assignments' ? 'WORKS_ON' : 'REQUIRES_SKILL',
            id,
            `${id}/${relatedId}`,
            items[found],
            null,
          );
        items.splice(found, 1);
        return json(null, 204);
      }
      if (method === 'PUT') {
        if (relation === 'assignments') {
          const other = Object.entries(relations)
            .filter(([k]) => k.endsWith('/assignments') && k !== key)
            .flatMap(([, v]) => v)
            .filter((a) => a.employee_id === relatedId)
            .reduce((sum, a) => sum + a.allocation, 0);
          if (other + body.allocation > 100)
            return json(
              { detail: `Employee would exceed 100% allocation (${other + body.allocation}%).` },
              409,
            );
        }
        const skill = skills.find((s) => s.skill_id === relatedId);
        const value =
          relation === 'assignments'
            ? { ...assignment(id, relatedId, body.allocation), ...body }
            : {
                [`${resource === 'employees' ? 'employee' : 'project'}_id`]: id,
                [`${resource === 'employees' ? 'employee' : 'project'}_name`]: database[
                  resource
                ].find(
                  (item) => item[resource === 'employees' ? 'employee_id' : 'project_id'] === id,
                )?.name,
                skill_id: relatedId,
                skill_name: skill?.name,
                category: skill?.category,
                ...body,
              };
        if (resource === 'projects')
          track(
            relation === 'assignments' ? 'WORKS_ON' : 'REQUIRES_SKILL',
            id,
            `${id}/${relatedId}`,
            found < 0 ? null : items[found],
            value,
          );
        if (found < 0) items.push(value);
        else items[found] = value;
        return json(
          relation === 'assignments' ? allocationItems([value])[0] : value,
          found < 0 ? 201 : 200,
        );
      }
    }
    const items = database[resource];
    if (!items) return json({ detail: 'Not found' }, 404);
    const idField =
      resource === 'employees'
        ? 'employee_id'
        : resource === 'projects'
          ? 'project_id'
          : 'skill_id';
    if (method === 'GET' && !id) {
      let filtered = [...items];
      for (const field of ['status', 'category'])
        if (url.searchParams.get(field))
          filtered = filtered.filter(
            (item) => item[field]?.toLowerCase() === url.searchParams.get(field)?.toLowerCase(),
          );
      const search = url.searchParams.get('q')?.toLowerCase();
      if (search)
        filtered = filtered.filter((item) =>
          Object.values(item).some((v) => String(v).toLowerCase().includes(search)),
        );
      const limit = Number(url.searchParams.get('limit') || 20);
      const offset = Number(url.searchParams.get('offset') || 0);
      return json({
        items: filtered.slice(offset, offset + limit),
        total: filtered.length,
        offset,
        limit,
      });
    }
    const found = items.findIndex((item) => item[idField] === id);
    if (method === 'POST') {
      if (items.some((item) => item[idField] === body[idField]))
        return json({ detail: 'Mã đã tồn tại.' }, 409);
      items.push(body);
      if (resource === 'projects') track('PROJECT', body.project_id, body.project_id, null, body);
      return json(body, 201);
    }
    if (found < 0) return json({ detail: 'Không tìm thấy bản ghi.' }, 404);
    if (method === 'GET') return json(items[found]);
    if (method === 'PATCH') {
      if (resource === 'projects')
        track('PROJECT', id, id, items[found], { ...items[found], ...body });
      items[found] = { ...items[found], ...body };
      return json(items[found]);
    }
    if (method === 'DELETE') {
      if (resource === 'projects') track('PROJECT', id, id, items[found], null);
      items.splice(found, 1);
      return json(null, 204);
    }
    return json({ detail: 'Unknown method' }, 405);
  });
  return {
    activities,
    expire: () => {
      authenticated = false;
    },
  };
}
