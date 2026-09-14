import { useRef, useState, type ReactNode } from 'react';
import { ArrowRight, Eye, EyeOff, LockKeyhole, Network, ShieldCheck } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth, roleLabel } from '../auth';
import { save } from '../api';
import { ErrorNotice, Loading, PageHeading } from '../components/ui';

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="auth-layout">
      <aside className="auth-story">
        <Link className="brand" to="/">
          <Network size={28} />
          SkillGraph<span className="brand-dot">.</span>
        </Link>
        <div className="auth-story-content">
          <span className="auth-kicker">CON NGƯỜI · KỸ NĂNG · CƠ HỘI</span>
          <h1>
            Mỗi kết nối.
            <br />
            Một khả năng mới.
          </h1>
          <p>Hiểu năng lực đội ngũ, tìm đúng mảnh ghép và cùng nhau tạo nên những dự án tốt hơn.</p>
          <div className="auth-graph" aria-hidden="true">
            <span>Kỹ năng</span>
            <Network size={64} />
            <span>Đội ngũ</span>
            <span>Dự án</span>
          </div>
        </div>
        <div className="auth-story-foot">
          <ShieldCheck size={18} />
          Không gian làm việc dành riêng cho đội ngũ của bạn.
        </div>
      </aside>
      <main className="auth-main">
        <div className="auth-card">{children}</div>
        <p className="auth-footer">SkillGraph · Kết nối con người. Kiến tạo đội ngũ.</p>
      </main>
    </div>
  );
}

