'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, BellOff, DownloadCloud, HardDrive, MonitorX, PauseCircle, RefreshCw, XCircle } from 'lucide-react'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { ListToolbar } from '@/components/dashboard/list-toolbar'
import { Badge } from '@/components/ui/badge'
import { DropdownMenuItem } from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { relativeTime } from '@/lib/format'
import type { ContentItem, Screen } from '@/lib/types'

type Severity = 'critical' | 'warning'

type Alert = {
  id: string
  severity: Severity
  icon: typeof MonitorX
  title: string
  detail: string
  href: string
  at: string | null
}

/** A screen quiet for this long is a fault, not a slow heartbeat. */
const OFFLINE_HOURS = 1
/** Below this a player cannot cache the next advert. */
const LOW_STORAGE_MB = 500

const hoursSince = (value: string | null | undefined) =>
  value ? (Date.now() - Date.parse(value)) / 3_600_000 : Infinity

/**
 * Derived rather than stored.
 *
 * Every condition here is already visible in data the console polls, so persisting an
 * alert table would only add a way for the two to disagree.
 */
function buildAlerts(screens: Screen[], content: ContentItem[]): Alert[] {
  const alerts: Alert[] = []

  for (const screen of screens) {
    const label = screen.name || `Screen ${screen.id}`
    const href = `/dashboard/screens/${screen.id}`

    if (screen.status !== 'online' && hoursSince(screen.last_seen) > OFFLINE_HOURS) {
      alerts.push({
        id: `offline-${screen.id}`,
        severity: 'critical',
        icon: MonitorX,
        title: `${label} is offline`,
        detail: `No heartbeat since ${relativeTime(screen.last_seen)}. Check power and network at the site.`,
        href,
        at: screen.last_seen,
      })
    }

    if (screen.last_error) {
      alerts.push({
        id: `error-${screen.id}`,
        severity: 'critical',
        icon: AlertTriangle,
        title: `${label} reported a playback error`,
        detail: screen.last_error,
        href,
        at: screen.last_error_at,
      })
    }

    if (screen.free_storage_mb !== null && screen.free_storage_mb !== undefined && screen.free_storage_mb < LOW_STORAGE_MB) {
      alerts.push({
        id: `storage-${screen.id}`,
        severity: 'warning',
        icon: HardDrive,
        title: `${label} is low on storage`,
        detail: `${screen.free_storage_mb} MB free. New content may fail to cache for offline playback.`,
        href,
        at: screen.last_seen,
      })
    }

    // A rollout that stalled. Left alone these quietly never update.
    if (screen.update_status === 'failed') {
      alerts.push({
        id: `update-${screen.id}`,
        severity: 'warning',
        icon: DownloadCloud,
        title: `${label} failed to update`,
        detail: `Still on ${screen.app_version || 'an unknown version'}, wanted ${screen.target_version_code ?? 'the latest'}. It will retry, but repeated failures need a look.`,
        href,
        at: screen.last_seen,
      })
    }

    // Online and idle is worse than offline: the screen looks fine and sells nothing.
    if (screen.status === 'online' && screen.playback_state === 'idle') {
      alerts.push({
        id: `idle-${screen.id}`,
        severity: 'critical',
        icon: PauseCircle,
        title: `${label} is on but not playing`,
        detail: screen.effective_playlist_id
          ? 'It has a playlist but reports nothing playing. Check the content downloaded correctly.'
          : 'No playlist is assigned, so this screen is showing nothing to anybody.',
        href,
        at: screen.last_seen,
      })
    }
  }

  for (const item of content) {
    if (item.status === 'failed') {
      alerts.push({
        id: `content-${item.id}`,
        severity: 'warning',
        icon: XCircle,
        title: `“${item.name}” failed to process`,
        detail: item.failed_reason || 'Transcoding did not complete, so no screen can play this asset.',
        href: '/dashboard/content',
        at: item.uploaded_at,
      })
    }
  }

  // Criticals first, then most recent — the order an operator would triage in.
  return alerts.sort((a, b) => {
    if (a.severity !== b.severity) return a.severity === 'critical' ? -1 : 1
    return Date.parse(b.at || '0') - Date.parse(a.at || '0')
  })
}

export default function AlertsPage() {
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens, refetchInterval: 30000 })
  const contentQuery = useQuery({ queryKey: ['content'], queryFn: api.getContent })

  const [severity, setSeverity] = useState<Severity | 'all'>('all')
  const [search, setSearch] = useState('')

  const alerts = useMemo(
    () => buildAlerts(screensQuery.data || [], contentQuery.data || []),
    [screensQuery.data, contentQuery.data],
  )

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return alerts.filter((alert) => {
      const matchesSeverity = severity === 'all' || alert.severity === severity
      const matchesSearch = !term || alert.title.toLowerCase().includes(term) || alert.detail.toLowerCase().includes(term)
      return matchesSeverity && matchesSearch
    })
  }, [alerts, severity, search])

  const criticals = alerts.filter((alert) => alert.severity === 'critical').length

  if (screensQuery.isError || contentQuery.isError) {
    return <ErrorState message="Alerts could not be loaded." onRetry={() => { screensQuery.refetch(); contentQuery.refetch() }} />
  }

  return (
    <div>
      <ListToolbar
        title="Alerts"
        action={
          alerts.length > 0
            ? <Badge variant={criticals ? 'danger' : 'warning'}>{criticals ? `${criticals} critical` : `${alerts.length} to review`}</Badge>
            : undefined
        }
        search={{ value: search, onChange: setSearch }}
        filters={
          <>
            {(['all', 'critical', 'warning'] as const).map((value) => (
              <DropdownMenuItem key={value} onClick={() => setSeverity(value)} className={severity === value ? 'bg-accent font-medium' : undefined}>
                <span className="capitalize">{value === 'all' ? 'All alerts' : value}</span>
              </DropdownMenuItem>
            ))}
          </>
        }
      />

      {screensQuery.isLoading ? (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-20 rounded-xl" />)}</div>
      ) : !alerts.length ? (
        <EmptyState icon={BellOff} title="Nothing needs attention" description="Every screen is reporting in and all content processed cleanly." />
      ) : !filtered.length ? (
        <EmptyState icon={RefreshCw} title="No matching alerts" description="Try a different search term or severity." />
      ) : (
        <div className="space-y-3">
          {filtered.map((alert) => {
            const Icon = alert.icon
            const critical = alert.severity === 'critical'
            return (
              <Link
                key={alert.id}
                href={alert.href}
                className="ring-hairline bg-card focus-visible:ring-ring flex items-start gap-4 rounded-xl p-4 ring-1 transition-shadow hover:shadow-md focus-visible:ring-2 focus-visible:outline-none"
              >
                <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${critical ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400' : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'}`}>
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-foreground font-semibold">{alert.title}</h2>
                    <Badge variant={critical ? 'danger' : 'warning'}>{alert.severity}</Badge>
                  </div>
                  <p className="text-muted-foreground mt-1 text-sm">{alert.detail}</p>
                </div>
                {alert.at && <span className="text-muted-foreground/70 shrink-0 text-xs">{relativeTime(alert.at)}</span>}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
