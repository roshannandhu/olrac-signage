import { useQuery } from '@tanstack/react-query'
import { reportsApi } from '../api'
import type { ReportKind, ReportRange, ReportRow } from '../api'
import { qk } from './keys'

export function useReports(kind: ReportKind, range: ReportRange = {}) {
  return useQuery<ReportRow[]>({
    queryKey: qk.reports(kind, range),
    queryFn: () => reportsApi.get(kind, range),
  })
}

// Convenience re-export so pages can trigger the CSV download from the Export modal.
export const exportReportCsv = reportsApi.exportCsv