export function LoginPage() {
  const auth = useAuth();
  const location = useLocation();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [visible, setVisible] = useState(false);
  const submitting = useRef(false);
  return (
    <AuthLayout>
      <span className="auth-emblem">
        <LockKeyhole size={25} />
      </span>
      <span className="eyebrow">CHÀO MỪNG TRỞ LẠI</span>
      <h2>Đăng nhập không gian của bạn</h2>
      <p className="auth-intro">Tiếp tục kết nối năng lực và xây dựng đội ngũ.</p>
      {(auth.notice || location.state?.passwordChanged) && (
        <p className={auth.notice?.tone === 'info' ? 'auth-notice' : 'auth-success'} role="status">
          {auth.notice?.message ||
            'Đã đổi mật khẩu và đăng xuất các phiên cũ. Hãy đăng nhập bằng mật khẩu mới.'}
        </p>
      )}
      <form
        className="auth-form"
        onSubmit={async (event) => {
          event.preventDefault();
          if (submitting.current) return;
          const form = event.currentTarget;
          const data = new FormData(form);
          submitting.current = true;
          setPending(true);
          setError(null);
          try {
            await auth.login(String(data.get('email')).trim(), String(data.get('password')));
            form.reset();
          } catch (err) {
            setError(err);
            submitting.current = false;
            setPending(false);
          }
        }}
      >
        <fieldset disabled={pending}>
          <label>
            Email
            <input
              name="email"
              type="email"
              autoComplete="username"
              required
              maxLength={254}
              placeholder="ban@congty.com"
            />
          </label>
          <label>
            Mật khẩu
            <span className="password-input">
              <input
                name="password"
                type={visible ? 'text' : 'password'}
                autoComplete="current-password"
                required
                maxLength={128}
              />
              <button
                type="button"
                aria-label={visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                aria-pressed={visible}
                onClick={() => setVisible(!visible)}
              >
                {visible ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </span>
          </label>
          <button className="button primary auth-submit" disabled={pending}>
            {pending ? 'Đang đăng nhập…' : 'Đăng nhập'}
            <ArrowRight size={18} />
          </button>
        </fieldset>
        {error != null && <ErrorNotice error={error} focus />}
      </form>
      <p className="auth-help">
        Tài khoản được cấp bởi quản trị viên của tổ chức. Nếu chưa có tài khoản hoặc quên mật khẩu,
        hãy liên hệ quản trị viên để được hỗ trợ.
      </p>
    </AuthLayout>
  );
}

export function SessionLoading() {
  const auth = useAuth();
  return (
    <AuthLayout>
      <h2>Kết nối không gian</h2>
      {auth.error ? (
        <ErrorNotice error={auth.error} retry={() => void auth.refresh()} />
      ) : (
        <Loading />
      )}
    </AuthLayout>
  );
}

export function PasswordForm() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const submitting = useRef(false);
  return (
    <form
      className="auth-form"
      onSubmit={async (event) => {
        event.preventDefault();
        if (submitting.current) return;
        const data = new FormData(event.currentTarget);
        if (data.get('new_password') !== data.get('confirm_password')) {
          setError(new Error('Hai lần nhập mật khẩu mới chưa khớp.'));
          return;
        }
        submitting.current = true;
        setPending(true);
        setError(null);
        try {
          await save('/api/auth/password', 'POST', {
            current_password: data.get('current_password'),
            new_password: data.get('new_password'),
          });
          auth.forget(
            'Đã đổi mật khẩu và đăng xuất các phiên cũ. Hãy đăng nhập bằng mật khẩu mới.',
            'success',
          );
          auth.notifyTabs();
          navigate('/login', { replace: true, state: { passwordChanged: true } });
        } catch (err) {
          setError(err);
          submitting.current = false;
          setPending(false);
        }
      }}
    >
      <fieldset disabled={pending}>
        <input type="text" autoComplete="username" value={auth.user?.email || ''} readOnly hidden />
        <label>
          Mật khẩu hiện tại
          <input
            name="current_password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={128}
          />
        </label>
        <label>
          Mật khẩu mới
          <input
            name="new_password"
            type="password"
            autoComplete="new-password"
            required
            minLength={15}
            maxLength={128}
          />
        </label>
        <small>Dùng 15–128 ký tự. Có thể dùng một cụm từ dài, dễ nhớ và riêng biệt.</small>
        <label>
          Nhập lại mật khẩu mới
          <input
            name="confirm_password"
            type="password"
            autoComplete="new-password"
            required
            minLength={15}
            maxLength={128}
          />
        </label>
        <button className="button primary auth-submit" disabled={pending}>
          {pending ? 'Đang cập nhật…' : 'Đổi mật khẩu & đăng xuất'}
        </button>
      </fieldset>
      {error != null && <ErrorNotice error={error} focus />}
    </form>
  );
}

export function RequiredPasswordChange() {
  const auth = useAuth();
  const [error, setError] = useState<unknown>(null);
  return (
    <AuthLayout>
      <span className="auth-emblem">
        <ShieldCheck size={26} />
      </span>
      <h2>Tạo mật khẩu riêng của bạn</h2>
      <p className="auth-intro">
        Bạn đang dùng mật khẩu tạm. Hãy đổi trước khi truy cập dữ liệu SkillGraph.
      </p>
      <PasswordForm />
      <button className="text-button" onClick={() => void auth.logout().catch(setError)}>
        Đăng xuất tài khoản này
      </button>
      {error != null && <ErrorNotice error={error} />}
    </AuthLayout>
  );
}

export function AccountPage() {
  const { user } = useAuth();
  return (
    <>
      <PageHeading
        eyebrow="TÀI KHOẢN CÁ NHÂN"
        title="An toàn bắt đầu từ bạn"
        description="Quản lý thông tin đăng nhập và bảo vệ không gian làm việc."
      />
      <section className="panel account-panel">
        <span className="auth-emblem">
          <ShieldCheck size={24} />
        </span>
        <h2>{user?.name}</h2>
        <p>{user?.email}</p>
        <span className="badge">{user && roleLabel(user.role)}</span>
        {user?.role === 'MANAGER' && (
          <p>Dự án được quản lý: {user.project_ids.join(', ') || 'Chưa được giao dự án'}</p>
        )}
        <h3>Đổi mật khẩu</h3>
        <p>Thao tác này sẽ đăng xuất tất cả thiết bị đang dùng tài khoản.</p>
        <PasswordForm />
      </section>
    </>
  );
}
