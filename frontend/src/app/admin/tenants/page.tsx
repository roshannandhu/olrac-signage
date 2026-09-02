'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle, Clock, Film, Gauge, MonitorPlay, RefreshCw, Users, XCircle,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import type { TenantSummary } from '@/lib/types'
import {
  Feedback, PageHeader, QuotaBar, StatCard, StatusPill, formatBytes,
} from '@/components/admin/admin-ui'

/**
 * Every workspace, with the controls to police it.
 *
 * Two things this page previously got wrong, both now handled by going through adminApi:
 * it called the API with a bare fetch() and a hand-built auth header (so an expired
 * session showed an empty table rather than redirecting to login), and its stat cards
 * built Tailwind classes by interpolation (`bg-${color}-500/10`), which Tailwind v4 cannot
 * see -- so none of them were styled.
 */
export default function AdminTenantsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [quotaFor, setQuotaFor] = useState<TenantSummary | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const { data: tenants = [], isLoading, isFetching } = useQuery({
    queryKey: ['admin', 'tenants'],
    queryFn: () => adminApi.listTenants(),
  })
  const { data: packages = [] } = useQuery({ queryKey: ['admin', 'packages'], queryFn: adminApi.listPackages })

  const done = (text: string) => {
    setError('')
    setMessage(text)
    queryClient.invalidateQueries({ queryKey: ['admin', 'tenants'] })
  }
  const failed = (e: Error) => { setMessage(''); setError(e.message) }

  const setStatus = useMutation({
    mutationFn: ({ id, action }: { id: number; action: 'suspend' | 'reinstate' }) =>
      action === 'suspend' ? adminApi.suspendTenant(id) : adminApi.reinstateTenant(id),
    onSuccess: (tenant) => done(`${tenant.name} is now ${tenant.status}.`),
    onError: failed,
  })

  const saveQuota = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { plan_id?: number; max_screens: number; max_ad_slots: number } }) =>
      adminApi.updateQuota(id, body),
    onSuccess: (tenant) => { setQuotaFor(null); done(`Limits updated for ${tenant.name}.`) },
    onError: failed,
  })

  const filtered = tenants.filter((t) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return [t.name, t.slug, t.owner_email ?? ''].some((v) => v.toLowerCase().includes(q))
  })

  const totals = {
    active: tenants.filter((t) => t.status === 'active').length,
    pending: tenants.filter((t) => t.status === 'pending_approval').length,
    screens: tenants.reduce((s, t) => s + t.screens_count, 0),
    online: tenants.reduce((s, t) => s + t.online_screens_count, 0),
    ads: tenants.reduce((s, t) => s + t.ad_slots_used, 0),
  }

  return (
    <div className="space-y-6 p-6 text-white lg:p-8">
      <PageHeader title="All Tenants" description="Limits, status and usage for every workspace">
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['admin', 'tenants'] })}
          className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/70 transition-all hover:bg-white/10"
        >
          <RefreshCw className={`size-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </PageHeader>

      <Feedback ok={message} error={error} />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Active workspaces" value={totals.active} icon={CheckCircle} accent="emerald" />
        <StatCard label="Pending approvals" value={totals.pending} icon={Clock} accent="amber" />
        <StatCard label="TVs online (of paired)" value={`${totals.online} / ${totals.screens}`} icon={MonitorPlay} accent="violet" />
        <StatCard label="Active ad placements" value={totals.ads} icon={Film} accent="cyan" />
      </div>

      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search by workspace, slug or owner email…"
        className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder:text-white/30 outline-none focus:border-violet-500/50"
      />

      <section className="overflow-hidden rounded-2xl border border-white/8 bg-[#0a0f1e]">
        <div className="flex items-center gap-2 border-b border-white/5 p-4 text-sm font-semibold">
          <Users className="size-4 text-violet-400" />
          {filtered.length} of {tenants.length} tenants
        </div>

        {isLoading ? (
          <p className="p-10 text-center text-sm text-white/40">Loading…</p>
        ) : (
          <div className="overflow-x-auto">
            {/* min-w keeps the eight columns readable and lets the wrapper scroll, rather
                than squeezing them into 375px until every cell wraps to three lines. */}
            <table className="w-full min-w-[880px] text-sm">
              <thead className="border-b border-white/5 bg-white/[0.02] text-xs uppercase tracking-wider text-white/30">
                <tr>
                  <th className="p-4 pl-5 text-left">Workspace</th>
                  <th className="p-4 text-left">Owner</th>
                  <th className="p-4 text-left">Package</th>
                  <th className="p-4 text-left">Status</th>
                  <th className="p-4 text-left">Screens</th>
                  <th className="p-4 text-left">Ad slots</th>
                  <th className="p-4 text-left">Storage</th>
                  <th className="p-4 pr-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {filtered.map((tenant) => (
                  <tr key={tenant.id} className="transition-colors hover:bg-white/[0.02]">
                    <td className="p-4 pl-5">
                      <Link href={`/admin/tenants/${tenant.id}`} className="font-semibold text-white hover:underline">
                        {tenant.name}
                      </Link>
                      <p className="font-mono text-xs text-white/30">{tenant.slug}</p>
                    </td>
                    <td className="p-4 font-mono text-xs text-emerald-400">{tenant.owner_email ?? '—'}</td>
                    <td className="p-4 text-xs text-white/60">{tenant.plan_name ?? '—'}</td>
                    <td className="p-4"><StatusPill status={tenant.status} /></td>
                    <td className="w-32 p-4"><QuotaBar used={tenant.screens_count} max={tenant.max_screens} /></td>
                    <td className="w-32 p-4"><QuotaBar used={tenant.ad_slots_used} max={tenant.max_ad_slots} /></td>
                    <td className="p-4 text-xs text-white/50">
                      {formatBytes(tenant.storage_used_bytes)} / {formatBytes(tenant.storage_quota_bytes)}
                    </td>
                    <td className="p-4 pr-5">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => { setQuotaFor(tenant); setMessage(''); setError('') }}
                          className="flex items-center gap-1.5 rounded-lg border border-violet-500/20 bg-violet-500/10 px-3 py-1.5 text-xs text-violet-400 transition-all hover:bg-violet-500/20"
                        >
                          <Gauge className="size-3" />
                          Limits
                        </button>
                        {tenant.status === 'suspended' ? (
                          <button
                            onClick={() => setStatus.mutate({ id: tenant.id, action: 'reinstate' })}
                            className="flex items-center gap-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-400 transition-all hover:bg-emerald-500/20"
                          >
                            <CheckCircle className="size-3" />
                            Reinstate
                          </button>
                        ) : (
                          <button
                            onClick={() => {
                              if (window.confirm(`Block "${tenant.name}"? Their dashboard and API access stop immediately.`)) {
                                setStatus.mutate({ id: tenant.id, action: 'suspend' })
                              }
                            }}
                            className="flex items-center gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-400 transition-all hover:bg-rose-500/20"
                          >
                            <XCircle className="size-3" />
                            Block
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {quotaFor && (
        <QuotaDialog
          tenant={quotaFor}
          packages={packages}
          saving={saveQuota.isPending}
          onCancel={() => setQuotaFor(null)}
          onSave={(body) => saveQuota.mutate({ id: quotaFor.id, body })}
        />
      )}
    </div>
  )
}

function QuotaDialog({
  tenant, packages, saving, onCancel, onSave,
}: {
  tenant: TenantSummary
  packages: { id: number; name: string; max_screens: number; max_ad_slots: number; is_active: boolean }[]
  saving: boolean
  onCancel: () => void
  onSave: (body: { plan_id?: number; max_screens: number; max_ad_slots: number }) => void
}) {
  const [planId, setPlanId] = useState<number | ''>(tenant.plan_id ?? '')
  const [screens, setScreens] = useState(tenant.max_screens)
  const [ads, setAds] = useState(tenant.max_ad_slots)

  // Picking a package pre-fills its limits, but they stay editable: the override is the
  // point, so one tenant can be raised without moving everyone on that package.
  const choosePackage = (value: number | '') => {
    setPlanId(value)
    const pkg = packages.find((p) => p.id === value)
    if (pkg) { setScreens(pkg.max_screens); setAds(pkg.max_ad_slots) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm" onClick={onCancel}>
      <div className="w-full max-w-md space-y-5 rounded-3xl border border-white/10 bg-[#0a0f1e] p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-2xl border border-violet-500/20 bg-violet-500/10">
            <Gauge className="size-5 text-violet-400" />
          </div>
          <div>
            <h2 className="font-bold text-white">Edit limits</h2>
            <p className="text-xs text-white/50">{tenant.name}</p>
          </div>
        </div>

        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold text-white/60">Package</span>
          <select
            value={planId}
            onChange={(e) => choosePackage(e.target.value === '' ? '' : Number(e.target.value))}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none focus:border-violet-500/50"
          >
            <option value="">No package</option>
            {packages.filter((p) => p.is_active || p.id === tenant.plan_id).map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold text-white/60">
            Max TV screens <span className="font-normal text-white/30">(0 = unlimited)</span>
          </span>
          <input
            type="number" min={0} value={screens} onChange={(e) => setScreens(Number(e.target.value) || 0)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none focus:border-violet-500/50"
          />
          <p className="mt-1 text-xs text-white/30">Currently using {tenant.screens_count}.</p>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold text-white/60">
            Max ad slots <span className="font-normal text-white/30">(0 = unlimited)</span>
          </span>
          <input
            type="number" min={0} value={ads} onChange={(e) => setAds(Number(e.target.value) || 0)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none focus:border-cyan-500/50"
          />
          <p className="mt-1 text-xs text-white/30">Currently using {tenant.ad_slots_used}.</p>
        </label>

        <div className="flex gap-3 pt-1">
          <button
            onClick={() => onSave({ ...(planId === '' ? {} : { plan_id: planId }), max_screens: screens, max_ad_slots: ads })}
            disabled={saving}
            className="flex-1 rounded-xl bg-violet-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save limits'}
          </button>
          <button onClick={onCancel} className="rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm text-white/70 transition-all hover:bg-white/10">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
