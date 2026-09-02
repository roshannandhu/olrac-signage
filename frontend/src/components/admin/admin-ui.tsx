'use client'

import type { ReactNode } from 'react'
import { AlertTriangle, CheckCircle, Clock, XCircle } from 'lucide-react'

/**
 * Shared pieces for the platform-admin pages.
 *
 * All five of them draw the same status pills, stat cards and feedback banners; without a
 * shared home they get copy-pasted and drift, which is how the previous two admin screens
 * ended up disagreeing about how to call the API.
 */

export const statusStyles: Record<string, { label: string; className: string; Icon: typeof CheckCircle }> = {
  active: { label: 'Active', className: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30', Icon: CheckCircle },
  pending_approval: { label: 'Pending', className: 'text-amber-400 bg-amber-500/15 border-amber-500/30', Icon: Clock },
  suspended: { label: 'Suspended', className: 'text-rose-400 bg-rose-500/15 border-rose-500/30', Icon: XCircle },
  rejected: { label: 'Rejected', className: 'text-red-400 bg-red-500/15 border-red-500/30', Icon: XCircle },
}

export function StatusPill({ status }: { status: string }) {
  const style = statusStyles[status] ?? statusStyles.active
  const { Icon } = style
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium ${style.className}`}>
      <Icon className="size-3" />
      {style.label}
    </span>
  )
}

// Complete class strings, never interpolated.
//
// These used to be built as `bg-${color}-500/10`. Tailwind v4 discovers classes by scanning
// source text, and this project has no config file and no safelist -- so not one of those
// generated classes existed in the stylesheet and every stat card rendered unstyled.
const accents = {
  violet: { tile: 'bg-violet-500/10 border-violet-500/20', icon: 'text-violet-400' },
  emerald: { tile: 'bg-emerald-500/10 border-emerald-500/20', icon: 'text-emerald-400' },
  amber: { tile: 'bg-amber-500/10 border-amber-500/20', icon: 'text-amber-400' },
  cyan: { tile: 'bg-cyan-500/10 border-cyan-500/20', icon: 'text-cyan-400' },
  rose: { tile: 'bg-rose-500/10 border-rose-500/20', icon: 'text-rose-400' },
} as const

export type Accent = keyof typeof accents

export function StatCard({
  label, value, icon: Icon, accent = 'violet',
}: { label: string; value: ReactNode; icon: React.ElementType; accent?: Accent }) {
  const style = accents[accent]
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
      <div className={`grid size-9 place-items-center rounded-xl border ${style.tile}`}>
        <Icon className={`size-4 ${style.icon}`} />
      </div>
      <div className="min-w-0">
        <p className="text-xl font-bold text-white">{value}</p>
        <p className="truncate text-xs text-white/40">{label}</p>
      </div>
    </div>
  )
}

export function QuotaBar({ used, max }: { used: number; max: number | null }) {
  // null is "no limit configured", 0 is "a package that grants none". This used to treat
  // 0 as unlimited, which was right for the raw override column and wrong for the limit
  // now reported: every tenant's override is 0, so the console drew an infinity sign for
  // the whole estate while the packages behind them were capped.
  const unlimited = max === null || max === undefined
  const pct = unlimited || max === 0 ? 100 : Math.min(100, Math.round((used / max) * 100))
  const barColor = pct >= 100 ? 'bg-rose-500' : pct >= 80 ? 'bg-amber-500' : 'bg-violet-500'
  const textColor = pct >= 100 ? 'text-rose-400 font-semibold' : pct >= 80 ? 'text-amber-400' : 'text-white/60'
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className={textColor}>{used} / {unlimited ? '∞' : max}</span>
        {!unlimited && <span className="text-white/30">{pct}%</span>}
      </div>
      {!unlimited && (
        <div className="h-1 overflow-hidden rounded-full bg-white/5">
          <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  )
}

export function Feedback({ ok, error }: { ok?: string; error?: string }) {
  if (!ok && !error) return null
  return (
    <div
      role="status"
      className={`flex items-center gap-2 rounded-xl border p-3 text-sm ${
        error
          ? 'border-rose-500/30 bg-rose-500/10 text-rose-400'
          : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
      }`}
    >
      {error ? <AlertTriangle className="size-4 shrink-0" /> : <CheckCircle className="size-4 shrink-0" />}
      {error || ok}
    </div>
  )
}

export function PageHeader({ title, description, children }: { title: string; description?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {description && <p className="mt-0.5 text-sm text-white/50">{description}</p>}
      </div>
      {children}
    </div>
  )
}

export function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function formatPaise(paise: number): string {
  return paise === 0 ? 'Free' : `₹${(paise / 100).toLocaleString('en-IN')}`
}
