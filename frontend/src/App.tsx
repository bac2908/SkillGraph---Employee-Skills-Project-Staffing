import { useEffect, useState } from 'react';
import {
  BriefcaseBusiness,
  ChevronRight,
  LayoutDashboard,
  Layers3,
  Menu,
  Network,
  RefreshCw,
  Users,
  X,
  LogOut,
  ShieldCheck,
  History,
} from 'lucide-react';
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useIsFetching, useQueryClient } from '@tanstack/react-query';
import { Dashboard } from './pages/Dashboard';
import { Directory } from './pages/Directory';
import { EmployeeDetail, ProjectDetail } from './pages/Details';
import { ErrorNotice, FeedbackProvider, PageHeading, initials } from './components/ui';
import { useAuth, roleLabel } from './auth';
import { AccountPage, LoginPage, RequiredPasswordChange, SessionLoading } from './pages/Auth';
import { UsersPage } from './pages/Users';
import { ActivityPageView } from './components/Activity';

const nav = [
  { to: '/', label: 'Tổng quan', icon: LayoutDashboard },
  { to: '/employees', label: 'Nhân viên', icon: Users },
  { to: '/skills', label: 'Kỹ năng', icon: Layers3 },
  { to: '/projects', label: 'Dự án', icon: BriefcaseBusiness },
];

export default function App() {
  const auth = useAuth();
  const location = useLocation();
  if (auth.loading || auth.error) return <SessionLoading />;
  if (!auth.user)
    return location.pathname === '/login' ? (
      <LoginPage />
    ) : (
      <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
    );
  if (auth.user.must_change_password) return <RequiredPasswordChange />;
  if (location.pathname === '/login') {
    const from = location.state?.from;
    const destination =
      typeof from === 'string' &&
      from.startsWith('/') &&
      !from.startsWith('//') &&
      !from.startsWith('/login')
        ? from
        : '/';
    return <Navigate to={destination} replace />;
  }
  return <AppShell key={auth.user.user_id} />;
}

function AppShell() {
  const auth = useAuth();
  const [logoutPending, setLogoutPending] = useState(false);
  const [logoutError, setLogoutError] = useState<unknown>(null);
  const navigation = auth.isAdmin
    ? [
        ...nav,
        { to: '/users', label: 'Tài khoản', icon: ShieldCheck },
        { to: '/activity', label: 'Hoạt động', icon: History },
      ]
    : nav;
  const [menu, setMenu] = useState(false);
  const location = useLocation();
  const client = useQueryClient();
  const fetching = useIsFetching({ queryKey: ['api'] });
  const current =
    navigation.find((item) => item.to !== '/' && location.pathname.startsWith(item.to)) ||
    (location.pathname === '/account' ? { label: 'Tài khoản cá nhân' } : nav[0]);
  useEffect(() => {
    setMenu(false);
    window.scrollTo(0, 0);
    document.title = `${current.label} · SkillGraph`;
  }, [location.pathname, current.label]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenu(false);
    };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, []);
  return (
    <FeedbackProvider>
      <a className="skip-link" href="#main">
        Đi đến nội dung
      </a>
      <div className="app-shell">
        {menu && (
          <button
            className="sidebar-backdrop"
            aria-label="Đóng menu"
            onClick={() => setMenu(false)}
          />
        )}
        <aside className={`sidebar ${menu ? 'is-open' : ''}`}>
          <Link className="brand" to="/">
            <span>
              <Network size={24} />
            </span>
            SkillGraph<span className="brand-dot">.</span>
          </Link>
          <div className="workspace-label">
            <span className="workspace-avatar">SG</span>
            <div>
              <strong>Không gian nhân sự</strong>
              <small>Employee & Project Staffing</small>
            </div>
          </div>
          <span className="nav-label">WORKSPACE</span>
          <nav aria-label="Điều hướng chính">
            {navigation.map((item) => (
              <NavLink to={item.to} key={item.to} end={item.to === '/'}>
                <item.icon size={19} />
                {item.label}
                <ChevronRight className="nav-arrow" size={15} />
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-note">
              <Network size={23} />
              <h3>Kết nối đúng năng lực.</h3>
              <p>Mở ra cơ hội để mỗi người phát huy thế mạnh.</p>
            </div>
            <div className="workspace-mode">
              <i />
              Không gian phát triển<span>v0.1</span>
            </div>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <div className="breadcrumbs">
              <button
                className="icon-button menu-toggle"
                aria-label={menu ? 'Đóng menu' : 'Mở menu'}
                aria-expanded={menu}
                onClick={() => setMenu((v) => !v)}
              >
                {menu ? <X size={20} /> : <Menu size={20} />}
              </button>
              <span>Workspace</span>
              <ChevronRight size={14} />
              <strong>{current.label}</strong>
            </div>
            <div className="topbar-actions">
              <span className="today">
                {new Intl.DateTimeFormat('vi-VN', {
                  day: '2-digit',
                  month: 'long',
                  year: 'numeric',
                }).format(new Date())}
              </span>
              <button
                className="icon-button"
                title="Làm mới dữ liệu"
                aria-label="Làm mới dữ liệu"
                disabled={fetching > 0}
                onClick={() => void client.invalidateQueries({ queryKey: ['api'] })}
              >
                <RefreshCw size={18} className={fetching ? 'spin' : ''} />
              </button>
              <Link className="account-link" to="/account" aria-label="Tài khoản cá nhân">
                <span className="account-caption">
                  <strong>{auth.user?.name}</strong>
                  <small>{auth.user && roleLabel(auth.user.role)}</small>
                </span>
                <span className="top-avatar">{initials(auth.user?.name || 'SG')}</span>
              </Link>
              <button
                className="icon-button"
                aria-label="Đăng xuất"
                title="Đăng xuất"
                disabled={logoutPending}
                onClick={async () => {
                  setLogoutPending(true);
                  setLogoutError(null);
                  try {
                    await auth.logout();
                  } catch (error) {
                    setLogoutError(error);
                    setLogoutPending(false);
                  }
                }}
              >
                <LogOut size={18} />
              </button>
            </div>
          </header>
          <main id="main" tabIndex={-1}>
            {logoutError != null && <ErrorNotice error={logoutError} />}
            <Routes>
              <Route path="/account" element={<AccountPage />} />
              <Route path="/users" element={<UsersPage />} />
              <Route path="/activity" element={<ActivityPageView />} />
              <Route path="/" element={<Dashboard />} />
              <Route
                path="/employees"
                element={<Directory key="employees" resource="employees" />}
              />
              <Route path="/employees/:id" element={<EmployeeDetail />} />
              <Route path="/skills" element={<Directory key="skills" resource="skills" />} />
              <Route path="/projects" element={<Directory key="projects" resource="projects" />} />
              <Route path="/projects/:id" element={<ProjectDetail />} />
              <Route
                path="*"
                element={
                  <>
                    <PageHeading
                      eyebrow="404"
                      title="Không tìm thấy trang"
                      description="Đường dẫn này chưa có trong không gian SkillGraph."
                    />
                    <Link className="button primary" to="/">
                      Về tổng quan
                    </Link>
                  </>
                }
              />
            </Routes>
          </main>
          <footer className="app-footer">
            <span>SkillGraph</span>
            <span>Kết nối con người. Kiến tạo đội ngũ.</span>
          </footer>
        </div>
      </div>
    </FeedbackProvider>
  );
}
