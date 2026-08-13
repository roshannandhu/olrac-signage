'use client'

import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, ImageIcon, Search, Tag, Trash2, Upload, UploadCloud, Video, X } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { MediaThumbnail } from '@/components/dashboard/media-thumbnail'
import { PageHeader } from '@/components/dashboard/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { expiryLabel, relativeTime } from '@/lib/format'
import { useAuthStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import type { ContentItem } from '@/lib/types'

type QueuedUpload = {
  file: File
  name: string
  status: 'queued' | 'uploading' | 'done' | 'error'
  progress: number
  error?: string
}

const stripExtension = (filename: string) => filename.replace(/\.[^.]+$/, '')
const isSupported = (file: File) => file.type.startsWith('image/') || file.type.startsWith('video/')

export default function ContentPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canEdit = user?.role === 'owner' || user?.role === 'editor'

  const contentQuery = useQuery({
    queryKey: ['content'],
    queryFn: api.getContent,
    refetchInterval: (query) => {
      const data = query.state.data as ContentItem[] | undefined
      return data?.some((item) => item.status === 'processing') ? 3000 : false
    },
  })

  const content = useMemo(() => contentQuery.data || [], [contentQuery.data])

  const [uploadOpen, setUploadOpen] = useState(false)
  const [queue, setQueue] = useState<QueuedUpload[]>([])
  const [tags, setTags] = useState('')
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const [search, setSearch] = useState('')
  const [tagFilter, setTagFilter] = useState<string | null>(null)
  const [deleteItem, setDeleteItem] = useState<ContentItem | null>(null)

  const allTags = useMemo(() => [...new Set(content.flatMap((item) => item.tags?.split(',').map((tag) => tag.trim()).filter(Boolean) || []))].sort(), [content])
  const filtered = useMemo(() => content.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(search.toLowerCase()) || item.tags?.toLowerCase().includes(search.toLowerCase())
    const matchesTag = !tagFilter || item.tags?.split(',').map((tag) => tag.trim()).includes(tagFilter)
    return matchesSearch && matchesTag
  }), [content, search, tagFilter])

  const addFiles = (files: FileList | null) => {
    if (!files?.length) return
    const accepted = [...files].filter(isSupported)
    const rejected = files.length - accepted.length
    if (rejected) toast.error(`${rejected} file${rejected === 1 ? '' : 's'} skipped — only images and video can be uploaded`)
    if (!accepted.length) return
    setQueue((current) => [
      ...current,
      ...accepted.map((file) => ({ file, name: stripExtension(file.name), status: 'queued' as const, progress: 0 })),
    ])
  }

  const patchItem = (index: number, patch: Partial<QueuedUpload>) =>
    setQueue((current) => current.map((entry, position) => position === index ? { ...entry, ...patch } : entry))

  const startUploads = async () => {
    setUploading(true)
    // Sequential on purpose: signage assets are large, and firing a dozen parallel
    // multipart requests at the media worker starves every one of them.
    let failures = 0
    for (const [index, entry] of queue.entries()) {
      if (entry.status === 'done') continue
      patchItem(index, { status: 'uploading', progress: 0, error: undefined })
      try {
        await api.uploadContent(entry.file, entry.name.trim() || entry.file.name, tags, (percent) => patchItem(index, { progress: percent }))
        patchItem(index, { status: 'done', progress: 100 })
      } catch (reason) {
        failures += 1
        patchItem(index, { status: 'error', error: reason instanceof Error ? reason.message : 'Upload failed' })
      }
    }
    setUploading(false)
    queryClient.invalidateQueries({ queryKey: ['content'] })

    const uploaded = queue.length - failures
    if (failures === 0) {
      toast.success(`${uploaded} file${uploaded === 1 ? '' : 's'} uploaded`)
      closeUpload(false)
    } else {
      toast.error(`${failures} of ${queue.length} upload${queue.length === 1 ? '' : 's'} failed`)
    }
  }

  const closeUpload = (open: boolean) => {
    if (open) { setUploadOpen(true); return }
    if (uploading) return
    setUploadOpen(false)
    setQueue([])
    setTags('')
    setDragging(false)
  }

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteContent(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['content'] }); queryClient.invalidateQueries({ queryKey: ['playlists'] }); toast.success('Media removed'); setDeleteItem(null) },
    onError: (error: Error) => toast.error(error.message),
  })
  const retryMutation = useMutation({
    mutationFn: (id: number) => api.retryContentProcessing(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['content'] }); toast.success('Retry queued') },
    onError: (error: Error) => toast.error(error.message),
  })

  if (contentQuery.isError) return <ErrorState message="The media library could not be loaded." onRetry={() => contentQuery.refetch()} />

  const pending = queue.filter((entry) => entry.status !== 'done').length

  const uploadDialog = (
    <Dialog open={uploadOpen} onOpenChange={closeUpload}>
      <DialogTrigger render={<Button />}><Upload data-icon="inline-start" /> Upload media</DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload media</DialogTitle>
          <DialogDescription>Drop as many images and videos as you like. Each player caches them for offline playback.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          <div
            onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files) }}
            className={cn(
              'rounded-2xl border border-dashed px-6 py-8 text-center transition-colors',
              dragging ? 'border-primary bg-primary/5' : 'border-border bg-muted/40',
            )}
          >
            <UploadCloud className="text-muted-foreground/60 mx-auto size-7" aria-hidden="true" />
            <p className="text-foreground mt-3 text-sm font-medium">Drop files here</p>
            <p className="text-muted-foreground/70 mt-1 text-xs">Images and video, as many as you need</p>
            <Button type="button" variant="outline" size="sm" className="bg-card mt-4" disabled={uploading} onClick={() => fileInput.current?.click()}>
              Choose files
            </Button>
            <input
              ref={fileInput}
              type="file"
              multiple
              accept="image/*,video/*"
              className="sr-only"
              onChange={(event) => { addFiles(event.target.files); event.target.value = '' }}
            />
          </div>

          {queue.length > 0 && (
            <>
              <ul className="max-h-64 space-y-2 overflow-y-auto pr-1">
                {queue.map((entry, index) => (
                  <li key={`${entry.file.name}-${index}`} className="border-hairline rounded-xl border p-3">
                    <div className="flex items-center gap-2">
                      {entry.status === 'done'
                        ? <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                        : entry.file.type.startsWith('video/')
                          ? <Video className="text-muted-foreground/70 size-4 shrink-0" aria-hidden="true" />
                          : <ImageIcon className="text-muted-foreground/70 size-4 shrink-0" aria-hidden="true" />}
                      <Input
                        value={entry.name}
                        disabled={uploading || entry.status === 'done'}
                        aria-label={`Display name for ${entry.file.name}`}
                        onChange={(event) => patchItem(index, { name: event.target.value })}
                        className="h-8 flex-1 text-sm"
                      />
                      {!uploading && entry.status !== 'done' && (
                        <button
                          type="button"
                          onClick={() => setQueue((current) => current.filter((_, position) => position !== index))}
                          className="text-muted-foreground/50 hover:text-destructive grid size-7 shrink-0 place-items-center rounded-lg"
                          aria-label={`Remove ${entry.file.name} from the queue`}
                        >
                          <X className="size-4" />
                        </button>
                      )}
                    </div>

                    {entry.status === 'uploading' && (
                      <div className="mt-2 flex items-center gap-2">
                        <div className="bg-muted h-1.5 flex-1 overflow-hidden rounded-full">
                          <div className="bg-primary h-full rounded-full transition-[width] duration-150" style={{ width: `${entry.progress}%` }} />
                        </div>
                        <span className="text-muted-foreground w-9 shrink-0 text-right font-mono text-[11px] tabular-nums">{entry.progress}%</span>
                      </div>
                    )}
                    {entry.status === 'error' && <p className="text-destructive mt-2 text-xs">{entry.error}</p>}
                  </li>
                ))}
              </ul>

              <div className="space-y-2">
                <Label htmlFor="media-tags">Tags for this batch <span className="text-muted-foreground/70 font-normal">(comma separated)</span></Label>
                <Input id="media-tags" value={tags} disabled={uploading} onChange={(event) => setTags(event.target.value)} placeholder="lobby, summer, promotion" />
              </div>

              <Button className="w-full" disabled={uploading || !pending} onClick={startUploads}>
                {uploading ? 'Uploading…' : `Upload ${pending} file${pending === 1 ? '' : 's'}`}
              </Button>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Asset library" title="Content" description="Keep every campaign asset organized, searchable, and ready to drop into a playlist." actions={canEdit ? uploadDialog : <Badge variant="outline">View only</Badge>} />

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:max-w-md"><Search className="text-muted-foreground/70 pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search media or tags…" className="bg-card pl-9" aria-label="Search content" /></div>
        {allTags.length > 0 && <div className="flex gap-2 overflow-x-auto pb-1" aria-label="Filter by tag"><Button size="sm" variant={!tagFilter ? 'secondary' : 'outline'} onClick={() => setTagFilter(null)}>All</Button>{allTags.map((tag) => <Button key={tag} size="sm" variant={tagFilter === tag ? 'secondary' : 'outline'} className="bg-card" onClick={() => setTagFilter(tag)}><Tag data-icon="inline-start" /> {tag}</Button>)}</div>}
      </div>

      {contentQuery.isLoading ? <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">{Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-72" />)}</div> : !content.length ? (
        <EmptyState icon={ImageIcon} title="Your library is empty" description="Upload an image or video, then add it to a playlist and publish it to a screen." action={canEdit ? <Button onClick={() => setUploadOpen(true)}><Upload data-icon="inline-start" /> Upload first asset</Button> : undefined} />
      ) : !filtered.length ? (
        <EmptyState icon={Search} title="No matching media" description="Try a different search term or clear the selected tag filter." action={<Button variant="outline" onClick={() => { setSearch(''); setTagFilter(null) }}>Clear filters</Button>} />
      ) : (
        <div className="stagger grid gap-5 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {filtered.map((item, index) => {
            const expiry = expiryLabel(item.expires_at)
            return <Card key={item.id} style={{ '--i': index } as React.CSSProperties} className={`group/card lift ring-hairline bg-card relative overflow-hidden border-0 py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1 ${item.status === 'processing' ? 'opacity-80' : 'hover:shadow-[0_15px_40px_rgba(15,23,42,.08)]'}`}>
              <MediaThumbnail item={item} className="aspect-video" />
              {item.status === 'processing' && (
                <div className="bg-background/50 absolute inset-0 z-10 grid place-items-center backdrop-blur-[2px]">
                  <div className="flex flex-col items-center gap-3">
                    <div className="border-brand size-6 animate-spin rounded-full border-2 border-t-transparent" />
                    <span className="text-foreground text-xs font-semibold tracking-wider uppercase shadow-sm">Processing…</span>
                  </div>
                </div>
              )}
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="text-foreground truncate font-semibold">{item.name}</h2>
                    <p className="text-muted-foreground/70 mt-1 flex items-center gap-1.5 text-xs capitalize">
                      {item.type === 'video' ? <Video className="size-3" /> : <ImageIcon className="size-3" />} {item.type} · added {relativeTime(item.uploaded_at)}
                    </p>
                  </div>
                  {canEdit && (
                    <button onClick={() => setDeleteItem(item)} className="text-muted-foreground/40 hover:bg-destructive/10 hover:text-destructive focus-visible:ring-destructive grid size-8 shrink-0 place-items-center rounded-lg focus-visible:ring-2 focus-visible:outline-none" aria-label={`Delete ${item.name}`}>
                      <Trash2 className="size-4" />
                    </button>
                  )}
                </div>
                {item.status === 'failed' && (
                  <div className="border-destructive/20 bg-destructive/5 mt-3 rounded-lg border p-3 text-sm">
                    <p className="text-destructive font-semibold">Processing failed</p>
                    <p className="text-muted-foreground mt-1 text-xs">{item.failed_reason || 'An unknown error occurred.'}</p>
                    {canEdit && (
                      <Button variant="outline" size="sm" className="mt-2 h-7 text-xs" disabled={retryMutation.isPending} onClick={() => retryMutation.mutate(item.id)}>
                        {retryMutation.isPending ? 'Retrying…' : 'Retry'}
                      </Button>
                    )}
                  </div>
                )}
                <div className="mt-4 flex min-h-6 flex-wrap gap-1.5">
                  {expiry && <Badge variant={expiry === 'Expired' ? 'danger' : 'warning'}>{expiry}</Badge>}
                  {item.tags?.split(',').map((tag) => tag.trim()).filter(Boolean).slice(0, 3).map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>)}
                </div>
              </CardContent>
            </Card>
          })}
        </div>
      )}

      <Dialog open={Boolean(deleteItem)} onOpenChange={(open) => !open && setDeleteItem(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Delete “{deleteItem?.name}”?</DialogTitle><DialogDescription>This removes the asset from every playlist. Players will stop using it on their next sync.</DialogDescription></DialogHeader>
          <DialogFooter showCloseButton><Button variant="destructive" disabled={deleteMutation.isPending} onClick={() => deleteItem && deleteMutation.mutate(deleteItem.id)}>{deleteMutation.isPending ? 'Deleting…' : 'Delete media'}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
