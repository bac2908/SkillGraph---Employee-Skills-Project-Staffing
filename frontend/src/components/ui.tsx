import { createContext, useContext, useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { AlertCircle, Check, ChevronRight, LoaderCircle, Network, Plus, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

const labels: Record<string, string> = { AVAILABLE: 'Sẵn sàng', ASSIGNED: 'Đã phân công', UNAVAILABLE: 'Không sẵn sàng', ON_LEAVE: 'Nghỉ phép', ACTIVE: 'Đang thực hiện', PLANNING: 'Lên kế hoạch', ON_HOLD: 'Tạm dừng', COMPLETED: 'Hoàn thành', CANCELLED: 'Đã hủy', COVERED: 'Đáp ứng', GAP: 'Cần nâng cấp', MISSING: 'Chưa có', MUST: 'Bắt buộc', SHOULD: 'Ưu tiên', NICE: 'Bổ trợ' };
export const label = (value: string) => labels[value] || value;
export const initials = (name: string) => name.trim().split(/\s+/).slice(-2).map(p => p[0]).join('').toUpperCase();
export function Avatar({ name, index = 0 }: { name: string; index?: number }) { return <span className={`avatar avatar-${index % 4}`} aria-hidden="true">{initials(name)}</span>; }
export function Badge({ value }: { value: string }) { return <span className={`badge badge-${value.toLowerCase()}`}><i />{label(value)}</span>; }
export function Meter({ value, label: text }: { value: number; label?: string }) { return <div className="meter" role="meter" aria-label={text || 'Tỷ lệ'} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${Math.min(100, Math.max(0, value))}%` }} /></div>; }
export function Empty({ title = 'Chưa có dữ liệu', detail = 'Thêm dữ liệu đầu tiên để bắt đầu.', action }: { title?: string; detail?: string; action?: ReactNode }) { return <div className="empty"><span className="empty-icon"><Network size={26} /></span><h3>{title}</h3><p>{detail}</p>{action}</div>; }
export function Loading() { return <div className="loading" role="status"><LoaderCircle size={20} className="spin" /> Đang tải dữ liệu…<div className="skeleton" /><div className="skeleton" /></div>; }
export function ErrorNotice({ error, retry }: { error: unknown; retry?: () => void }) { return <div className="error-notice" role="alert"><AlertCircle size={20} /><div><strong>Chưa thực hiện được yêu cầu</strong><p>{error instanceof Error ? error.message : String(error)}</p>{retry && <button className="text-button" onClick={retry}>Thử lại</button>}</div></div>; }
export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) { return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</div>; }
export function BackLink({ to, children }: { to: string; children: ReactNode }) { return <Link className="back-link" to={to}>← {children}</Link>; }
export function SectionHeading({ title, detail, action }: { title: string; detail?: string; action?: ReactNode }) { return <div className="section-heading"><div><h2>{title}</h2>{detail && <p>{detail}</p>}</div>{action}</div>; }
export function AddButton({ children, onClick }: { children: ReactNode; onClick: () => void }) { return <button className="button primary" onClick={onClick}><Plus size={17} />{children}</button>; }
export function TextLink({ to, children }: { to: string; children: ReactNode }) { return <Link className="text-link" to={to}>{children}<ChevronRight size={16} /></Link>; }

const ToastContext = createContext<(message: string) => void>(() => {});
export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('');
  useEffect(() => { if (message) { const timer = setTimeout(() => setMessage(''), 5000); return () => clearTimeout(timer); } }, [message]);
  return <ToastContext.Provider value={setMessage}>{children}{message && <div className="toast" role="status"><Check size={18} />{message}<button aria-label="Đóng thông báo" onClick={() => setMessage('')}><X size={16} /></button></div>}</ToastContext.Provider>;
}
export function useWrite() {
  const client = useQueryClient();
  const notify = useContext(ToastContext);
  return async (operation: () => Promise<unknown>, message = 'Đã lưu thay đổi.') => {
    await operation();
    // The write is committed; refresh failures are reported by each query panel.
    void client.invalidateQueries({ queryKey: ['api'] });
    notify(message);
  };
}

export interface Field { name: string; label: string; type?: 'text' | 'email' | 'number' | 'textarea' | 'select'; options?: { value: string; label: string }[]; required?: boolean; min?: number; max?: number; maxLength?: number; step?: number; pattern?: string; hint?: string; disabled?: boolean }
export function FormDialog({ title, description, fields = [], initial = {}, submitLabel = 'Lưu thay đổi', danger = false, submitDisabled = false, onSubmit, onClose, children }: {
  title: string; description?: string; fields?: Field[]; initial?: Record<string, unknown>; submitLabel?: string; danger?: boolean; submitDisabled?: boolean;
  onSubmit: (values: Record<string, unknown>) => Promise<void>; onClose: () => void; children?: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const headingId = useId();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => { const dialog = ref.current!; dialog.showModal(); return () => dialog.close(); }, []);
  return <dialog ref={ref} className="dialog" aria-labelledby={headingId} onCancel={event => { event.preventDefault(); if (!pending) onClose(); }}>
    <form onSubmit={async event => {
      event.preventDefault(); if (pending || submitDisabled) return;
      const form = new FormData(event.currentTarget);
      const values = Object.fromEntries(fields.filter(f => !f.disabled).map(f => [f.name, f.type === 'number' ? Number(form.get(f.name)) : String(form.get(f.name) ?? '').trim()]));
      setPending(true); setError(null);
      try { await onSubmit(values); onClose(); } catch (err) { setError(err); setPending(false); }
    }}>
      <div className="dialog-heading"><div><span className="eyebrow">SKILLGRAPH WORKSPACE</span><h2 id={headingId}>{title}</h2></div><button type="button" className="icon-button" aria-label="Đóng biểu mẫu" disabled={pending} onClick={onClose}><X size={20} /></button></div>
      {description && <p className="dialog-description">{description}</p>}{children}
      <fieldset disabled={pending} className="form-fields">
        {fields.map(f => <label key={f.name} className={f.type === 'textarea' ? 'wide' : ''}><span>{f.label}{f.required !== false && <b aria-hidden="true"> *</b>}</span>
          {f.type === 'select' ? <select name={f.name} required={f.required !== false} disabled={f.disabled} defaultValue={String(initial[f.name] ?? '')}><option value="" disabled>Chọn {f.label.toLowerCase()}</option>{f.options?.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
          : f.type === 'textarea' ? <textarea name={f.name} required={f.required !== false} maxLength={f.maxLength} rows={3} defaultValue={String(initial[f.name] ?? '')} />
          : <input name={f.name} type={f.type || 'text'} required={f.required !== false} disabled={f.disabled} min={f.min} max={f.max} step={f.step} maxLength={f.maxLength} pattern={f.pattern} defaultValue={String(initial[f.name] ?? '')} />}
          {f.hint && <small>{f.hint}</small>}
        </label>)}
      </fieldset>
      {error != null && <ErrorNotice error={error} />}
      <div className="dialog-footer"><button type="button" className="button secondary" disabled={pending} onClick={onClose}>Hủy</button><button type="submit" className={`button ${danger ? 'danger' : 'primary'}`} disabled={pending || submitDisabled}>{pending && <LoaderCircle size={16} className="spin" />}{pending ? 'Đang lưu…' : submitLabel}</button></div>
    </form>
  </dialog>;
}
