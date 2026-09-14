import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ChevronLeft, ChevronRight, Pencil, Search, Trash2 } from 'lucide-react';
import { configs, type Entity, type Resource } from '../config';
import { request, save, useResource } from '../api';
import type { Page } from '../types';
import { useAuth } from '../auth';
import {
  AddButton,
  AvailabilityNote,
  Avatar,
  Badge,
  Empty,
  ErrorNotice,
  FormDialog,
  Loading,
  PageHeading,
  label,
  useWrite,
} from '../components/ui';

export function Directory({ resource }: { resource: Resource }) {
  const { isAdmin, canManageProject } = useAuth();
  const config = configs[resource];
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [filter, setFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const [edit, setEdit] = useState<Entity | 'new' | null>(null);
  const [remove, setRemove] = useState<Entity | null>(null);
  useEffect(() => {
    if (search === debounced) return;
    const timer = setTimeout(() => {
      setDebounced(search);
      setOffset(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [search, debounced]);
  const params = new URLSearchParams({ limit: '10', offset: String(offset) });
  if (debounced.trim()) params.set('q', debounced.trim());
  if (filter.trim()) params.set(config.filter!, filter.trim());
  const query = useResource<Page<Entity>>(`/api/${resource}?${params}`);
  const write = useWrite();
  const rows = query.data?.items || [];
  return (
    <>
      <PageHeading
        eyebrow={`KHÔNG GIAN ${config.singular.toUpperCase()}`}
        title={config.title}
        description={config.description}
        action={
          isAdmin && <AddButton onClick={() => setEdit('new')}>Thêm {config.singular}</AddButton>
        }
      />
      {resource === 'employees' && <AvailabilityNote />}
      <section className="panel directory-panel">
        <div className="toolbar">
          <label className="search-field">
            <Search size={18} />
            <input
              aria-label={`Tìm ${config.singular}`}
              placeholder={`Tìm ${config.singular} theo tên hoặc mã…`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          {config.statuses ? (
            <select
              aria-label="Lọc trạng thái"
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">Tất cả trạng thái</option>
              {config.statuses.map((s) => (
                <option key={s} value={s}>
                  {label(s)}
                </option>
              ))}
            </select>
          ) : (
            <input
              aria-label="Lọc nhóm kỹ năng"
              placeholder="Lọc nhóm kỹ năng…"
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value);
                setOffset(0);
              }}
            />
          )}
        </div>
        {query.isPending ? (
          <Loading />
        ) : query.isError ? (
          <ErrorNotice error={query.error} retry={() => void query.refetch()} />
        ) : !rows.length ? (
          <Empty
            title="Không có kết quả"
            detail={
              search || filter
                ? 'Thử thay đổi từ khóa hoặc bộ lọc.'
                : `Thêm ${config.singular} đầu tiên cho không gian của bạn.`
            }
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>
                    {resource === 'employees'
                      ? 'Nhân viên'
                      : resource === 'projects'
                        ? 'Dự án'
                        : 'Kỹ năng'}
                  </th>
                  <th>
                    {resource === 'employees'
                      ? 'Chức danh'
                      : resource === 'projects'
                        ? 'Mô tả'
                        : 'Nhóm kỹ năng'}
                  </th>
                  {resource !== 'skills' && <th>Trạng thái</th>}
                  <th className="align-right">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={String(row[config.id])}>
                    <td>
                      <div className="identity">
                        {resource === 'employees' && <Avatar name={row.name} index={index} />}
                        <div>
                          {resource !== 'skills' ? (
                            <Link className="entity-link" to={`/${resource}/${row[config.id]}`}>
                              {row.name}
                              <ArrowUpRight size={14} />
                            </Link>
                          ) : (
                            <strong>{row.name}</strong>
                          )}
                          <small>
                            {String(row[config.id])}
                            {resource === 'employees' && ` · ${row.email}`}
                          </small>
                        </div>
                      </div>
                    </td>
                    <td className="description-cell">
                      {String(
                        row[
                          resource === 'employees'
                            ? 'title'
                            : resource === 'projects'
                              ? 'description'
                              : 'category'
                        ],
                      )}
                      {resource === 'employees' && (
                        <small>
                          {String(row.seniority)} · {String(row.location)}
                        </small>
                      )}
                    </td>
                    {resource !== 'skills' && (
                      <td>
                        <Badge value={String(row.status)} />
                      </td>
                    )}
                    <td>
                      <div className="row-actions">
                        {(isAdmin ||
                          (resource === 'projects' &&
                            canManageProject(String(row[config.id])))) && (
                          <button
                            className="icon-button"
                            aria-label={`Sửa ${row.name}`}
                            onClick={() => setEdit(row)}
                          >
                            <Pencil size={16} />
                          </button>
                        )}
                        {isAdmin && (
                          <button
                            className="icon-button delete-button"
                            aria-label={`Xóa ${row.name}`}
                            onClick={() => setRemove(row)}
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                        {!(
                          isAdmin ||
                          (resource === 'projects' && canManageProject(String(row[config.id])))
                        ) && <small>Chỉ xem</small>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {query.data && (
          <div className="pagination">
            <span>
              {query.data.total ? `${offset + 1}–${offset + rows.length}` : '0'} /{' '}
              {query.data.total} {config.singular}
            </span>
            <div>
              <button
                className="icon-button"
                aria-label="Trang trước"
                disabled={!offset}
                onClick={() => setOffset((v) => Math.max(0, v - 10))}
              >
                <ChevronLeft size={18} />
              </button>
              <button
                className="icon-button"
                aria-label="Trang sau"
                disabled={offset + 10 >= query.data.total}
                onClick={() => setOffset((v) => v + 10)}
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}
      </section>
      {edit && (
        <FormDialog
          title={`${edit === 'new' ? 'Thêm' : 'Chỉnh sửa'} ${config.singular}`}
          fields={config.fields.map((f) => ({
            ...f,
            disabled: edit !== 'new' && f.name === config.id,
          }))}
          initial={
            edit === 'new'
              ? { seniority: 'Junior', status: resource === 'employees' ? 'AVAILABLE' : 'PLANNING' }
              : edit
          }
          onClose={() => setEdit(null)}
          onSubmit={async (values) => {
            await write(() =>
              save(
                `/api/${resource}${edit === 'new' ? '' : `/${edit[config.id]}`}`,
                edit === 'new' ? 'POST' : 'PATCH',
                values,
              ),
            );
          }}
        />
      )}
      {remove && (
        <FormDialog
          title={`Xóa ${remove.name}?`}
          description="Thao tác này xóa bản ghi. Nếu vẫn còn quan hệ với nhân viên, kỹ năng hoặc dự án, hệ thống sẽ yêu cầu bạn gỡ liên kết trước."
          submitLabel="Xác nhận xóa"
          danger
          onClose={() => setRemove(null)}
          onSubmit={async () => {
            await write(
              () => request(`/api/${resource}/${remove[config.id]}`, { method: 'DELETE' }),
              'Đã xóa bản ghi.',
            );
            if (rows.length === 1 && offset) setOffset((v) => Math.max(0, v - 10));
          }}
        />
      )}
    </>
  );
}
