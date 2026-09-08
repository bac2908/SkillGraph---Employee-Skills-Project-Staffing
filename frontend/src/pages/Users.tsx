import { useState } from 'react';
import { ChevronLeft, ChevronRight, KeyRound, Pencil, ShieldCheck } from 'lucide-react';
import { useAuth, roleLabel, type Role, type User } from '../auth';
import { save, useAll, useResource } from '../api';
import type { Page, Project } from '../types';
import {
  AddButton,
  Avatar,
  Empty,
  ErrorNotice,
  FormDialog,
  Loading,
  PageHeading,
  useWrite,
  type Field,
} from '../components/ui';

export function UsersPage() {
  const { isAdmin } = useAuth();
  return isAdmin ? (
    <UserDirectory />
  ) : (
    <Empty
      title="Bạn không có quyền truy cập"
      detail="Chỉ Admin được quản lý tài khoản và quyền truy cập."
    />
  );
}

function UserDirectory() {
  const { user: current } = useAuth();
  const [offset, setOffset] = useState(0);
  const query = useResource<Page<User>>(`/api/auth/users?limit=20&offset=${offset}`);
  const [edit, setEdit] = useState<User | 'new' | null>(null);
  const [reset, setReset] = useState<User | null>(null);
  const write = useWrite();
  return (
    <>
      <PageHeading
        eyebrow="QUẢN TRỊ KHÔNG GIAN"
        title="Đúng người, đúng quyền"
        description="Cấp tài khoản và xác định phạm vi quản lý rõ ràng cho đội ngũ."
        action={<AddButton onClick={() => setEdit('new')}>Thêm tài khoản</AddButton>}
      />
      <div className="access-note">
        <ShieldCheck size={20} />
        <p>
          Thay đổi quyền, khóa tài khoản hoặc đặt lại mật khẩu sẽ thu hồi các phiên đăng nhập hiện
          có. Tài khoản mới phải đổi mật khẩu khi đăng nhập lần đầu.
        </p>
      </div>
      <section className="panel">
        {query.isPending ? (
          <Loading />
        ) : query.isError ? (
          <ErrorNotice error={query.error} retry={() => void query.refetch()} />
        ) : (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Tài khoản</th>
                    <th>Quyền truy cập</th>
                    <th>Dự án quản lý</th>
                    <th>Trạng thái</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.items.map((user, index) => (
                    <tr key={user.user_id}>
                      <td>
                        <div className="identity">
                          <Avatar name={user.name} index={index} />
                          <div>
                            <strong>
                              {user.name}
                              {user.user_id === current?.user_id ? ' (Bạn)' : ''}
                            </strong>
                            <small>{user.email}</small>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="badge">{roleLabel(user.role)}</span>
                      </td>
                      <td className="description-cell">
                        {user.role === 'ADMIN'
                          ? 'Toàn bộ không gian'
                          : user.role === 'MANAGER'
                            ? user.project_ids.join(', ') || 'Chưa giao dự án'
                            : 'Chỉ đọc'}
                      </td>
                      <td>
                        <span
                          className={`badge ${user.is_active ? 'badge-active' : 'badge-cancelled'}`}
                        >
                          {user.is_active ? 'Hoạt động' : 'Đã khóa'}
                        </span>
                        {user.must_change_password && <small>Cần đổi mật khẩu</small>}
                      </td>
                      <td>
                        <div className="row-actions">
                          {user.user_id !== current?.user_id && (
                            <>
                              <button
                                className="icon-button"
                                aria-label={`Phân quyền ${user.name}`}
                                onClick={() => setEdit(user)}
                              >
                                <Pencil size={16} />
                              </button>
                              <button
                                className="icon-button"
                                aria-label={`Đặt lại mật khẩu ${user.name}`}
                                onClick={() => setReset(user)}
                              >
                                <KeyRound size={16} />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>
                {query.data.total} tài khoản · Trang {offset / 20 + 1}
              </span>
              <div>
                <button
                  className="icon-button"
                  aria-label="Trang trước"
                  disabled={!offset}
                  onClick={() => setOffset(offset - 20)}
                >
                  <ChevronLeft size={18} />
                </button>
                <button
                  className="icon-button"
                  aria-label="Trang sau"
                  disabled={offset + 20 >= query.data.total}
                  onClick={() => setOffset(offset + 20)}
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>
          </>
        )}
      </section>
      {edit && <UserEditor existing={edit === 'new' ? null : edit} onClose={() => setEdit(null)} />}
      {reset && (
        <FormDialog
          title={`Đặt lại mật khẩu ${reset.name}`}
          description="Cấp mật khẩu tạm và gửi qua kênh riêng an toàn. Người dùng phải đổi mật khẩu sau khi đăng nhập. Các phiên hiện tại sẽ bị đăng xuất."
          submitLabel="Đặt lại mật khẩu"
          fields={[passwordField]}
          onClose={() => setReset(null)}
          onSubmit={async (values) => {
            await write(
              () =>
                save(
                  `/api/auth/users/${encodeURIComponent(reset.user_id)}/password`,
                  'POST',
                  values,
                ),
              'Đã đặt lại mật khẩu và thu hồi phiên cũ.',
            );
          }}
        />
      )}
    </>
  );
}

const passwordField: Field = {
  name: 'password',
  label: 'Mật khẩu tạm',
  type: 'password',
  minLength: 15,
  maxLength: 128,
  autoComplete: 'new-password',
  hint: '15–128 ký tự. Không chia sẻ trong nhóm chat hoặc đưa vào Git.',
};

function UserEditor({ existing, onClose }: { existing: User | null; onClose: () => void }) {
  const [role, setRole] = useState<Role>(existing?.role || 'VIEWER');
  const [active, setActive] = useState(existing?.is_active ?? true);
  const [selected, setSelected] = useState(existing?.project_ids || []);
  const projects = useAll<Project>('projects');
  const write = useWrite();
  return (
    <FormDialog
      title={existing ? `Phân quyền ${existing.name}` : 'Thêm tài khoản'}
      description={
        existing
          ? 'Thay đổi sẽ đăng xuất các phiên hiện tại của người dùng.'
          : 'Tạo tài khoản nội bộ. Người dùng sẽ đổi mật khẩu tạm khi đăng nhập lần đầu.'
      }
      fields={
        existing
          ? []
          : [
              { name: 'name', label: 'Họ tên', maxLength: 100 },
              { name: 'email', label: 'Email', type: 'email', maxLength: 254, autoComplete: 'off' },
              passwordField,
            ]
      }
      submitDisabled={role === 'MANAGER' && (projects.isPending || !!projects.error)}
      onClose={onClose}
      onSubmit={async (values) => {
        const body = {
          ...values,
          role,
          project_ids: role === 'MANAGER' ? selected : [],
          ...(existing ? { is_active: active } : {}),
        };
        await write(
          () =>
            save(
              `/api/auth/users${existing ? `/${encodeURIComponent(existing.user_id)}` : ''}`,
              existing ? 'PATCH' : 'POST',
              body,
            ),
          existing
            ? 'Đã cập nhật quyền truy cập.'
            : 'Đã tạo tài khoản. Hãy gửi mật khẩu tạm qua kênh riêng.',
        );
      }}
    >
      <div className="permission-fields">
        <label>
          Quyền truy cập
          <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
            {(['VIEWER', 'MANAGER', 'ADMIN'] as const).map((value) => (
              <option key={value} value={value}>
                {roleLabel(value)}
              </option>
            ))}
          </select>
        </label>
        {existing && (
          <label>
            Trạng thái tài khoản
            <select
              value={String(active)}
              onChange={(event) => setActive(event.target.value === 'true')}
            >
              <option value="true">Hoạt động</option>
              <option value="false">Đã khóa</option>
            </select>
          </label>
        )}
        {role === 'MANAGER' && (
          <fieldset className="project-grants">
            <legend>Dự án được quản lý</legend>
            {projects.isPending ? (
              <Loading />
            ) : projects.error ? (
              <ErrorNotice error={projects.error} retry={() => void projects.refetch()} />
            ) : (
              projects.data?.map((project) => (
                <label key={project.project_id}>
                  <input
                    type="checkbox"
                    checked={selected.includes(project.project_id)}
                    onChange={(event) =>
                      setSelected(
                        event.target.checked
                          ? [...selected, project.project_id]
                          : selected.filter((id) => id !== project.project_id),
                      )
                    }
                  />
                  {project.name}
                  <small>{project.project_id}</small>
                </label>
              ))
            )}
            <small>
              Manager vẫn xem được dữ liệu chung, nhưng chỉ sửa và phân công trong các dự án được
              chọn.
            </small>
          </fieldset>
        )}
      </div>
    </FormDialog>
  );
}
