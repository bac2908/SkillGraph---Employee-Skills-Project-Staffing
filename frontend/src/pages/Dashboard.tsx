import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight,
  BriefcaseBusiness,
  ChevronDown,
  Layers3,
  RefreshCw,
  Sparkles,
  Users,
  UserRoundCheck,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useResource } from '../api';
import type { Candidate, DashboardOverview, Project } from '../types';
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
import { ProjectPicker } from '../components/ProjectPicker';

export function Dashboard() {
  const overview = useResource<DashboardOverview>('/api/dashboard');
  const client = useQueryClient();
  const [selected, setSelected] = useState<Project | null>(null);
  const [picking, setPicking] = useState(false);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const selectedProject = selected || overview.data?.default_project;
  const summary = overview.data?.summary;
  const stats = [
    {
      title: 'Nhân viên',
      value: summary?.employee_count,
      icon: Users,
      note: 'Những tài năng trong tổ chức',
      to: '/employees',
      tone: 'green',
    },
    {
      title: 'Trạng thái sẵn sàng',
      value: summary?.available_employee_count,
      icon: UserRoundCheck,
      note: 'Không đồng nghĩa còn dung lượng',
      to: '/employees',
      tone: 'mint',
    },
    {
      title: 'Dự án đang chạy',
      value: summary?.active_project_count,
      icon: BriefcaseBusiness,
      note: `${summary?.project_count ?? '…'} dự án trong không gian`,
      to: '/projects',
      tone: 'amber',
    },
    {
      title: 'Kỹ năng',
      value: summary?.skill_count,
      icon: Layers3,
      note: 'Nền tảng năng lực chung',
      to: '/skills',
      tone: 'blue',
    },
  ];
  const freePeople = overview.data?.capacity || [];
  return (
    <>
      <PageHeading
        eyebrow="TỔNG QUAN KHÔNG GIAN"
        title="Đúng người. Đúng cơ hội."
        description="Một góc nhìn rõ ràng để xây dựng những đội ngũ tốt hơn."
        action={
          <div className="dashboard-actions">
            <button
              type="button"
              className="button secondary"
              disabled={overview.isFetching}
              onClick={() => void client.invalidateQueries({ queryKey: ['api'] })}
            >
              <RefreshCw size={16} className={overview.isFetching ? 'spin' : ''} />
              Làm mới
            </button>
            <Link className="button primary" to="/projects">
              Khám phá dự án
              <ArrowRight size={17} />
            </Link>
          </div>
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
            <strong>{overview.error ? '—' : (stat.value ?? '…')}</strong>
            <p>
              {overview.error ? 'Chưa tải được dữ liệu' : stat.note}
              <ArrowRight size={14} />
            </p>
          </Link>
        ))}
      </div>
      {overview.error && (
        <ErrorNotice error={overview.error} retry={() => void overview.refetch()} />
      )}
      <div className="dashboard-grid">
        <section className="panel focus-panel">
          <SectionHeading
            title="Dự án trong tầm nhìn"
            detail="Nhận diện khoảng trống kỹ năng của đội ngũ."
            action={
              overview.data &&
              !overview.isError && (
                <span className="live-label">
                  Đã tải {new Date(overview.data.generated_at).toLocaleTimeString('vi-VN')}
                </span>
              )
            }
          />
          {overview.isPending ? (
            <Loading />
          ) : overview.error ? (
            <p className="dashboard-unavailable">Phân tích sẽ hiển thị khi tải lại thành công.</p>
          ) : selectedProject ? (
            <>
              <div className="project-picker">
                <span className="project-mark">
                  <BriefcaseBusiness size={21} />
                </span>
                <div className="project-picker-selection">
                  <small>DỰ ÁN ĐANG XEM</small>
                  <button
                    type="button"
                    className="project-picker-trigger"
                    aria-label="Chọn dự án phân tích"
                    aria-haspopup="dialog"
                    onClick={() => setPicking(true)}
                  >
                    <span>{selectedProject.name}</span>
                    <ChevronDown size={16} />
                  </button>
                </div>
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
            detail="Tối đa 5 người có mức phân bổ thấp nhất. Số % là phần đã phân bổ trên tất cả dự án, không phải phần còn trống."
          />
          {overview.isPending ? (
            <Loading />
          ) : overview.error ? (
            <p className="dashboard-unavailable">Chưa có số liệu phân bổ đáng tin cậy.</p>
          ) : !freePeople.length ? (
            <Empty title="Chưa có nhân viên" />
          ) : (
            <>
              <div className="capacity-list">
                {freePeople.map((employee, index) => {
                  const used = employee.total_allocation;
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
                        <Meter
                          value={Math.min(100, used)}
                          label={`Phân bổ ${employee.name}: ${used}%`}
                        />
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
      {selectedProject && !overview.isError && (
        <CandidateSuggestions
          projectId={selectedProject.project_id}
          onAssign={setCandidate}
          compact
        />
      )}
      {picking && selectedProject && (
        <ProjectPicker
          selectedId={selectedProject.project_id}
          onSelect={(project) => {
            setSelected(project);
            setCandidate(null);
          }}
          onClose={() => setPicking(false)}
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
