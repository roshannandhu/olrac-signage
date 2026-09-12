'use client'

import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { api } from '@/lib/api'

/**
 * Says out loud when the server cannot serve media.
 *
 * Without object storage every `/api/media/*` request is a 503, so every thumbnail renders
 * as a grey box that looks exactly like a missing file — and uploads fall back to the
 * container's own disk, which Render wipes on each redeploy, so they are gone within hours.
 * Both of those are invisible. "Thumbnail not showing" has been chased through the
 * dashboard, the booking code and the player more than once when the answer was two unset
 * environment variables all along.
 *
 * Shown to the tenant rather than only the operator on purpose: they are the one looking at
 * the blank tile and wondering what they did wrong.
 */
export function StorageWarning() {
  const { data } = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    // It changes when someone edits the environment and redeploys, not minute to minute.
    staleTime: 60_000,
    retry: false,
  })

  const status = data?.object_storage
  if (!status || !/ephemeral/i.test(status)) return null

  // Two different failures, and telling them apart matters: with a published bucket every
  // existing thumbnail renders and only NEW uploads are at risk, so repeating "this is why
  // thumbnails are blank" there would send someone chasing a bug that is not happening.
  const readsWork = /public read/i.test(status)

  if (readsWork) {
    return (
      <div
        role="alert"
        className="mb-4 flex flex-wrap items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-sm"
      >
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-foreground font-semibold">New uploads are not being saved permanently.</p>
          <p className="text-muted-foreground">
            Existing content plays normally. Anything uploaded from now on is written to
            temporary storage and disappears the next time the server restarts.{' '}
            <span className="text-foreground font-medium">Re-upload it after this is fixed.</span>
          </p>
          <p className="text-muted-foreground text-xs">
            Fix: set the storage API token in the backend&apos;s environment
            (<code className="text-foreground">AWS_ACCESS_KEY_ID</code> and{' '}
            <code className="text-foreground">AWS_SECRET_ACCESS_KEY</code>).
          </p>
        </div>
      </div>
    )
  }

  return (
    <div
      role="alert"
      className="mb-4 flex flex-wrap items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-sm"
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-foreground font-semibold">
          Media storage is not configured — this is why thumbnails are blank.
        </p>
        <p className="text-muted-foreground">
          Existing images and videos cannot be served, so they show as empty tiles here and
          do not play on your screens.{' '}
          <span className="text-foreground font-medium">
            Anything uploaded now is also lost the next time the server restarts.
          </span>
        </p>
        <p className="text-muted-foreground text-xs">
          Fix: set <code className="text-foreground">AWS_ACCESS_KEY_ID</code> and{' '}
          <code className="text-foreground">AWS_SECRET_ACCESS_KEY</code> in the backend&apos;s
          environment. Nothing else needs changing — media is served through the API, which
          signs each request itself.
        </p>
      </div>
    </div>
  )
}
