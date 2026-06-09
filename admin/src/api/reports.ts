import { client, unwrap } from './client'
import type { ByScreenRow, HourlyRow, SummaryRow } from './types'

export type ReportKind = 'summary' | 'by-screen' | 'hourly'
export interface ReportRange {
  from?: string
  to?: string
}
export type ReportRow = SummaryRow | ByScreenRow | HourlyRow

export const reportsApi = {
  get: (kind: ReportKind, range: ReportRange = {}) =>
    unwrap<ReportRow[]>(client.get(`/reports/${kind}`, { params: range })),

  // Triggers a CSV download in the browser. The token is attached by the axios
  // request interceptor; we stream the blob and click a temporary anchor.
  exportCsv: async (kind: ReportKind, range: ReportRange = {}) => {
    const resp = await client.get('/reports/export', {
      params: { type: kind, ...range },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(resp.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `olrac-report-${kind}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },
}
