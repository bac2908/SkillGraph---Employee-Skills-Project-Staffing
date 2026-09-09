import { useState, type FormEvent } from 'react';
import { ChevronLeft, ChevronRight, History, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useResource } from '../api';
import { useAuth } from '../auth';
import type { ActivityEvent, ActivityPage } from '../types';
import { Avatar, Empty, ErrorNotice, Loading, PageHeading } from './ui';

const actions = { CREATED: 'Đã tạo', UPDATED: 'Đã cập nhật', DELETED: 'Đã xóa' };
const kinds = {
  PROJECT: 'Thông tin dự án',
  WORKS_ON: 'Phân công nhân sự',
  REQUIRES_SKILL: 'Yêu cầu kỹ năng',
};
const fields: Record<string, string> = {
  project_id: 'Mã dự án',
  employee_id: 'Mã nhân viên',
  skill_id: 'Mã kỹ năng',
  name: 'Tên dự án',
  description: 'Mô tả',
  status: 'Trạng thái',
  role: 'Vai trò',
  allocation: 'Phân bổ (%)',
  min_level: 'Cấp độ tối thiểu',
  priority: 'Ưu tiên',
};
const initialFilters = {
  project_id: '',
  actor: '',
  action: '',
  resource_type: '',
  since: '',
  until: '',
};

export function ActivityPageView() {
  const { isAdmin } = useAuth();
  if (!isAdmin)
    return (
      <Empty title="Bạn không có quyền truy cập" detail="Chỉ Admin được xem nhật ký hoạt động." />
    );
  return (
    <>
      <PageHeading
        eyebrow="NHẬT KÝ DỰ ÁN"
        title="Mỗi thay đổi, một dấu vết."
        description="Theo dõi người thực hiện và nội dung thay đổi, kể cả dự án đã bị xóa."
      />
      <ActivityFeed />
    </>
  );
}

export function ActivityFeed({ projectId }: { projectId?: string }) {
  const { isAdmin } = useAuth();
  // Do not even mount the query for roles that cannot read history.
  return isAdmin ? <ActivityContent key={projectId || 'all'} projectId={projectId} /> : null;
}

