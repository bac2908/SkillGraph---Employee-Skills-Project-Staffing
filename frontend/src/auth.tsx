import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError, request, save, setCsrfToken } from './api';

export type Role = 'ADMIN' | 'MANAGER' | 'VIEWER';
export interface User {
  user_id: string;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  must_change_password: boolean;
  project_ids: string[];
}
interface Session {
  user: User;
  csrf_token: string;
}
interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: unknown;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  forget: (notice?: string, tone?: 'info' | 'success') => void;
  notice: { message: string; tone: 'info' | 'success' } | null;
  notifyTabs: () => void;
  isAdmin: boolean;
  canManageProject: (id: string) => boolean;
}
const AuthContext = createContext<AuthContextValue | null>(null);
const sessionEnded =
  'Phiên đăng nhập đã hết hạn hoặc bị thu hồi. Vui lòng đăng nhập lại để tiếp tục.';

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<AuthContextValue['notice']>(null);
  const currentId = useRef<string | null>(null);
  const revision = useRef(0);
  const channel = useRef<BroadcastChannel | null>(null);
  const clearCache = useCallback(() => {
    void client.cancelQueries();
    client.clear();
  }, [client]);
  const forget = useCallback(
    (message?: string, tone: 'info' | 'success' = 'info') => {
      if (message) setNotice({ message, tone });
      revision.current++;
      currentId.current = null;
      setCsrfToken(null);
      clearCache();
      setUser(null);
      setError(null);
      setLoading(false);
    },
    [clearCache],
  );
  const accept = useCallback(
    (session: Session) => {
      setNotice(null);
      if (currentId.current !== session.user.user_id) clearCache();
      currentId.current = session.user.user_id;
      setCsrfToken(session.csrf_token);
      setUser(session.user);
      setError(null);
      setLoading(false);
    },
    [clearCache],
  );
  const refresh = useCallback(async () => {
    const version = ++revision.current;
    try {
      const session = await request<Session>('/api/auth/me');
      if (version === revision.current) accept(session);
    } catch (err) {
      if (version !== revision.current) return;
      if (err instanceof ApiError && err.status === 401) {
        forget(currentId.current ? sessionEnded : undefined);
      } else {
        // A transient check failure is not evidence of an invalid session.
        // Keep an already-open draft; every business request is still authorized by BE.
        setError(err);
        setLoading(false);
      }
    }
  }, [accept, forget]);
  useEffect(() => {
    void refresh();
    const lost = () => forget(sessionEnded);
    const focused = () => {
      void refresh();
    };
    window.addEventListener('skillgraph:unauthorized', lost);
    window.addEventListener('focus', focused);
    if (typeof BroadcastChannel !== 'undefined') {
      channel.current = new BroadcastChannel('skillgraph-auth');
      channel.current.onmessage = () => {
        forget();
        setLoading(true);
        void refresh();
      };
    }
    return () => {
      revision.current++;
      window.removeEventListener('skillgraph:unauthorized', lost);
      window.removeEventListener('focus', focused);
      channel.current?.close();
      channel.current = null;
    };
  }, [forget, refresh]);
  const notifyTabs = () => channel.current?.postMessage('session-changed');
  const login = async (email: string, password: string) => {
    const session = await save<Session>('/api/auth/login', 'POST', { email, password });
    revision.current++;
    accept(session);
    notifyTabs();
  };
  const logout = async () => {
    try {
      await request('/api/auth/logout', { method: 'POST' });
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 401)) throw err;
    }
    forget();
    notifyTabs();
  };
  return (
    <AuthContext.Provider
      value={{
        user,
        notice,
        loading,
        error,
        login,
        logout,
        refresh,
        forget,
        notifyTabs,
        isAdmin: user?.role === 'ADMIN',
        canManageProject: (id) =>
          user?.role === 'ADMIN' || (user?.role === 'MANAGER' && user.project_ids.includes(id)),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('AuthProvider is required.');
  return auth;
}
export const roleLabel = (role: Role) =>
  ({ ADMIN: 'Quản trị viên', MANAGER: 'Quản lý dự án', VIEWER: 'Chỉ xem' })[role];
