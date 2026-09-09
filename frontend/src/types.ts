export interface Employee {
  employee_id: string;
  name: string;
  email: string;
  title: string;
  seniority: string;
  status: string;
  location: string;
}
export interface Skill {
  skill_id: string;
  name: string;
  category: string;
}
export interface Project {
  project_id: string;
  name: string;
  description: string;
  status: string;
}
export interface ActivityEvent {
  event_id: string;
  occurred_at: string;
  actor_id: string;
  actor_name: string;
  project_id: string;
  action: 'CREATED' | 'UPDATED' | 'DELETED';
  resource_type: 'PROJECT' | 'WORKS_ON' | 'REQUIRES_SKILL';
  resource_id: string;
  before: Record<string, string | number | null> | null;
  after: Record<string, string | number | null> | null;
}
export interface ActivityPage {
  items: ActivityEvent[];
  next_cursor: string | null;
}
export interface DashboardOverview {
  generated_at: string;
  summary: {
    employee_count: number;
    available_employee_count: number;
    project_count: number;
    active_project_count: number;
    skill_count: number;
  };
  capacity: {
    employee_id: string;
    name: string;
    title: string;
    total_allocation: number;
    remaining_allocation: number;
  }[];
  default_project: Project | null;
}
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
export interface Items<T> {
  items: T[];
  total: number;
}
export interface EmployeeSkill {
  employee_id: string;
  employee_name: string;
  skill_id: string;
  skill_name: string;
  category: string;
  level: number;
  years_experience: number;
}
export interface Assignment {
  project_id: string;
  project_name: string;
  employee_id: string;
  employee_name: string;
  role: string;
  allocation: number;
  employee_total_allocation: number;
  employee_remaining_allocation: number;
}
export interface Requirement {
  project_id: string;
  project_name: string;
  skill_id: string;
  skill_name: string;
  category: string;
  min_level: number;
  priority: string;
}
export interface GapSkill {
  skill_id: string;
  skill: string;
  required_level: number;
  best_team_level: number;
  employee_count: number;
  priority: string;
  status: 'COVERED' | 'GAP' | 'MISSING';
}
export interface Gap {
  project_id: string;
  summary: {
    total: number;
    covered: number;
    gap: number;
    missing: number;
    coverage_percent: number;
  };
  skills: GapSkill[];
}
export interface Candidate extends Employee {
  matched_skills: { skill_id: string; skill: string; level: number; required_level: number }[];
  matched_skill_count: number;
  collaboration_count: number;
  collaborators: string[];
  shared_projects: string[];
  rank: number;
}
export interface Recommendations {
  project_id: string;
  summary: { uncovered_skill_count: number; candidate_count: number };
  uncovered_skills: GapSkill[];
  candidates: Candidate[];
}
