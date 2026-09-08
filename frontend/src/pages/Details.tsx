import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { BriefcaseBusiness, Mail, MapPin } from 'lucide-react';
import { useResource } from '../api';
import type { Candidate, Employee, Project } from '../types';
import {
  Avatar,
  BackLink,
  Badge,
  ErrorNotice,
  Loading,
  PageHeading,
  SectionHeading,
} from '../components/ui';
import { Assignments, AssignmentDialog, SkillRelations } from '../components/Relations';
import { CandidateSuggestions, SkillCoverage } from '../components/Analysis';
import { useCapacity } from '../hooks';

const projectTabs = [
  ['analysis', 'Phân tích & gợi ý'],
  ['assignments', 'Đội ngũ'],
  ['requirements', 'Yêu cầu kỹ năng'],
] as const;

export function EmployeeDetail() {
  const { id } = useParams();
  const query = useResource<Employee>(`/api/employees/${encodeURIComponent(id || '')}`);
  const capacity = useCapacity();
  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorNotice error={query.error} retry={() => void query.refetch()} />;
  const employee = query.data;
  return (
    <>
      <BackLink to="/employees">Danh sách nhân viên</BackLink>
      <div className="profile-heading">
        <Avatar name={employee.name} />
        <div>
          <span className="eyebrow">
            {employee.employee_id} · {employee.seniority}
          </span>
          <h1>{employee.name}</h1>
          <p>{employee.title}</p>
        </div>
        <Badge value={employee.status} />
      </div>
      <div className="profile-meta">
        <span>
          <Mail size={17} />
          {employee.email}
        </span>
        <span>
          <MapPin size={17} />
          {employee.location}
        </span>
        <span>
          <BriefcaseBusiness size={17} />
          {capacity.isPending
            ? 'Đang tính phân bổ…'
            : capacity.error
              ? 'Chưa tải được phân bổ'
              : `${capacity.totals.get(employee.employee_id) || 0}% đã phân bổ`}
        </span>
      </div>
      {capacity.error && <ErrorNotice error={capacity.error} retry={capacity.retry} />}
      <SkillRelations ownerId={employee.employee_id} kind="employee" />
    </>
  );
}

export function ProjectDetail() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const query = useResource<Project>(`/api/projects/${encodeURIComponent(id || '')}`);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const selectedTab = ['analysis', 'assignments', 'requirements'].includes(params.get('tab') || '')
    ? params.get('tab')!
    : 'analysis';
  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorNotice error={query.error} retry={() => void query.refetch()} />;
  const project = query.data;
  return (
    <>
      <BackLink to="/projects">Danh sách dự án</BackLink>
      <PageHeading
        eyebrow={project.project_id}
        title={project.name}
        description={project.description}
        action={<Badge value={project.status} />}
      />
      <div className="tabs" role="tablist" aria-label="Nội dung dự án">
        {projectTabs.map(([value, title], index) => (
          <button
            key={value}
            id={`project-tab-${value}`}
            role="tab"
            aria-selected={selectedTab === value}
            aria-controls="project-tabpanel"
            tabIndex={selectedTab === value ? 0 : -1}
            onClick={() => setParams({ tab: value })}
            onKeyDown={(event) => {
              const next =
                event.key === 'ArrowRight'
                  ? (index + 1) % projectTabs.length
                  : event.key === 'ArrowLeft'
                    ? (index + projectTabs.length - 1) % projectTabs.length
                    : event.key === 'Home'
                      ? 0
                      : event.key === 'End'
                        ? projectTabs.length - 1
                        : null;
              if (next === null) return;
              event.preventDefault();
              setParams({ tab: projectTabs[next][0] });
              document.getElementById(`project-tab-${projectTabs[next][0]}`)?.focus();
            }}
          >
            {title}
          </button>
        ))}
      </div>
      <div
        id="project-tabpanel"
        role="tabpanel"
        aria-labelledby={`project-tab-${selectedTab}`}
        tabIndex={0}
      >
        {selectedTab === 'analysis' && (
          <>
            <section className="panel analysis-panel">
              <SectionHeading
                title="Mức độ đáp ứng kỹ năng"
                detail="Đối chiếu yêu cầu dự án với năng lực tốt nhất trong đội ngũ."
                action={
                  <Link className="text-link" to={`?tab=requirements`}>
                    Quản lý yêu cầu →
                  </Link>
                }
              />
              <SkillCoverage projectId={project.project_id} />
            </section>
            <CandidateSuggestions projectId={project.project_id} onAssign={setCandidate} />
          </>
        )}
        {selectedTab === 'assignments' && <Assignments projectId={project.project_id} />}
        {selectedTab === 'requirements' && (
          <SkillRelations ownerId={project.project_id} kind="project" />
        )}
      </div>
      {candidate && (
        <AssignmentDialog
          projectId={project.project_id}
          employeeId={candidate.employee_id}
          onClose={() => setCandidate(null)}
        />
      )}
    </>
  );
}
