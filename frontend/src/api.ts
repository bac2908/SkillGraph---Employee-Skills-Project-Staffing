import { useQuery } from '@tanstack/react-query';
import type { Page } from './types';

let csrfToken: string | null = null;
export const setCsrfToken = (token: string | null) => {
  csrfToken = token;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function readableDetail(detail: string): string {
  const linked =
    /^(Employee|Skill|Project) '[^']+' is connected by (\d+) relationship\(s\) and cannot be deleted\.$/.exec(
      detail,
    );
  if (linked)
    return `Bản ghi còn ${linked[2]} liên kết với dữ liệu khác. Hãy gỡ liên kết trước khi xóa.`;
  const allocation =
    /^Employee 'EMP\d+' would reach (\d+)% total allocation: (\d+)% outside Project 'PROJ\d+' plus (\d+)% requested\. The maximum is 100%\.$/.exec(
      detail,
    );
  if (allocation)
    return `Tổng phân bổ sẽ là ${allocation[1]}% (${allocation[2]}% ở dự án khác + ${allocation[3]}% yêu cầu). Giới hạn là 100%. Hãy giảm tỷ lệ hoặc điều chỉnh phân công khác.`;
  return detail;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isWrite = !['GET', 'HEAD', 'OPTIONS'].includes(init.method || 'GET');
  const uncertainWrite =
    isWrite && !['/api/auth/login', '/api/auth/logout', '/api/auth/password'].includes(path)
      ? ' Chưa xác nhận được kết quả ghi. Hãy kiểm tra dữ liệu trước khi gửi lại để tránh thao tác trùng.'
      : '';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  const abort = () => controller.abort();
  init.signal?.addEventListener('abort', abort, { once: true });
  if (init.signal?.aborted) controller.abort();
  try {
    const response = await fetch(path, {
      ...init,
      credentials: 'same-origin',
      signal: controller.signal,
      headers: {
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...(csrfToken && !['GET', 'HEAD', 'OPTIONS'].includes(init.method || 'GET')
          ? { 'X-CSRF-Token': csrfToken }
          : {}),
        ...init.headers,
      },
    });
    if (!response.ok) {
      if (response.status === 401 && path !== '/api/auth/login' && path !== '/api/auth/me') {
        window.dispatchEvent(new Event('skillgraph:unauthorized'));
      }
      const data = await response.json().catch(() => null);
      const detail = data?.detail;
      const message =
        response.status === 503
          ? 'Dịch vụ dữ liệu tạm thời chưa sẵn sàng. Vui lòng thử lại sau hoặc liên hệ quản trị viên.' +
            uncertainWrite
          : response.status >= 500
            ? 'Hệ thống gặp lỗi khi xử lý yêu cầu. Vui lòng thử lại sau hoặc liên hệ quản trị viên.' +
              uncertainWrite
            : Array.isArray(detail)
              ? detail
                  .map(
                    (issue: { loc?: string[]; msg: string }) =>
                      `${issue.loc?.slice(1).join('.') || 'Dữ liệu'}: ${issue.msg}`,
                  )
                  .join(' · ')
              : typeof detail === 'string'
                ? readableDetail(detail)
                : `Yêu cầu không thành công (${response.status}).`;
      throw new ApiError(response.status, message);
    }
    return response.status === 204 ? (undefined as T) : await response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (init.signal?.aborted) throw error;
    throw new Error(
      controller.signal.aborted
        ? 'Yêu cầu quá thời gian chờ. Vui lòng kiểm tra kết nối.' + uncertainWrite
        : 'Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối mạng hoặc liên hệ quản trị viên.' +
            uncertainWrite,
    );
  } finally {
    clearTimeout(timeout);
    init.signal?.removeEventListener('abort', abort);
  }
}

export const save = <T>(
  path: string,
  method: 'POST' | 'PATCH' | 'PUT',
  data: Record<string, unknown>,
) => request<T>(path, { method, body: JSON.stringify(data) });

export function useResource<T>(path: string | null) {
  return useQuery<T>({
    queryKey: ['api', path],
    enabled: !!path,
    queryFn: ({ signal }) => request<T>(path!, { signal }),
  });
}

// Fetch every page for legacy selectors; never silently truncate at API limit 100.
export async function getAll<T>(resource: string, signal?: AbortSignal): Promise<T[]> {
  const result: T[] = [];
  let offset = 0;
  while (true) {
    const page = await request<Page<T>>(`/api/${resource}?limit=100&offset=${offset}`, { signal });
    result.push(...page.items);
    if (result.length >= page.total || !page.items.length) return result;
    offset += page.items.length;
  }
}

export function useAll<T>(resource: string) {
  return useQuery({
    queryKey: ['api', 'all', resource],
    queryFn: ({ signal }) => getAll<T>(resource, signal),
  });
}
