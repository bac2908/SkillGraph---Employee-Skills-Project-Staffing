import type { Page as BrowserPage } from '@playwright/test';

// Browser-only fixtures. The application itself always uses the real API.
export async function mockApi(page: BrowserPage) {
  const employees = Array.from({ length: 12 }, (_, i) => ({ employee_id: `EMP${String(i + 1).padStart(3, '0')}`, name: ['Nguyen Van Bac', 'An Nguyen', 'Minh Tran', 'Lan Le', 'Huy Pham', 'Mai Vo', 'Khoa Nguyen', 'Thao Tran', 'Linh Pham', 'Bao Le', 'Nam Tran', 'Nhi Ho'][i], email: `person${i}@example.com`, title: i === 3 ? 'DevOps Engineer' : 'Backend Developer', seniority: 'Middle', status: i % 2 ? 'ASSIGNED' : 'AVAILABLE', location: 'Ho Chi Minh City' }));
  const skills = ['Python', 'FastAPI', 'Java', 'Spring Boot', 'MySQL', 'PostgreSQL', 'Docker', 'React', 'TypeScript', 'AWS', 'Linux', 'Redis'].map((name, i) => ({ skill_id: `SK${String(i + 1).padStart(3, '0')}`, name, category: i === 6 ? 'DevOps' : 'Backend' }));
  const projects = ['E-commerce Platform', 'Cloud Gaming Platform', 'Analytics Platform'].map((name, i) => ({ project_id: `PROJ00${i + 1}`, name, description: 'Kết nối năng lực đội ngũ để xây dựng sản phẩm tốt hơn.', status: i === 2 ? 'PLANNING' : 'ACTIVE' }));
  const database: Record<string, any[]> = { employees, skills, projects };
  const relations: Record<string, any[]> = {
    '/api/projects/PROJ001/assignments': [assignment('PROJ001', 'EMP002', 80), assignment('PROJ001', 'EMP003', 60)],
    '/api/projects/PROJ002/assignments': [assignment('PROJ002', 'EMP001', 80), assignment('PROJ002', 'EMP002', 20)],
    '/api/projects/PROJ003/assignments': [assignment('PROJ003', 'EMP004', 40)],
  };
  function assignment(projectId: string, employeeId: string, allocation: number) { return { project_id: projectId, project_name: projects.find(p => p.project_id === projectId)?.name, employee_id: employeeId, employee_name: employees.find(e => e.employee_id === employeeId)?.name, role: 'Backend Developer', allocation }; }
  function allocationItems(items: any[]) { return items.map(item => {
    const total = Object.entries(relations).filter(([key]) => key.endsWith('/assignments')).flatMap(([, list]) => list).filter(a => a.employee_id === item.employee_id).reduce((sum, a) => sum + a.allocation, 0);
    return { ...item, employee_total_allocation: total, employee_remaining_allocation: 100 - total };
  }); }
  function gap(projectId: string) {
    const isMain = projectId === 'PROJ001';
    const items = (isMain ? ['Docker', 'Java', 'MySQL', 'React', 'Spring Boot'] : ['Python', 'FastAPI', 'PostgreSQL']).map(name => ({ skill_id: skills.find(s => s.name === name)!.skill_id, skill: name, required_level: name === 'React' ? 2 : 3, best_team_level: name === 'Docker' ? 2 : 4, employee_count: 2, priority: name === 'Docker' ? 'SHOULD' : 'MUST', status: name === 'Docker' ? 'GAP' : 'COVERED' }));
    return { project_id: projectId, summary: { total: items.length, covered: items.length - (isMain ? 1 : 0), gap: isMain ? 1 : 0, missing: 0, coverage_percent: isMain ? 80 : 100 }, skills: items };
  }
  await page.route('**/api/**', async route => {
    const req = route.request(); const url = new URL(req.url()); const parts = url.pathname.split('/').filter(Boolean); const [, resource, id, relation, relatedId] = parts;
    const method = req.method(); const body = method === 'GET' || method === 'DELETE' ? null : req.postDataJSON();
    const json = (value: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: status === 204 ? undefined : JSON.stringify(value) });
    if (relation === 'skill-gap') return json(gap(id));
    if (relation === 'recommendations') return json({ project_id: id, summary: { uncovered_skill_count: id === 'PROJ001' ? 1 : 0, candidate_count: id === 'PROJ001' ? 2 : 0 }, uncovered_skills: gap(id).skills.filter(s => s.status !== 'COVERED'), candidates: id !== 'PROJ001' ? [] : [employees[0], employees[3]].map((e, i) => ({ ...e, status: 'AVAILABLE', rank: i + 1, matched_skill_count: 1, matched_skills: [{ skill_id: 'SK007', skill: 'Docker', level: i + 3, required_level: 3 }], collaboration_count: i ? 0 : 1, collaborators: i ? [] : ['An Nguyen'], shared_projects: i ? [] : ['Cloud Gaming Platform'] })) });
    if (relation) {
      const key = `/api/${resource}/${id}/${relation}`; const items = relations[key] ||= [];
      const relatedField = relation === 'assignments' ? 'employee_id' : 'skill_id';
      if (method === 'GET') return json({ items: relation === 'assignments' ? allocationItems(items) : items, total: items.length });
      const found = items.findIndex(item => item[relatedField] === relatedId);
      if (method === 'DELETE') { if (found < 0) return json({ detail: 'Không tìm thấy liên kết.' }, 404); items.splice(found, 1); return json(null, 204); }
      if (method === 'PUT') {
        if (relation === 'assignments') {
          const other = Object.entries(relations).filter(([k]) => k.endsWith('/assignments') && k !== key).flatMap(([, v]) => v).filter(a => a.employee_id === relatedId).reduce((sum, a) => sum + a.allocation, 0);
          if (other + body.allocation > 100) return json({ detail: `Employee would exceed 100% allocation (${other + body.allocation}%).` }, 409);
        }
        const skill = skills.find(s => s.skill_id === relatedId);
        const value = relation === 'assignments' ? { ...assignment(id, relatedId, body.allocation), ...body } : { [`${resource === 'employees' ? 'employee' : 'project'}_id`]: id, [`${resource === 'employees' ? 'employee' : 'project'}_name`]: database[resource].find(item => item[resource === 'employees' ? 'employee_id' : 'project_id'] === id)?.name, skill_id: relatedId, skill_name: skill?.name, category: skill?.category, ...body };
        if (found < 0) items.push(value); else items[found] = value;
        return json(relation === 'assignments' ? allocationItems([value])[0] : value, found < 0 ? 201 : 200);
      }
    }
    const items = database[resource]; if (!items) return json({ detail: 'Not found' }, 404);
    const idField = resource === 'employees' ? 'employee_id' : resource === 'projects' ? 'project_id' : 'skill_id';
    if (method === 'GET' && !id) { let filtered = [...items]; for (const field of ['status', 'category']) if (url.searchParams.get(field)) filtered = filtered.filter(item => item[field]?.toLowerCase() === url.searchParams.get(field)?.toLowerCase());
      const search = url.searchParams.get('q')?.toLowerCase(); if (search) filtered = filtered.filter(item => Object.values(item).some(v => String(v).toLowerCase().includes(search)));
      const limit = Number(url.searchParams.get('limit') || 20); const offset = Number(url.searchParams.get('offset') || 0);
      return json({ items: filtered.slice(offset, offset + limit), total: filtered.length, offset, limit }); }
    const found = items.findIndex(item => item[idField] === id);
    if (method === 'POST') { if (items.some(item => item[idField] === body[idField])) return json({ detail: 'Mã đã tồn tại.' }, 409); items.push(body); return json(body, 201); }
    if (found < 0) return json({ detail: 'Không tìm thấy bản ghi.' }, 404);
    if (method === 'GET') return json(items[found]);
    if (method === 'PATCH') { items[found] = { ...items[found], ...body }; return json(items[found]); }
    if (method === 'DELETE') { items.splice(found, 1); return json(null, 204); }
    return json({ detail: 'Unknown method' }, 405);
  });
}
