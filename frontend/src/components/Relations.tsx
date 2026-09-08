import { useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import { request, save, useAll, useResource } from '../api';
import type { Assignment, Employee, EmployeeSkill, Items, Requirement, Skill } from '../types';
import { useCapacity } from '../hooks';
import {
  AddButton,
  Avatar,
  Badge,
  Empty,
  ErrorNotice,
  FormDialog,
  Loading,
  Meter,
  SectionHeading,
  useWrite,
  type Field,
} from './ui';
import { options } from '../config';
import { useAuth } from '../auth';

export function AssignmentDialog({
  projectId,
  employeeId,
  existing,
  onClose,
}: {
  projectId: string;
  employeeId?: string;
  existing?: Assignment;
  onClose: () => void;
}) {
  const employees = useAll<Employee>('employees');
  const capacity = useCapacity();
  const write = useWrite();
  const assignments = useResource<Items<Assignment>>(`/api/projects/${projectId}/assignments`);
  const selectedId = existing?.employee_id || employeeId;
  const currentAssignment =
    existing || assignments.data?.items.find((a) => a.employee_id === selectedId);
  const total = selectedId ? capacity.totals.get(selectedId) || 0 : null;
  const remaining =
    total === null ? null : Math.max(0, 100 - total + (currentAssignment?.allocation || 0));
  const error = employees.error || capacity.error || assignments.error;
  // Keep form mounted only after capacity and selector data are available.
  if (employees.isPending || capacity.isPending || assignments.isPending || error)
    return (
      <FormDialog
        title="Phân công nhân viên"
        onClose={onClose}
        submitDisabled
        onSubmit={async () => {}}
      >
        {error ? (
          <ErrorNotice
            error={error}
            retry={() => {
              void employees.refetch();
              void assignments.refetch();
              capacity.retry();
            }}
          />
        ) : (
          <Loading />
        )}
      </FormDialog>
    );
  const fields: Field[] = [
    {
      name: 'employee_id',
      label: 'Nhân viên',
      type: 'select',
      disabled: !!selectedId,
      options: (employees.data || [])
        .filter(
          (e) =>
            e.employee_id === selectedId ||
            !assignments.data?.items.some((a) => a.employee_id === e.employee_id),
        )
        .map((e) => ({
          value: e.employee_id,
          label: `${e.name} · còn ${Math.max(0, 100 - (capacity.totals.get(e.employee_id) || 0) + (currentAssignment?.employee_id === e.employee_id ? currentAssignment.allocation : 0))}%`,
        })),
    },
    { name: 'role', label: 'Vai trò trong dự án', maxLength: 100 },
    {
      name: 'allocation',
      label: 'Phân bổ (%)',
      type: 'number',
      min: 1,
      max: remaining ?? 100,
      step: 1,
      hint: 'Tổng phân bổ trên tất cả dự án không vượt quá 100%.',
    },
  ];
  return (
    <FormDialog
      title={currentAssignment ? 'Điều chỉnh phân công' : 'Phân công nhân viên'}
      fields={fields}
      submitDisabled={remaining === 0}
      initial={{
        employee_id: selectedId || '',
        role:
          currentAssignment?.role ||
          employees.data?.find((e) => e.employee_id === selectedId)?.title ||
          '',
        allocation:
          currentAssignment?.allocation ||
          (remaining && remaining > 0 ? Math.min(20, remaining) : ''),
      }}
      onClose={onClose}
      onSubmit={async (values) => {
        const targetId = selectedId || String(values.employee_id);
        const proposed =
          (capacity.totals.get(targetId) || 0) -
          (currentAssignment?.allocation || 0) +
          Number(values.allocation);
        if (proposed > 100)
          throw new Error(
            `Nhân viên sẽ được phân bổ ${proposed}%. Hãy chọn tỷ lệ thấp hơn hoặc điều chỉnh dự án khác.`,
          );
        await write(
          () =>
            save(`/api/projects/${projectId}/assignments/${targetId}`, 'PUT', {
              role: values.role,
              allocation: values.allocation,
            }),
          'Đã cập nhật phân công.',
        );
      }}
    >
      {remaining !== null && (
        <div className="capacity-note">
          <strong>{remaining}%</strong>
          <span>Dung lượng có thể phân bổ cho dự án này</span>
        </div>
      )}
    </FormDialog>
  );
}

export function Assignments({ projectId }: { projectId: string }) {
  const { canManageProject } = useAuth();
  const canEdit = canManageProject(projectId);
  const path = `/api/projects/${projectId}/assignments`;
  const query = useResource<Items<Assignment>>(path);
  const write = useWrite();
  const [edit, setEdit] = useState<Assignment | 'new' | null>(null);
  const [remove, setRemove] = useState<Assignment | null>(null);
  return (
    <section className="panel">
      <SectionHeading
        title="Đội ngũ dự án"
        detail="Điều phối vai trò và dung lượng làm việc của từng thành viên."
        action={canEdit && <AddButton onClick={() => setEdit('new')}>Phân công</AddButton>}
      />
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorNotice error={query.error} retry={() => void query.refetch()} />
      ) : !query.data.items.length ? (
        <Empty
          title="Đội ngũ đang chờ thành viên đầu tiên"
          detail="Phân công nhân viên để bắt đầu xây dựng năng lực dự án."
        />
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Thành viên</th>
                <th>Vai trò</th>
                <th>Dự án này</th>
                <th>Tổng phân bổ</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((a, index) => (
                <tr key={a.employee_id}>
                  <td>
                    <div className="identity">
                      <Avatar name={a.employee_name} index={index} />
                      <div>
                        <strong>{a.employee_name}</strong>
                        <small>{a.employee_id}</small>
                      </div>
                    </div>
                  </td>
                  <td>{a.role}</td>
                  <td>
                    <strong>{a.allocation}%</strong>
                  </td>
                  <td>
                    <div className="allocation-cell">
                      <span>
                        {a.employee_total_allocation}% · còn {a.employee_remaining_allocation}%
                      </span>
                      <Meter value={a.employee_total_allocation} />
                    </div>
                  </td>
                  <td>
                    {canEdit ? (
                      <div className="row-actions">
                        <button
                          className="icon-button"
                          aria-label={`Sửa phân công ${a.employee_name}`}
                          onClick={() => setEdit(a)}
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="icon-button delete-button"
                          aria-label={`Gỡ phân công ${a.employee_name}`}
                          onClick={() => setRemove(a)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    ) : (
                      <small>Chỉ xem</small>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {edit && (
        <AssignmentDialog
          projectId={projectId}
          existing={edit === 'new' ? undefined : edit}
          onClose={() => setEdit(null)}
        />
      )}
      {remove && (
        <FormDialog
          title={`Gỡ phân công ${remove.employee_name}?`}
          description="Nhân viên sẽ được gỡ khỏi dự án này. Kết quả Skill Gap sẽ được tính lại."
          submitLabel="Gỡ phân công"
          danger
          onClose={() => setRemove(null)}
          onSubmit={() =>
            write(
              () => request(`${path}/${remove.employee_id}`, { method: 'DELETE' }),
              'Đã gỡ phân công.',
            )
          }
        />
      )}
    </section>
  );
}

export function SkillRelations({
  ownerId,
  kind,
}: {
  ownerId: string;
  kind: 'employee' | 'project';
}) {
  const isEmployee = kind === 'employee';
  const { isAdmin, canManageProject } = useAuth();
  const canEdit = isEmployee ? isAdmin : canManageProject(ownerId);
  const path = isEmployee
    ? `/api/employees/${ownerId}/skills`
    : `/api/projects/${ownerId}/requirements`;
  const query = useResource<Items<EmployeeSkill | Requirement>>(path);
  const skills = useAll<Skill>('skills');
  const write = useWrite();
  const [edit, setEdit] = useState<EmployeeSkill | Requirement | 'new' | null>(null);
  const [remove, setRemove] = useState<EmployeeSkill | Requirement | null>(null);
  const fields: Field[] = [
    {
      name: 'skill_id',
      label: 'Kỹ năng',
      type: 'select',
      disabled: edit !== 'new',
      options: (skills.data || []).map((skill) => ({
        value: skill.skill_id,
        label: `${skill.name} · ${skill.category}`,
      })),
    },
    {
      name: isEmployee ? 'level' : 'min_level',
      label: isEmployee ? 'Mức thành thạo (1–5)' : 'Mức yêu cầu (1–5)',
      type: 'number',
      min: 1,
      max: 5,
      step: 1,
    },
    isEmployee
      ? {
          name: 'years_experience',
          label: 'Số năm kinh nghiệm',
          type: 'number',
          min: 0,
          max: 80,
          step: 0.1,
        }
      : {
          name: 'priority',
          label: 'Độ ưu tiên',
          type: 'select',
          options: options(['MUST', 'SHOULD', 'NICE']),
        },
  ];
  return (
    <section className="panel">
      <SectionHeading
        title={isEmployee ? 'Hồ sơ kỹ năng' : 'Yêu cầu kỹ năng'}
        detail={
          isEmployee
            ? 'Ghi nhận mức thành thạo và kinh nghiệm thực tế.'
            : 'Đặt mức năng lực cần thiết cho đội ngũ dự án.'
        }
        action={
          canEdit && (
            <AddButton onClick={() => setEdit('new')}>
              {isEmployee ? 'Gán kỹ năng' : 'Thêm yêu cầu'}
            </AddButton>
          )
        }
      />
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorNotice error={query.error} retry={() => void query.refetch()} />
      ) : !query.data.items.length ? (
        <Empty
          title={isEmployee ? 'Chưa có kỹ năng' : 'Chưa có yêu cầu'}
          detail="Thêm kỹ năng để SkillGraph hiểu rõ năng lực cần kết nối."
        />
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Kỹ năng</th>
                <th>Nhóm</th>
                <th>Mức độ</th>
                <th>{isEmployee ? 'Kinh nghiệm' : 'Ưu tiên'}</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((item) => (
                <tr key={item.skill_id}>
                  <td>
                    <strong>{item.skill_name}</strong>
                    <small>{item.skill_id}</small>
                  </td>
                  <td>{item.category}</td>
                  <td>
                    <span
                      className="level-dots"
                      aria-label={`Cấp ${'level' in item ? item.level : item.min_level}/5`}
                    >
                      {[1, 2, 3, 4, 5].map((n) => (
                        <i
                          key={n}
                          className={
                            n <= ('level' in item ? item.level : item.min_level) ? 'filled' : ''
                          }
                        />
                      ))}
                    </span>
                  </td>
                  <td>
                    {'years_experience' in item ? (
                      `${item.years_experience} năm`
                    ) : (
                      <Badge value={item.priority} />
                    )}
                  </td>
                  <td>
                    {canEdit ? (
                      <div className="row-actions">
                        <button
                          className="icon-button"
                          aria-label={`Sửa ${item.skill_name}`}
                          onClick={() => setEdit(item)}
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="icon-button delete-button"
                          aria-label={`Gỡ ${item.skill_name}`}
                          onClick={() => setRemove(item)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    ) : (
                      <small>Chỉ xem</small>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {edit && (
        <FormDialog
          title={isEmployee ? 'Cập nhật kỹ năng nhân viên' : 'Cập nhật yêu cầu kỹ năng'}
          submitDisabled={skills.isPending || skills.isError || !skills.data?.length}
          fields={skills.isPending || skills.isError ? [] : fields}
          initial={
            edit === 'new'
              ? { level: 3, min_level: 3, years_experience: 1, priority: 'MUST' }
              : { ...edit }
          }
          onClose={() => setEdit(null)}
          onSubmit={async (values) => {
            if (!skills.data) throw new Error('Danh mục kỹ năng chưa tải xong. Hãy thử lại.');
            const id = edit === 'new' ? String(values.skill_id) : edit.skill_id;
            const { skill_id: _, ...body } = values;
            await write(() => save(`${path}/${id}`, 'PUT', body));
          }}
        >
          {skills.isPending && <Loading />}
          {skills.error && <ErrorNotice error={skills.error} retry={() => void skills.refetch()} />}
          {skills.data?.length === 0 && (
            <p>Hãy thêm kỹ năng vào danh mục trước khi tạo liên kết.</p>
          )}
        </FormDialog>
      )}
      {remove && (
        <FormDialog
          title={`Gỡ ${remove.skill_name}?`}
          description="Chỉ gỡ liên kết này. Kỹ năng vẫn được giữ trong danh mục chung."
          danger
          submitLabel="Gỡ kỹ năng"
          onClose={() => setRemove(null)}
          onSubmit={() =>
            write(
              () => request(`${path}/${remove.skill_id}`, { method: 'DELETE' }),
              'Đã gỡ liên kết kỹ năng.',
            )
          }
        />
      )}
    </section>
  );
}
