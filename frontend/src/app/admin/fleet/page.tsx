'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, CheckCircle, MonitorPlay, RefreshCw, Rocket } from 'lucide-react'
import { adminApi } from '@/lib/api'
import type { FleetScreen } from '@/lib/types'
import { PageHeader, StatCard } from '@/components/admin/admin-ui'

/**
 * The whole fleet's version spread in one place.
 *
 * Per-tenant screen lists already show a single screen's version; this is the platform
 * operator's global view — which TVs are online, what build each is on, and how a rollout
 * is landing. Polls so a release can be watched propagating.
 */
export default function AdminFleetPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['admin', 'fleet'],
    queryFn: adminApi.getFleet,
    refetchInterval: 15000,
  })

  const versions = data ? Object.entries(data.versions).sort((a, b) => b[1] - a[1]) : []
  const latest = data?.latest_version_name ?? null

  return (
    <div className="space-y-6 p-6 text-foreground lg:p-8">
      <PageHeader title="Fleet Versions" description="Every TV across every tenant — the build it runs and its update state">
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['admin', 'fleet'] })}
          className="flex items-center gap-2 rounded-xl border border-border bg-muted px-4 py-2 text-sm text-muted-foreground transition-all hover:bg-muted"
        >
          <RefreshCw className={`size-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </PageHeader>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total TVs" value={data?.total ?? 0} icon={MonitorPlay} accent="violet" />
        <StatCard label="Online now" value={`${data?.online ?? 0} / ${data?.total ?? 0}`} icon={Activity} accent="emerald" />
        <StatCard
          label={latest ? `On latest (${latest})` : 'On latest'}
          value={data?.on_latest ?? 0}
          icon={CheckCircle}
          accent="cyan"
        />
        <StatCard label="Failed / rolled back" value={data?.failed ?? 0} icon={AlertTriangle} accent="amber" />
      </div>

      {/* Version spread */}
      <section className="rounded-2xl border border-border bg-card p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Rocket className="size-4 text-violet-400" />
          Version spread
          {latest && <span className="ml-2 text-xs font-normal text-muted-foreground">latest released: <span className="text-emerald-400">{latest}</span></span>}
          {data && data.updating > 0 && <span className="ml-auto text-xs font-normal text-amber-300">{data.updating} updating…</span>}
        </div>
        {versions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No paired TVs yet.</p>
        ) : (
          <div className="space-y-2">
            {versions.map(([version, count]) => {
              const pct = data && data.total ? Math.round((count / data.total) * 100) : 0
              const isLatest = latest !== null && version === latest
              return (
                <div key={version} className="flex items-center gap-3">
                  <span className={`w-28 shrink-0 truncate font-mono text-xs ${isLatest ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                    {version}{isLatest && ' ✓'}
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className={`h-full rounded-full ${isLatest ? 'bg-emerald-500' : 'bg-violet-500'}`} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="w-10 shrink-0 text-right text-xs text-muted-foreground">{count}</span>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* Per-TV table */}
      <section className="overflow-hidden rounded-2xl border border-border bg-card">
        <div className="flex items-center gap-2 border-b border-border p-4 text-sm font-semibold">
          <MonitorPlay className="size-4 text-violet-400" />
          {data?.screens.length ?? 0} TVs
        </div>
        {isLoading ? (
          <p className="p-10 text-center text-sm text-muted-foreground">Loading…</p>
        ) : !data?.screens.length ? (
          <p className="p-10 text-center text-sm text-muted-foreground">No TVs paired across the fleet yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-sm">
              <thead className="border-b border-border bg-muted text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="p-4 pl-5 text-left">TV</th>
                  <th className="p-4 text-left">Workspace</th>
                  <th className="p-4 text-left">Version</th>
                  <th className="p-4 text-left">Pin</th>
                  <th className="p-4 text-left">Update</th>
                  <th className="p-4 text-left">State</th>
                  <th className="p-4 pr-5 text-left">Last seen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.screens.map((s) => (
                  <tr key={s.id} className="transition-colors hover:bg-muted">
                    <td className="p-4 pl-5 font-medium">{s.name || `Screen ${s.id}`}</td>
                    <td className="p-4 text-xs text-muted-foreground">{s.organization_name}</td>
                    <td className="p-4">
                      <span className={`font-mono text-xs ${latest && s.app_version === latest ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                        {s.app_version || '—'}
                      </span>
                    </td>
                    <td className="p-4 text-xs text-muted-foreground">{s.target_version_code ?? '—'}</td>
                    <td className="p-4"><UpdateChip screen={s} /></td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1.5 text-xs ${s.online ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                        <span className={`size-1.5 rounded-full ${s.online ? 'bg-emerald-400' : 'bg-muted'}`} />
                        {s.online ? 'Online' : 'Offline'}
                      </span>
                    </td>
                    <td className="p-4 pr-5 text-xs text-muted-foreground">{s.last_seen ? new Date(s.last_seen).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

function UpdateChip({ screen }: { screen: FleetScreen }) {
  const s = screen.update_status
  if (s === 'failed' || s === 'rolled_back') {
    return <span className="rounded-full border border-rose-500/20 bg-rose-500/10 px-2 py-0.5 text-xs text-rose-400">{s === 'rolled_back' ? 'rolled back' : 'failed'}{screen.update_failure_count > 0 ? ` ×${screen.update_failure_count}` : ''}</span>
  }
  if (s === 'pending' || s === 'downloading' || s === 'installing') {
    return <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300">{s}…</span>
  }
  if (s === 'success') {
    return <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-400">up to date</span>
  }
  return <span className="text-xs text-muted-foreground">—</span>
}
