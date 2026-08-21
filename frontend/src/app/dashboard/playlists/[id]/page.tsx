'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import { PlaylistBuilder } from '@/components/dashboard/playlist-builder'

/**
 * Direct route to one playlist, kept for deep links and bookmarks.
 *
 * The editor itself now lives in a component so the same builder can be embedded on a
 * screen or a group page — which is where an operator actually edits a loop.
 */
export default function PlaylistBuilderPage() {
  const { id } = useParams<{ id: string }>()
  const playlistId = Number(id)

  return (
    <div className="space-y-6">
      <Link href="/dashboard/screens" className="text-muted-foreground hover:text-foreground inline-flex items-center gap-2 text-sm font-medium">
        <ArrowLeft className="size-4" /> Back to screens
      </Link>
      <PlaylistBuilder playlistId={playlistId} />
    </div>
  )
}
