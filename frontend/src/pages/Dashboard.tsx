import { useState } from 'react';
import {
  ArrowRight,
  BriefcaseBusiness,
  Layers3,
  Sparkles,
  Users,
  UserRoundCheck,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAll } from '../api';
import { useCapacity } from '../hooks';
import type { Candidate, Employee, Project, Skill } from '../types';
import {
  Avatar,
  Empty,
  ErrorNotice,
  Loading,
  Meter,
  PageHeading,
  SectionHeading,
  TextLink,
} from '../components/ui';
import { CandidateSuggestions, SkillCoverage } from '../components/Analysis';
import { AssignmentDialog } from '../components/Relations';

export function Dashboard() {
  const employees = useAll<Employee>('employees');
  const projects = useAll<Project>('projects');
  const skills = useAll<Skill>('skills');
  const capacity = useCapacity();
  const [selected, setSelected] = useState('');
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const selectedProject =
    projects.data?.find((p) => p.project_id === selected) ||
    projects.data?.find((p) => p.status === 'ACTIVE') ||
    projects.data?.[0];
  const available = employees.data?.filter((e) => e.status === 'AVAILABLE') || [];
  const stats = [
    {
      title: 'Nhân viên',
      value: employees.data?.length,
      icon: Users,
      note: 'Những tài năng trong tổ chức',
      to: '/employees',
      tone: 'green',
      error: employees.error,
    },
    {
      title: 'Sẵn sàng kết nối',
      value: employees.data ? available.length : undefined,
      icon: UserRoundCheck,
      note: 'Theo trạng thái nhân viên',
      to: '/employees',
      tone: 'mint',
      error: employees.error,
    },
    {
      title: 'Dự án đang chạy',
      value: projects.data?.filter((p) => p.status === 'ACTIVE').length,
      icon: BriefcaseBusiness,
      note: `${projects.data?.length ?? '…'} dự án trong không gian`,
      to: '/projects',
      tone: 'amber',
      error: projects.error,
    },
    {
      title: 'Kỹ năng',
      value: skills.data?.length,
      icon: Layers3,
      note: 'Nền tảng năng lực chung',
      to: '/skills',
      tone: 'blue',
      error: skills.error,
    },
  ];
  const freePeople = [...(employees.data || [])]
    .sort(
      (a, b) =>
        (capacity.totals.get(a.employee_id) || 0) - (capacity.totals.get(b.employee_id) || 0),
    )
    .slice(0, 5);
  return (
    <>
      <PageHeading
        eyebrow="TỔNG QUAN KHÔNG GIAN"
        title="Đúng người. Đúng cơ hội."
        description="Một góc nhìn rõ ràng để xây dựng những đội ngũ tốt hơn."
        action={
          <Link className="button primary" to="/projects">
            Khám phá dự án
            <ArrowRight size={17} />
          </Link>
        }
      />
      <div className="welcome-banner">
        <div>
          <span className="banner-tag">
            <Sparkles size={14} /> KẾT NỐI NĂNG LỰC
          </span>
          <h2>Mỗi kỹ năng là một khả năng mới.</h2>
          <p>Biến hiểu biết về đội ngũ thành những quyết định phân công phù hợp.</p>
        </div>
        <div className="connection-art" aria-hidden="true">
          <svg viewBox="0 0 330 150">
            <path d="M35 80 115 35 198 76 276 30M35 80 116 125 198 76 275 124M115 35 116 125M276 30 275 124" />
            <circle cx="35" cy="80" r="18" />
            <circle cx="115" cy="35" r="13" />
            <circle cx="116" cy="125" r="12" />
            <circle cx="198" cy="76" r="29" className="art-center" />
            <circle cx="276" cy="30" r="15" />
            <circle cx="275" cy="124" r="11" />
            <path className="art-check" d="m187 76 8 8 15-17" />
          </svg>
        </div>
      </div>
      <div className="stat-grid">
        {stats.map((stat) => (
          <Link to={stat.to} className="stat-card" key={stat.title}>
            <div>
              <span>{stat.title}</span>
              <span className={`stat-icon ${stat.tone}`}>
                <stat.icon size={20} />
              </span>
            </div>
            <strong>{stat.error ? '—' : (stat.value ?? '…')}</strong>
            <p>
              {stat.error ? 'Chưa tải được dữ liệu' : stat.note}
              <ArrowRight size={14} />
            </p>
          </Link>
        ))}
      </div>
      {(employees.error || projects.error || skills.error) && (
        <ErrorNotice
          error={employees.error || projects.error || skills.error}
          retry={() => {
            void employees.refetch();
            void projects.refetch();
            void skills.refetch();
          }}
        />
      )}
      <div className="dashboard-grid">
        <section className="panel focus-panel">
          <SectionHeading
            title="Dự án trong tầm nhìn"
            detail="Nhận diện khoảng trống kỹ năng của đội ngũ."
            action={
              <span className="live-label">
                <i />
                Dữ liệu hiện tại
              </span>
            }
          />
          {projects.isPending ? (
            <Loading />
          ) : projects.error ? (
            <ErrorNotice error={projects.error} retry={() => void projects.refetch()} />
          ) : selectedProject ? (
            <>
              <div className="project-picker">
                <span className="project-mark">
                  <BriefcaseBusiness size={21} />
                </span>
                <label>
                  <small>DỰ ÁN ĐANG XEM</small>
                  <select
                    aria-label="Chọn dự án phân tích"
                    value={selectedProject.project_id}
                    onChange={(e) => {
                      setSelected(e.target.value);
                      setCandidate(null);
                    }}
                  >
                    {projects.data?.map((p) => (
                      <option value={p.project_id} key={p.project_id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
                <Link aria-label="Mở chi tiết dự án" to={`/projects/${selectedProject.project_id}`}>
                  <ArrowRight size={20} />
                </Link>
              </div>
              <SkillCoverage projectId={selectedProject.project_id} />
            </>
          ) : (
            <Empty
              title="Dự án đầu tiên bắt đầu từ đây"
              detail="Tạo dự án để kết nối kỹ năng với nhu cầu thực tế."
              action={<TextLink to="/projects">Tạo dự án</TextLink>}
            />
          )}
        </section>
        <section className="panel capacity-panel">
          <SectionHeading
            title="Nhịp làm việc của đội ngũ"
            detail="Tổng phân bổ trên tất cả dự án."
          />
          {employees.isPending || capacity.isPending ? (
            <Loading />
          ) : employees.error || capacity.error ? (
            <ErrorNotice error={employees.error || capacity.error} retry={capacity.retry} />
          ) : !freePeople.length ? (
            <Empty title="Chưa có nhân viên" />
          ) : (
            <>
              <div className="capacity-list">
                {freePeople.map((employee, index) => {
                  const used = capacity.totals.get(employee.employee_id) || 0;
                  return (
                    <Link
                      to={`/employees/${employee.employee_id}`}
                      className="capacity-person"
                      key={employee.employee_id}
                    >
                      <Avatar name={employee.name} index={index} />
                      <div>
                        <strong>{employee.name}</strong>
                        <small>{employee.title}</small>
                        <Meter value={used} label={`Phân bổ ${employee.name}`} />
                      </div>
                      <span className={used < 100 ? 'has-capacity' : ''}>{used}%</span>
                    </Link>
                  );
                })}
              </div>
              <div className="panel-foot">
                <TextLink to="/employees">Xem toàn bộ đội ngũ</TextLink>
              </div>
            </>
          )}
        </section>
      </div>
      {selectedProject && (
        <CandidateSuggestions
          projectId={selectedProject.project_id}
          onAssign={setCandidate}
          compact
        />
      )}
      {candidate && selectedProject && (
        <AssignmentDialog
          projectId={selectedProject.project_id}
          employeeId={candidate.employee_id}
          onClose={() => setCandidate(null)}
        />
      )}
    </>
  );
}
