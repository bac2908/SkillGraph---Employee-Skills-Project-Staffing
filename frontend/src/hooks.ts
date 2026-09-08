import { useQueries } from '@tanstack/react-query';
import { request, useAll } from './api';
import type { Assignment, Items, Project } from './types';

export function useCapacity() {
  const projects = useAll<Project>('projects');
  const assignments = useQueries({
    queries: (projects.data || []).map((project) => ({
      queryKey: ['api', `/api/projects/${project.project_id}/assignments`],
      queryFn: ({ signal }: { signal: AbortSignal }) =>
        request<Items<Assignment>>(`/api/projects/${project.project_id}/assignments`, { signal }),
    })),
  });
  const totals = new Map<string, number>();
  for (const query of assignments)
    for (const item of query.data?.items || [])
      totals.set(item.employee_id, (totals.get(item.employee_id) || 0) + item.allocation);
  return {
    totals,
    isPending: projects.isPending || assignments.some((q) => q.isPending),
    error: projects.error || assignments.find((q) => q.error)?.error,
    retry: () => {
      void projects.refetch();
      assignments.forEach((q) => void q.refetch());
    },
  };
}
