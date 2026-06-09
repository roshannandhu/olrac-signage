import type { ContentFilters, ReportKind, ReportRange } from '../api'

// Centralised React Query keys so queries + their invalidations always match.
export const qk = {
  me: ['me'] as const,
  content: (filters: ContentFilters = {}) => ['content', filters] as const,
  screens: ['screens'] as const,
  playlist: (screenId: string) => ['playlist', screenId] as const,
  groups: ['groups'] as const,
  websites: ['websites'] as const,
  reports: (kind: ReportKind, range: ReportRange = {}) => ['reports', kind, range] as const,
}
