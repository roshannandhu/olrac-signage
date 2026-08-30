'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Package as PackageIcon, Plus, Save, Trash2 } from 'lucide-react'
import { adminApi } from '@/lib/api'
import type { Package, PackageWrite } from '@/lib/types'
import { Feedback, PageHeader, formatBytes, formatPaise } from '@/components/admin/admin-ui'

const GIB = 1024 ** 3

const blank: PackageWrite = {
  name: '',
  slug: '',
  monthly_price_paise: 0,
  yearly_price_paise: 0,
  max_screens: 10,
  max_storage_bytes: 10 * GIB,
  max_ad_slots: 20,
  is_active: true,
}

/**
 * Packages: the named limits a workspace is approved onto.
 *
 * The Plan table has existed since billing was added, with exactly one way to change it --
 * editing a hardcoded tuple in backend/billing.py, which `ensure_billing_catalog` then
 * skips for any slug that already exists. So prices and quotas could not be changed on a
 * live database at all without direct SQL. This is the missing admin surface.
 */
export default function AdminPackagesPage() {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<PackageWrite | null>(null)
  const [editing, setEditing] = useState<Record<number, Partial<PackageWrite>>>({})
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const { data: packages = [], isLoading } = useQuery({
    queryKey: ['admin', 'packages'],
    queryFn: adminApi.listPackages,
  })

  const done = (text: string) => {
    setError('')
    setMessage(text)
    queryClient.invalidateQueries({ queryKey: ['admin', 'packages'] })
  }
  const failed = (e: Error) => { setMessage(''); setError(e.message) }

  const create = useMutation({
    mutationFn: (body: PackageWrite) => adminApi.createPackage(body),
    onSuccess: (pkg) => { setDraft(null); done(`Package "${pkg.name}" created.`) },
    onError: failed,
  })

  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<PackageWrite> }) => adminApi.updatePackage(id, body),
    onSuccess: (pkg) => {
      setEditing((prev) => { const next = { ...prev }; delete next[pkg.id]; return next })
      done(`Package "${pkg.name}" updated.`)
    },
    onError: failed,
  })

  const remove = useMutation({
    mutationFn: (id: number) => adminApi.deletePackage(id),
    onSuccess: (res) => done(res.detail ?? 'Package deleted.'),
    onError: failed,
  })

  const fieldOf = (pkg: Package, key: keyof PackageWrite) =>
    (editing[pkg.id]?.[key] ?? pkg[key as keyof Package]) as never

  const edit = (id: number, key: keyof PackageWrite, value: string | number | boolean) =>
    setEditing((prev) => ({ ...prev, [id]: { ...prev[id], [key]: value } }))

  return (
    <div className="space-y-6 p-6 text-white lg:p-8">
      <PageHeader title="Packages" description="Screen, storage and ad-slot limits a workspace can be approved onto">
        <button
          onClick={() => setDraft(draft ? null : blank)}
          className="flex items-center gap-2 rounded-xl border border-violet-500/20 bg-violet-500/10 px-4 py-2 text-sm text-violet-300 transition-all hover:bg-violet-500/20"
        >
          <Plus className="size-4" />
          {draft ? 'Cancel' : 'New package'}
        </button>
      </PageHeader>

      <Feedback ok={message} error={error} />

      {draft && (
        <form
          onSubmit={(e) => { e.preventDefault(); create.mutate(draft) }}
          className="space-y-4 rounded-2xl border border-violet-500/20 bg-violet-500/[0.03] p-5"
        >
          <h2 className="font-semibold">New package</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Name">
              <input required value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className={inputClass} />
            </Field>
            <Field label="Slug" hint="lowercase, cannot change later">
              <input
                required pattern="[a-z0-9][a-z0-9-]*" value={draft.slug}
                onChange={(e) => setDraft({ ...draft, slug: e.target.value.toLowerCase() })}
                className={`${inputClass} font-mono`}
              />
            </Field>
            <Field label="Monthly price (₹)">
              <input
                type="number" min={0} value={draft.monthly_price_paise / 100}
                onChange={(e) => setDraft({ ...draft, monthly_price_paise: Math.round(Number(e.target.value) * 100) })}
                className={inputClass}
              />
            </Field>
            <Field label="Yearly price (₹)">
              <input
                type="number" min={0} value={draft.yearly_price_paise / 100}
                onChange={(e) => setDraft({ ...draft, yearly_price_paise: Math.round(Number(e.target.value) * 100) })}
                className={inputClass}
              />
            </Field>
            <Field label="Max screens" hint="0 = unlimited">
              <input type="number" min={0} value={draft.max_screens} onChange={(e) => setDraft({ ...draft, max_screens: Number(e.target.value) })} className={inputClass} />
            </Field>
            <Field label="Max ad slots" hint="0 = unlimited">
              <input type="number" min={0} value={draft.max_ad_slots} onChange={(e) => setDraft({ ...draft, max_ad_slots: Number(e.target.value) })} className={inputClass} />
            </Field>
            <Field label="Storage (GB)">
              <input
                type="number" min={0} value={Math.round(draft.max_storage_bytes / GIB)}
                onChange={(e) => setDraft({ ...draft, max_storage_bytes: Number(e.target.value) * GIB })}
                className={inputClass}
              />
            </Field>
          </div>
          <button
            type="submit" disabled={create.isPending}
            className="rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-50"
          >
            {create.isPending ? 'Creating…' : 'Create package'}
          </button>
        </form>
      )}

      <section className="overflow-hidden rounded-2xl border border-white/8 bg-[#0a0f1e]">
        <div className="flex items-center gap-2 border-b border-white/5 p-4 text-sm font-semibold">
          <PackageIcon className="size-4 text-violet-400" />
          {packages.length} packages
        </div>

        {isLoading ? (
          <p className="p-10 text-center text-sm text-white/40">Loading…</p>
        ) : packages.length === 0 ? (
          <p className="p-10 text-center text-sm text-white/40">No packages yet. Create one to approve tenants onto it.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-white/5 bg-white/[0.02] text-xs uppercase tracking-wider text-white/30">
                <tr>
                  <th className="p-4 pl-5 text-left">Package</th>
                  <th className="p-4 text-left">Monthly</th>
                  <th className="p-4 text-left">Screens</th>
                  <th className="p-4 text-left">Ad slots</th>
                  <th className="p-4 text-left">Storage (GB)</th>
                  <th className="p-4 text-left">Active</th>
                  <th className="p-4 pr-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {packages.map((pkg) => {
                  const dirty = Boolean(editing[pkg.id])
                  return (
                    <tr key={pkg.id} className="transition-colors hover:bg-white/[0.02]">
                      <td className="p-4 pl-5">
                        <input
                          value={fieldOf(pkg, 'name')}
                          onChange={(e) => edit(pkg.id, 'name', e.target.value)}
                          className={`${inputClass} w-36`}
                        />
                        <p className="mt-1 font-mono text-xs text-white/30">{pkg.slug}</p>
                      </td>
                      <td className="p-4">
                        <input
                          type="number" min={0}
                          value={Number(fieldOf(pkg, 'monthly_price_paise')) / 100}
                          onChange={(e) => edit(pkg.id, 'monthly_price_paise', Math.round(Number(e.target.value) * 100))}
                          className={`${inputClass} w-24`}
                        />
                        <p className="mt-1 text-xs text-white/30">{formatPaise(pkg.monthly_price_paise)}</p>
                      </td>
                      <td className="p-4">
                        <input type="number" min={0} value={fieldOf(pkg, 'max_screens')} onChange={(e) => edit(pkg.id, 'max_screens', Number(e.target.value))} className={`${inputClass} w-20`} />
                      </td>
                      <td className="p-4">
                        <input type="number" min={0} value={fieldOf(pkg, 'max_ad_slots')} onChange={(e) => edit(pkg.id, 'max_ad_slots', Number(e.target.value))} className={`${inputClass} w-20`} />
                      </td>
                      <td className="p-4">
                        <input
                          type="number" min={0}
                          value={Math.round(Number(fieldOf(pkg, 'max_storage_bytes')) / GIB)}
                          onChange={(e) => edit(pkg.id, 'max_storage_bytes', Number(e.target.value) * GIB)}
                          className={`${inputClass} w-24`}
                        />
                        <p className="mt-1 text-xs text-white/30">{formatBytes(pkg.max_storage_bytes)}</p>
                      </td>
                      <td className="p-4">
                        <input
                          type="checkbox"
                          checked={Boolean(fieldOf(pkg, 'is_active'))}
                          onChange={(e) => edit(pkg.id, 'is_active', e.target.checked)}
                          className="size-4 accent-violet-500"
                        />
                      </td>
                      <td className="p-4 pr-5">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => update.mutate({ id: pkg.id, body: editing[pkg.id] ?? {} })}
                            disabled={!dirty || update.isPending}
                            className="flex items-center gap-1.5 rounded-lg border border-violet-500/20 bg-violet-500/10 px-3 py-1.5 text-xs text-violet-400 transition-all hover:bg-violet-500/20 disabled:opacity-30"
                          >
                            <Save className="size-3" />
                            Save
                          </button>
                          <button
                            onClick={() => {
                              if (window.confirm(`Delete "${pkg.name}"? Tenants already on it keep their limits and the package is retired instead.`)) {
                                remove.mutate(pkg.id)
                              }
                            }}
                            disabled={remove.isPending}
                            className="flex items-center gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-400 transition-all hover:bg-rose-500/20 disabled:opacity-50"
                          >
                            <Trash2 className="size-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

const inputClass =
  'rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-violet-500/50'

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold text-white/60">
        {label} {hint && <span className="font-normal text-white/30">({hint})</span>}
      </span>
      {children}
    </label>
  )
}
