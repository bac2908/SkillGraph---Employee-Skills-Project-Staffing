import { ArrowUpRight, CheckCheck, CircleDot, Sparkles, Users } from 'lucide-react';
import { useResource } from '../api';
import type { Candidate, Gap, Recommendations } from '../types';
import { Avatar, Badge, Empty, ErrorNotice, Loading, SectionHeading } from './ui';

export function SkillCoverage({ projectId }: { projectId: string }) {
  const query = useResource<Gap>(`/api/projects/${projectId}/skill-gap`);
  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorNotice error={query.error} retry={() => void query.refetch()} />;
  const gap = query.data;
  if (!gap.skills.length) return <Empty title="Chưa có yêu cầu kỹ năng" detail="Thêm kỹ năng dự án cần để bắt đầu phân tích mức độ đáp ứng." />;
  return <div className="coverage-content"><div className="coverage-summary"><div className="coverage-number">{gap.summary.coverage_percent}<span>%</span></div><div><strong>Kỹ năng được đáp ứng</strong><p>{gap.summary.covered} / {gap.summary.total} kỹ năng đạt yêu cầu</p></div><span className={`coverage-alert ${gap.summary.covered === gap.summary.total ? 'complete' : ''}`}>{gap.summary.covered === gap.summary.total ? <CheckCheck size={16} /> : <CircleDot size={16} />}{gap.summary.gap + gap.summary.missing} kỹ năng cần bổ sung</span></div>
    <div className="skill-bars">{gap.skills.map(skill => <div className="skill-bar-row" key={skill.skill_id}><div><strong>{skill.skill}</strong><span>{skill.best_team_level} / {skill.required_level}</span></div><div className="level-track" aria-label={`${skill.skill}: đội ngũ cấp ${skill.best_team_level}, yêu cầu cấp ${skill.required_level}`}><span className={skill.status === 'COVERED' ? '' : 'gap-fill'} style={{ width: `${Math.min(100, skill.best_team_level / 5 * 100)}%` }} /><i style={{ left: `${skill.required_level / 5 * 100}%` }} /></div><Badge value={skill.status} /></div>)}</div>
    <div className="chart-legend"><span><i />Năng lực đội ngũ</span><span><i className="legend-required" />Mức yêu cầu · thang 1–5</span></div>
  </div>;
}

export function CandidateSuggestions({ projectId, onAssign, compact = false }: { projectId: string; onAssign: (candidate: Candidate) => void; compact?: boolean }) {
  const query = useResource<Recommendations>(`/api/projects/${projectId}/recommendations`);
  return <section className="panel recommendations"><SectionHeading title="Những mảnh ghép phù hợp" detail="Gợi ý theo kỹ năng còn thiếu và kinh nghiệm cộng tác." action={<span className="subtle-label"><Sparkles size={16} />Gợi ý từ SkillGraph</span>} />
    {query.isPending ? <Loading /> : query.isError ? <ErrorNotice error={query.error} retry={() => void query.refetch()} /> : !query.data.candidates.length ? <Empty title={query.data.summary.uncovered_skill_count ? 'Chưa có ứng viên phù hợp' : 'Đội ngũ đã đáp ứng kỹ năng'} detail={query.data.summary.uncovered_skill_count ? 'Cập nhật năng lực hoặc trạng thái sẵn sàng của nhân viên để tìm thêm lựa chọn.' : 'Bạn có thể tiếp tục quản lý yêu cầu và phân công tại dự án.'} /> : <div className={`candidate-grid ${compact ? 'compact' : ''}`}>{query.data.candidates.map((candidate, index) => <article className="candidate-card" key={candidate.employee_id}>
      <div className="candidate-heading"><Avatar name={candidate.name} index={index} /><span className="rank">#{candidate.rank} phù hợp</span></div><h3>{candidate.name}</h3><p>{candidate.title} · {candidate.seniority}</p><div className="chips">{candidate.matched_skills.map(skill => <span className="chip" key={skill.skill_id}>{skill.skill} <b>{skill.level}/5</b></span>)}</div><div className="collaboration"><Users size={15} /><span>{candidate.collaboration_count ? `Đã làm cùng ${candidate.collaborators.join(', ')}` : 'Cơ hội kết nối mới trong đội ngũ'}</span></div><button className="button secondary" onClick={() => onAssign(candidate)}>Xem & phân công<ArrowUpRight size={16} /></button>
    </article>)}</div>}
  </section>;
}