function ActivityContent({ projectId }: { projectId?: string }) {
  const [draft, setDraft] = useState(initialFilters);
  const [filters, setFilters] = useState(initialFilters);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [formError, setFormError] = useState<string | null>(null);
  const params = new URLSearchParams({ limit: '20' });
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
  if (projectId) params.set('project_id', projectId);
  const cursor = cursors[cursors.length - 1];
  if (cursor) params.set('cursor', cursor);
  const query = useResource<ActivityPage>(`/api/activity?${params}`);
  const applyFilters = (event: FormEvent) => {
    event.preventDefault();
    if (draft.since && draft.until && new Date(draft.since) > new Date(draft.until)) {
      setFormError('Thời gian bắt đầu phải trước hoặc bằng thời gian kết thúc.');
      return;
    }
    setFormError(null);
    setFilters({
      ...draft,
      project_id: draft.project_id.trim(),
      actor: draft.actor.trim(),
      since: draft.since ? new Date(draft.since).toISOString() : '',
      until: draft.until ? new Date(draft.until).toISOString() : '',
    });
    setCursors([null]);
  };
  const update = (key: keyof typeof draft, value: string) =>
    setDraft((old) => ({ ...old, [key]: value }));
  return (
    <section className="panel activity-panel" aria-label="Nhật ký hoạt động dự án">
      <div className="activity-intro">
        <History size={22} aria-hidden="true" />
        <p>
          Chỉ ghi thay đổi từ khi tính năng được bật: thông tin dự án, phân công và yêu cầu kỹ năng.
          Không khôi phục lịch sử cũ.
        </p>
        <button
          className="button secondary"
          type="button"
          disabled={query.isFetching}
          onClick={() => {
            if (cursors.length > 1) setCursors([null]);
            else void query.refetch();
          }}
        >
          <RefreshCw size={16} />
          Mới nhất
        </button>
      </div>
      <form className="activity-filters" onSubmit={applyFilters}>
        {!projectId && (
          <label>
            Mã dự án
            <input
              value={draft.project_id}
              pattern="PROJ[0-9]{3,}"
              maxLength={100}
              placeholder="Tất cả dự án"
              onChange={(e) => update('project_id', e.target.value)}
            />
          </label>
        )}
        <label>
          Người thực hiện
          <input
            value={draft.actor}
            maxLength={100}
            placeholder="Tên hoặc mã tài khoản"
            onChange={(e) => update('actor', e.target.value)}
          />
        </label>
        <label>
          Hành động
          <select value={draft.action} onChange={(e) => update('action', e.target.value)}>
            <option value="">Tất cả hành động</option>
            {Object.entries(actions).map(([value, name]) => (
              <option key={value} value={value}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Loại thay đổi
          <select
            value={draft.resource_type}
            onChange={(e) => update('resource_type', e.target.value)}
          >
            <option value="">Tất cả loại</option>
            {Object.entries(kinds).map(([value, name]) => (
              <option key={value} value={value}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Từ thời điểm
          <input
            type="datetime-local"
            value={draft.since}
            onChange={(e) => update('since', e.target.value)}
          />
        </label>
        <label>
          Đến thời điểm
          <input
            type="datetime-local"
            value={draft.until}
            onChange={(e) => update('until', e.target.value)}
          />
        </label>
        <div className="activity-filter-actions">
          <button type="submit" className="button primary">
            Áp dụng bộ lọc
          </button>
          <button
            type="button"
            className="button secondary"
            onClick={() => {
              setDraft(initialFilters);
              setFilters(initialFilters);
              setCursors([null]);
              setFormError(null);
            }}
          >
            Xóa bộ lọc
          </button>
        </div>
      </form>
      {formError && (
        <p className="activity-form-error" role="alert">
          {formError}
        </p>
      )}
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorNotice error={query.error} retry={() => void query.refetch()} />
      ) : !query.data.items.length ? (
        <Empty
          title="Chưa có hoạt động phù hợp"
          detail="Thử thay đổi bộ lọc. Dữ liệu có sẵn trước khi bật nhật ký sẽ không có lịch sử."
        />
      ) : (
        <ol className="activity-list">
          {query.data.items.map((item) => (
            <ActivityItem key={item.event_id} item={item} showProject={!projectId} />
          ))}
        </ol>
      )}
      <div className="pagination">
        <span aria-live="polite">
          Trang {cursors.length}
          {query.data && !query.isError ? ` · ${query.data.items.length} hoạt động` : ''}
        </span>
        <div>
          <button
            className="icon-button"
            aria-label="Hoạt động mới hơn"
            disabled={cursors.length === 1 || query.isFetching}
            onClick={() => setCursors((old) => old.slice(0, -1))}
          >
            <ChevronLeft size={18} />
          </button>
          <button
            className="icon-button"
            aria-label="Hoạt động cũ hơn"
            disabled={!query.data?.next_cursor || query.isFetching || query.isError}
            onClick={() => {
              if (query.data?.next_cursor) setCursors((old) => [...old, query.data.next_cursor]);
            }}
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>
    </section>
  );
}

function ActivityItem({ item, showProject }: { item: ActivityEvent; showProject: boolean }) {
  const changed = [
    ...new Set([...Object.keys(item.before || {}), ...Object.keys(item.after || {})]),
  ].filter((key) => item.before?.[key] !== item.after?.[key]);
  return (
    <li className="activity-item">
      <Avatar name={item.actor_name} />
      <div className="activity-body">
        <div className="activity-item-heading">
          <strong>{item.actor_name}</strong>
          <time dateTime={item.occurred_at}>
            {new Date(item.occurred_at).toLocaleString('vi-VN')}
          </time>
        </div>
        <p>
          <span className={`activity-action activity-${item.action.toLowerCase()}`}>
            {actions[item.action]}
          </span>{' '}
          {kinds[item.resource_type]}
        </p>
        <small className="activity-resource">{item.resource_id}</small>
        {showProject && (
          <Link
            className="text-link"
            to={`/projects/${encodeURIComponent(item.project_id)}?tab=activity`}
          >
            Mở {item.project_id}
          </Link>
        )}
        <details className="activity-diff">
          <summary>Xem thay đổi</summary>
          <table aria-label={`Thay đổi ${item.resource_id}`}>
            <thead>
              <tr>
                <th>Trường</th>
                <th>Trước</th>
                <th>Sau</th>
              </tr>
            </thead>
            <tbody>
              {changed.map((key) => (
                <tr key={key}>
                  <th scope="row">{fields[key] || key}</th>
                  <td>{String(item.before?.[key] ?? '—')}</td>
                  <td>{String(item.after?.[key] ?? '—')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </div>
    </li>
  );
}
