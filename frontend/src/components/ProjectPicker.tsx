import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { Check, ChevronLeft, ChevronRight, Search, X } from 'lucide-react';
import { useResource } from '../api';
import type { Page, Project } from '../types';
import { Badge, Empty, ErrorNotice, Loading } from './ui';

const PAGE_SIZE = 10;

export function ProjectPicker({
  selectedId,
  onSelect,
  onClose,
}: {
  selectedId: string;
  onSelect: (project: Project) => void;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useId();
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [offset, setOffset] = useState(0);
  useLayoutEffect(() => {
    const element = dialog.current!;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    element.showModal();
    return () => {
      // Close before React removes the dialog; restore keyboard focus explicitly.
      element.close();
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    };
  }, []);
  useEffect(() => {
    if (search === debounced) return;
    const timer = setTimeout(() => {
      setDebounced(search);
      setOffset(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [search, debounced]);
  const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
  if (debounced.trim()) params.set('q', debounced.trim());
  const query = useResource<Page<Project>>(`/api/projects?${params}`);
  const items = query.data?.items || [];
  const searching = search !== debounced;
  return (
    <dialog
      ref={dialog}
      className="dialog project-search-dialog"
      aria-labelledby={heading}
      onKeyDownCapture={(event) => {
        // Search inputs otherwise consume Escape to clear text in some browsers.
        if (event.key === 'Escape') {
          event.preventDefault();
          event.stopPropagation();
          onClose();
        }
      }}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="dialog-heading">
        <div>
          <span className="eyebrow">PHÂN TÍCH ĐỘI NGŨ</span>
          <h2 id={heading}>Chọn dự án phân tích</h2>
        </div>
        <button
          type="button"
          className="icon-button"
          aria-label="Đóng chọn dự án"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      <p className="dialog-description">
        Tìm theo tên hoặc mã. Mỗi trang hiển thị tối đa 10 dự án.
      </p>
      <label className="search-field">
        <Search size={18} aria-hidden="true" />
        <input
          type="search"
          aria-label="Tìm dự án phân tích"
          placeholder="Tên hoặc mã dự án…"
          maxLength={100}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </label>
      {query.isPending || searching ? (
        <Loading />
      ) : query.isError ? (
        <ErrorNotice error={query.error} retry={() => void query.refetch()} />
      ) : !items.length ? (
        <Empty title="Không tìm thấy dự án" detail="Thử từ khóa khác hoặc quay lại trang trước." />
      ) : (
        <div className="project-search-results">
          {items.map((project) => (
            <button
              type="button"
              key={project.project_id}
              className="project-search-result"
              aria-label={`Chọn ${project.name}`}
              aria-pressed={project.project_id === selectedId}
              onClick={() => {
                onSelect(project);
                onClose();
              }}
            >
              <span>
                <strong>{project.name}</strong>
                <small>{project.project_id}</small>
              </span>
              <Badge value={project.status} />
              {project.project_id === selectedId && <Check size={18} aria-hidden="true" />}
            </button>
          ))}
        </div>
      )}
      <div className="pagination">
        <span aria-live="polite">
          {query.isError
            ? 'Chưa tải được danh sách'
            : query.data && !searching
              ? `${items.length ? offset + 1 : 0}–${offset + items.length} / ${query.data.total} dự án`
              : 'Đang tìm…'}
        </span>
        <div>
          <button
            type="button"
            className="icon-button"
            aria-label="Trang trước"
            disabled={offset === 0 || query.isFetching || searching}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            <ChevronLeft size={18} />
          </button>
          <button
            type="button"
            className="icon-button"
            aria-label="Trang sau"
            disabled={
              query.isFetching ||
              searching ||
              query.isError ||
              !query.data ||
              offset + PAGE_SIZE >= query.data.total
            }
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>
    </dialog>
  );
}
