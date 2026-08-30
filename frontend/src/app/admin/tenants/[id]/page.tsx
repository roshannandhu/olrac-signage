'use client'

import { use, useState } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FileVideo, MonitorPlay, Users } from 'lucide-react'
import { adminApi } from '@/lib/api'
import {
  Feedback, PageHeader, QuotaBar, StatusPill, formatBytes,
} from '@/components/admin/admin-ui'

type Tab = 'screens' | 'content' | 'users'

/**
 * Read-only view of one tenant's workspace.
 *
 * Deliberately has no edit controls for their screens, media or team: an operator needs to
 * SEE what a workspace contains to support it, not to change it. Status and limits are
 * changed from the tenants list, which is where those actions belong.
 */
export default function AdminTenantDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const tenantId = Number(id)
  const [tab, setTab] = useState<Tab>('screens')

  const tenantQuery = useQuery({
    queryKey: ['admin', 'tenant', tenantId],
    queryFn: () => adminApi.getTenant(tenantId),
  })
  const screensQuery = useQuery({
    queryKey: ['admin', 'tenant', tenantId, 'screens'],
    queryFn: () => adminApi.getTenantScreens(tenantId),
    enabled: tab === 'screens',
  })
  const contentQuery = useQuery({
    queryKey: ['admin', 'tenant', tenantId, 'content'],
    queryFn: () => adminApi.getTenantContent(tenantId),
    enabled: tab === 'content',
  })
  const usersQuery = useQuery({
    queryKey: ['admin', 'tenant', tenantId, 'users'],
    queryFn: () => adminApi.getTenantUsers(tenantId),
    enabled: tab === 'users',
  })

  const tenant = tenantQuery.data

  return (
    <div className="space-y-6 p-6 text-white lg:p-8">
      <Link href="/admin/tenants" className="inline-flex items-center gap-2 text-xs text-white/40 hover:text-white/70">
        <ArrowLeft className="size-3.5" />
        All tenants
      </Link>

      <Feedback error={tenantQuery.error ? (tenantQuery.error as Error).message : undefined} />

      {tenantQuery.isLoading ? (
        <p className="text-sm text-white/40">Loading…</p>
      ) : !tenant ? (
        <p className="text-sm text-white/40">This workspace does not exist.</p>
      ) : (
        <>
          <PageHeader title={tenant.name} description={tenant.owner_email ?? 'No owner email on record'}>
            <StatusPill status={tenant.status} />
          </PageHeader>

          {tenant.rejection_reason && (
            <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-3 text-sm text-rose-300">
              Rejection reason: {tenant.rejection_reason}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
              <p className="mb-2 text-xs text-white/40">TV screens</p>
              <QuotaBar used={tenant.screens_count} max={tenant.max_screens} />
              <p className="mt-2 text-xs text-white/30">{tenant.online_screens_count} online now</p>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
              <p className="mb-2 text-xs text-white/40">Ad slots</p>
              <QuotaBar used={tenant.ad_slots_used} max={tenant.max_ad_slots} />
              <p className="mt-2 text-xs text-white/30">{tenant.plan_name ?? 'No package'}</p>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
              <p className="mb-2 text-xs text-white/40">Storage</p>
              <p className="text-sm font-semibold">
                {formatBytes(tenant.storage_used_bytes)}{' '}
                <span className="font-normal text-white/40">of {formatBytes(tenant.storage_quota_bytes)}</span>
              </p>
              <p className="mt-2 text-xs text-white/30">
                Joined {tenant.created_at ? new Date(tenant.created_at).toLocaleDateString() : '—'}
              </p>
            </div>
          </div>

          <div className="flex gap-1 border-b border-white/5">
            {([
              ['screens', 'Screens', MonitorPlay],
              ['content', 'Content', FileVideo],
              ['users', 'Team', Users],
            ] as const).map(([key, label, Icon]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm transition-all ${
                  tab === key
                    ? 'border-violet-500 font-semibold text-violet-300'
                    : 'border-transparent text-white/40 hover:text-white/70'
                }`}
              >
                <Icon className="size-4" />
                {label}
              </button>
            ))}
          </div>

          <section className="overflow-hidden rounded-2xl border border-white/8 bg-[#0a0f1e]">
            {tab === 'screens' && (
              <Table
                loading={screensQuery.isLoading}
                empty="This workspace has no screens yet."
                headers={['Name', 'Status', 'Playback', 'Location', 'Model', 'App', 'Last seen']}
                rows={(screensQuery.data ?? []).map((s) => [
                  s.name ?? `Screen ${s.id}`,
                  <StatusPill key="s" status={s.status === 'online' ? 'active' : 'suspended'} />,
                  s.playback_state,
                  s.location ?? '—',
                  s.model ?? '—',
                  s.app_version ?? '—',
                  s.last_seen ? new Date(s.last_seen).toLocaleString() : '—',
                ])}
              />
            )}
            {tab === 'content' && (
              <Table
                loading={contentQuery.isLoading}
                empty="No media uploaded."
                headers={['Name', 'Type', 'Status', 'Size', 'Uploaded']}
                rows={(contentQuery.data ?? []).map((c) => [
                  c.name ?? `Asset ${c.id}`,
                  c.type ?? '—',
                  c.status,
                  formatBytes(c.file_size_bytes),
                  c.uploaded_at ? new Date(c.uploaded_at).toLocaleDateString() : '—',
                ])}
              />
            )}
            {tab === 'users' && (
              <Table
                loading={usersQuery.isLoading}
                empty="No users."
                headers={['Name', 'Email', 'Role', 'Active', 'Super Admin Action']}
                rows={(usersQuery.data ?? []).map((u) => [
                  u.full_name ?? u.username,
                  u.email ?? '—',
                  <span
                    key={`role-${u.id}`}
                    className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${
                      u.role === 'super_admin'
                        ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                        : 'bg-white/5 text-white/70'
                    }`}
                  >
                    {u.role}
                  </span>,
                  u.is_active ? 'Yes' : 'No',
                  <button
                    key={`action-${u.id}`}
                    onClick={async () => {
                      const newRole = u.role === 'super_admin' ? 'owner' : 'super_admin'
                      const confirmed = window.confirm(
                        u.role === 'super_admin'
                          ? `Demote ${u.username} from Super Admin to Owner?`
                          : `Hire/Promote ${u.username} to Platform Super Admin?`
                      )
                      if (!confirmed) return
                      try {
                        await adminApi.updateUserRole(u.id, newRole)
                        usersQuery.refetch()
                      } catch (err) {
                        alert(err instanceof Error ? err.message : 'Failed to update role')
                      }
                    }}
                    className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                      u.role === 'super_admin'
                        ? 'bg-rose-500/15 text-rose-300 hover:bg-rose-500/25 border border-rose-500/20'
                        : 'bg-violet-500/15 text-violet-300 hover:bg-violet-500/25 border border-violet-500/20'
                    }`}
                  >
                    {u.role === 'super_admin' ? 'Demote to Owner' : 'Promote to Super Admin'}
                  </button>,
                ])}
              />
            )}
          </section>
        </>
      )}
    </div>
  )
}

function Table({
  loading, empty, headers, rows,
}: { loading: boolean; empty: string; headers: string[]; rows: React.ReactNode[][] }) {
  if (loading) return <p className="p-10 text-center text-sm text-white/40">Loading…</p>
  if (rows.length === 0) return <p className="p-10 text-center text-sm text-white/40">{empty}</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-white/5 bg-white/[0.02] text-xs uppercase tracking-wider text-white/30">
          <tr>
            {headers.map((h) => <th key={h} className="p-4 text-left first:pl-5">{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.04]">
          {rows.map((cells, i) => (
            <tr key={i} className="transition-colors hover:bg-white/[0.02]">
              {cells.map((cell, j) => (
                <td key={j} className="p-4 first:pl-5 first:font-medium first:text-white">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
