'use client'

import { useMemo, useRef, useState } from 'react'
import { useBulkSelection } from '@/hooks/use-bulk-selection'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, ImageIcon, RefreshCw, Search, Trash2, Upload, UploadCloud, Video, X } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { AssetCard, AssetGrid, OverlayBadge } from '@/components/dashboard/asset-card'
import { BulkActionBar, SelectAllCheckbox } from '@/components/dashboard/bulk-action-bar'
import { ListToolbar, commonSorts, sortItems, type CommonSort } from '@/components/dashboard/list-toolbar'
import { MediaThumbnail } from '@/components/dashboard/media-thumbnail'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { DropdownMenuItem } from '@/components/ui/dropdown-menu'
import { assetOrientation, clipDuration, expiryLabel, relativeTime } from '@/lib/format'
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

  const clientsQuery = useQuery({ queryKey: ['clients'], queryFn: api.getClients })
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens })
  const sellScreens = screensQuery.data || []
  const plansQuery = useQuery({ queryKey: ['tenant-plans'], queryFn: () => api.getTenantPlans() })
  const sellClients = clientsQuery.data || []
  const sellPlans = plansQuery.data || []

  const [uploadOpen, setUploadOpen] = useState(false)
  const [queue, setQueue] = useState<QueuedUpload[]>([])
  const [tags, setTags] = useState('')
  // Selling the advert as it is uploaded. Both optional: leaving them blank uploads the
  // files and nothing else, which is what this dialog did before.
  const [sellClientId, setSellClientId] = useState('')
  const [sellPlanId, setSellPlanId] = useState('')
  const [sellScreenIds, setSellScreenIds] = useState<number[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const chosenPlan = sellPlans.find((plan) => String(plan.id) === sellPlanId)

  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<CommonSort>('newest')
  const [tagFilter, setTagFilter] = useState<string | null>(null)
  const [deleteItem, setDeleteItem] = useState<ContentItem | null>(null)
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)
  // Dragging over the whole page, not just the dialog — depth counting because dragenter
  // and dragleave also fire for every child element the pointer crosses.
  const [pageDragDepth, setPageDragDepth] = useState(0)

  const allTags = useMemo(() => [...new Set(content.flatMap((item) => item.tags?.split(',').map((tag) => tag.trim()).filter(Boolean) || []))].sort(), [content])
  const filtered = useMemo(() => {
    const matches = content.filter((item) => {
      const matchesSearch = item.name.toLowerCase().includes(search.toLowerCase()) || item.tags?.toLowerCase().includes(search.toLowerCase())
      const matchesTag = !tagFilter || item.tags?.split(',').map((tag) => tag.trim()).includes(tagFilter)
      return matchesSearch && matchesTag
    })
    return sortItems(matches, sort, (item) => item.name, (item) => item.uploaded_at)
  }, [content, search, sort, tagFilter])

  const bulk = useBulkSelection(filtered)

  const bulkDelete = useMutation({
    mutationFn: async () => {
      // Sequential: the worker cleans up renditions per asset and parallel deletes make it
      // contend with itself for the same files.
      for (const id of bulk.selected) await api.deleteContent(id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
      queryClient.invalidateQueries({ queryKey: ['playlists'] })
      toast.success(`${bulk.selected.length} asset${bulk.selected.length === 1 ? '' : 's'} deleted`)
      bulk.clear()
      setBulkDeleteOpen(false)
    },
    onError: (error: Error) => toast.error(error.message),
  })

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
        const uploaded = await api.uploadContent(entry.file, entry.name.trim() || entry.file.name, tags, (percent) => patchItem(index, { progress: percent }))
        // Sold on the way in, if a plan was chosen. Deliberately AFTER the upload resolves:
        // a booking pointing at content that failed to upload is worse than no booking.
        if (sellPlanId && uploaded?.id) {
          try {
            await api.createPlacement({
              content_id: uploaded.id,
              client_id: sellClientId ? Number(sellClientId) : undefined,
              advertiser: sellClientId ? undefined : 'Unassigned client',
              plan_id: Number(sellPlanId),
              price_paise: 0,
              is_paid: false,
              starts_at: new Date().toISOString(),
              targets: sellScreenIds.map((id) => ({ screen_id: id })),
            })
          } catch (reason) {
            // The file is safely uploaded either way, so this must not mark the row failed
            // and invite the operator to upload it a second time.
            toast.error(`Uploaded "${entry.name}", but the booking could not be created: ${reason instanceof Error ? reason.message : 'unknown error'}`)
          }
        }
        patchItem(index, { status: 'done', progress: 100 })
      } catch (reason) {
        failures += 1
        patchItem(index, { status: 'error', error: reason instanceof Error ? reason.message : 'Upload failed' })
      }
    }
    setUploading(false)
    queryClient.invalidateQueries({ queryKey: ['content'] })
    if (sellPlanId) queryClient.invalidateQueries({ queryKey: ['placements'] })

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
    setSellClientId('')
    setSellPlanId('')
    setSellScreenIds([])
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

  if (contentQuery.isError) return <ErrorState message={`The media library could not be loaded. Error: ${contentQuery.error?.message}`} onRetry={() => contentQuery.refetch()} />

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

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="sell-plan">Sell on plan <span className="text-muted-foreground/70 font-normal">(optional)</span></Label>
                  <select
                    id="sell-plan"
                    className="border-input bg-background h-10 w-full rounded-lg border px-3 text-sm"
                    value={sellPlanId}
                    disabled={uploading}
                    onChange={(event) => {
                      setSellPlanId(event.target.value)
                      const next = sellPlans.find((plan) => String(plan.id) === event.target.value)
                      // Switching to a smaller plan must not leave more screens picked than
                      // it covers -- the API would refuse the booking after the upload.
                      if (next) setSellScreenIds((current) => current.slice(0, next.max_locations))
                      else setSellScreenIds([])
                    }}
                  >
                    <option value="">Upload only</option>
                    {sellPlans.map((plan) => (
                      <option key={plan.id} value={String(plan.id)}>{plan.name} ({plan.duration_days} days)</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sell-client">Client</Label>
                  <select
                    id="sell-client"
                    className="border-input bg-background h-10 w-full rounded-lg border px-3 text-sm"
                    value={sellClientId}
                    disabled={uploading || !sellPlanId}
                    onChange={(event) => setSellClientId(event.target.value)}
                  >
                    <option value="">Choose later</option>
                    {sellClients.map((client) => (
                      <option key={client.id} value={String(client.id)}>{client.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              {chosenPlan ? (
                <div className="space-y-2">
                  <Label>
                    Screens{' '}
                    <span className="text-muted-foreground/70 font-normal">
                      ({sellScreenIds.length} of {chosenPlan.max_locations} · {chosenPlan.duration_days} days)
                    </span>
                  </Label>
                  <div className="border-hairline max-h-40 space-y-1 overflow-y-auto rounded-xl border p-2">
                    {!sellScreens.length && <p className="text-muted-foreground p-2 text-sm">No screens paired yet.</p>}
                    {sellScreens.map((screen) => {
                      const picked = sellScreenIds.includes(screen.id)
                      // Capped in the UI as well as at the API, so the limit is visible
                      // before the operator has filled in a booking that will be refused.
                      const full = !picked && sellScreenIds.length >= chosenPlan.max_locations
                      return (
                        <label
                          key={screen.id}
                          className={`flex items-center gap-3 rounded-lg p-2 text-sm ${full ? 'opacity-40' : 'hover:bg-muted cursor-pointer'}`}
                        >
                          <input
                            type="checkbox"
                            className="accent-primary size-4"
                            checked={picked}
                            disabled={uploading || full}
                            onChange={(event) => setSellScreenIds((current) =>
                              event.target.checked ? [...current, screen.id] : current.filter((id) => id !== screen.id))}
                          />
                          <span className="truncate">{screen.name || `Screen ${screen.id}`}</span>
                        </label>
                      )
                    })}
                  </div>
                  <p className="text-muted-foreground text-xs">
                    This plan covers {chosenPlan.max_locations} screen{chosenPlan.max_locations === 1 ? '' : 's'} for{' '}
                    {chosenPlan.duration_days} days. A booking is created per file, priced and dated from the plan, and
                    the advert comes off the screens automatically when it ends.
                  </p>
                </div>
              ) : null}

              <Button className="w-full" disabled={uploading || !pending} onClick={startUploads}>
                {uploading ? 'Uploading…' : `Upload ${pending} file${pending === 1 ? '' : 's'}`}
              </Button>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )

  const dropHandlers = canEdit ? {
    onDragEnter: (event: React.DragEvent) => {
      if (event.dataTransfer.types.includes('Files')) setPageDragDepth((depth) => depth + 1)
    },
    onDragOver: (event: React.DragEvent) => {
      if (event.dataTransfer.types.includes('Files')) event.preventDefault()
    },
    onDragLeave: () => setPageDragDepth((depth) => Math.max(0, depth - 1)),
    onDrop: (event: React.DragEvent) => {
      if (!event.dataTransfer.files?.length) return
      event.preventDefault()
      setPageDragDepth(0)
      addFiles(event.dataTransfer.files)
      setUploadOpen(true)
    },
  } : {}

  return (
    <div className="relative" {...dropHandlers}>
      {pageDragDepth > 0 && (
        <div className="border-primary bg-primary/5 pointer-events-none fixed inset-4 z-50 grid place-items-center rounded-2xl border-2 border-dashed backdrop-blur-sm">
          <div className="text-center">
            <UploadCloud className="text-primary dark:text-brand mx-auto size-10" aria-hidden="true" />
            <p className="text-foreground mt-3 text-lg font-semibold">Drop to upload</p>
            <p className="text-muted-foreground text-sm">Images and video</p>
          </div>
        </div>
      )}
      <ListToolbar
        title="Content library"
        action={canEdit ? uploadDialog : <Badge variant="outline">View only</Badge>}
        sort={{ value: sort, onChange: setSort, options: commonSorts }}
        search={{ value: search, onChange: setSearch, placeholder: 'Search' }}
        filters={
          <>
            <DropdownMenuItem onClick={() => setTagFilter(null)} className={!tagFilter ? 'bg-accent font-medium' : undefined}>
              All tags
            </DropdownMenuItem>
            {allTags.map((tag) => (
              <DropdownMenuItem key={tag} onClick={() => setTagFilter(tag)} className={tagFilter === tag ? 'bg-accent font-medium' : undefined}>
                {tag}
              </DropdownMenuItem>
            ))}
            {allTags.length === 0 && <p className="text-muted-foreground px-3 py-2 text-sm">No tags yet</p>}
          </>
        }
      />

      {canEdit && filtered.length > 0 && (
        <div className="mb-3">
          <SelectAllCheckbox
            checked={bulk.allVisibleSelected}
            indeterminate={bulk.someVisibleSelected}
            onChange={bulk.toggleAll}
            label={`Select all ${filtered.length}`}
          />
        </div>
      )}

      {canEdit && (
        <BulkActionBar count={bulk.selected.length} noun="asset" onClear={bulk.clear}>
          <Button size="sm" variant="destructive" onClick={() => setBulkDeleteOpen(true)}>
            <Trash2 data-icon="inline-start" /> Delete selected
          </Button>
        </BulkActionBar>
      )}

      {contentQuery.isLoading ? (
        <AssetGrid>{Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-64 rounded-xl" />)}</AssetGrid>
      ) : !content.length ? (
        <EmptyState icon={ImageIcon} title="Your library is empty" description="Upload an image or video, then add it to a playlist and publish it to a screen." action={canEdit ? <Button onClick={() => setUploadOpen(true)}><Upload data-icon="inline-start" /> Upload first asset</Button> : undefined} />
      ) : !filtered.length ? (
        <EmptyState icon={Search} title="No matching media" description="Try a different search term or clear the selected tag filter." action={<Button variant="outline" onClick={() => { setSearch(''); setTagFilter(null) }}>Clear filters</Button>} />
      ) : (
        <AssetGrid>
          {filtered.map((item) => {
            const expiry = expiryLabel(item.expires_at)
            const orientation = assetOrientation(item.renditions)
            const duration = clipDuration(item.duration_ms)
            return (
              <div key={item.id} className="relative">
                {canEdit && (
                  <label className="absolute top-2.5 right-2.5 z-10 grid size-7 cursor-pointer place-items-center rounded-md bg-black/50 backdrop-blur">
                    <input
                      type="checkbox"
                      className="accent-primary size-4"
                      checked={bulk.isSelected(item.id)}
                      onChange={(event) => bulk.toggle(item.id, event.target.checked)}
                      aria-label={`Select ${item.name}`}
                    />
                  </label>
                )}
              <AssetCard
                href={`/dashboard/content/${item.id}`}
                title={item.name}
                subtitle={
                  <>
                    {/* Only the leading noun is capitalised — `capitalize` on the whole
                        line title-cases the timestamp into "22 Hours Ago". */}
                    <span className="capitalize">{item.type}</span>
                    {orientation && ` • ${orientation}`}
                    {` • ${relativeTime(item.uploaded_at)}`}
                  </>
                }
                preview={
                  <>
                    <MediaThumbnail item={item} className="size-full" />
                    {item.status === 'processing' && (
                      <div className="bg-background/50 absolute inset-0 grid place-items-center backdrop-blur-[2px]">
                        <div className="flex flex-col items-center gap-2">
                          <div className="border-primary size-6 animate-spin rounded-full border-2 border-t-transparent" />
                          <span className="text-foreground text-[11px] font-semibold tracking-wider uppercase">Processing</span>
                        </div>
                      </div>
                    )}
                  </>
                }
                badges={
                  <>
                    {expiry && <OverlayBadge tone="danger">{expiry}</OverlayBadge>}
                    {item.status === 'failed' && <OverlayBadge tone="danger">Failed</OverlayBadge>}
                  </>
                }
                cornerBadge={duration ? <OverlayBadge>{duration}</OverlayBadge> : undefined}
                menu={canEdit ? (
                  <>
                    {item.status === 'failed' && (
                      <DropdownMenuItem onClick={() => retryMutation.mutate(item.id)}>
                        <RefreshCw aria-hidden="true" /> Retry processing
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem onClick={() => setDeleteItem(item)} className="text-destructive">
                      <Trash2 aria-hidden="true" /> Delete
                    </DropdownMenuItem>
                  </>
                ) : undefined}
              />
              </div>
            )
          })}
        </AssetGrid>
      )}

      <Dialog open={bulkDeleteOpen} onOpenChange={setBulkDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {bulk.selected.length} asset{bulk.selected.length === 1 ? '' : 's'}?</DialogTitle>
            <DialogDescription>
              They are removed from every playlist, and their files and transcoded renditions are deleted from disk. Players stop using them on the next sync.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter showCloseButton>
            <Button variant="destructive" disabled={bulkDelete.isPending} onClick={() => bulkDelete.mutate()}>
              {bulkDelete.isPending ? 'Deleting…' : `Delete ${bulk.selected.length}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(deleteItem)} onOpenChange={(open) => !open && setDeleteItem(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Delete “{deleteItem?.name}”?</DialogTitle><DialogDescription>This removes the asset from every playlist. Players will stop using it on their next sync.</DialogDescription></DialogHeader>
          <DialogFooter showCloseButton><Button variant="destructive" disabled={deleteMutation.isPending} onClick={() => deleteItem && deleteMutation.mutate(deleteItem.id)}>{deleteMutation.isPending ? 'Deleting…' : 'Delete media'}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
