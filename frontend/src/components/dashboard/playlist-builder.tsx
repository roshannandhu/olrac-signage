'use client'

import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { closestCenter, DndContext, type DragEndEvent, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { CalendarClock, Check, ChevronDown, Clock3, GripVertical, ListVideo, Plus, Search, Sparkles, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { BookOrExtendDialog } from '@/components/dashboard/book-or-extend-dialog'
import { MediaThumbnail } from '@/components/dashboard/media-thumbnail'
import { PageHeader } from '@/components/dashboard/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { invalidateBookingViews } from '@/lib/query-keys'
import { assetOrientation, clipDuration, dateTimeLocal, loopDuration } from '@/lib/format'
import { useAuthStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import type { ContentItem, Playlist, PlaylistItem, TransitionName } from '@/lib/types'

const transitionOptions: { value: TransitionName; label: string; description: string }[] = [
  { value: 'none', label: 'Cut', description: 'Immediate handoff' },
  { value: 'fade', label: 'Fade', description: 'Soft crossfade' },
  { value: 'slide_left', label: 'Slide left', description: 'Next ad enters from right' },
  { value: 'slide_right', label: 'Slide right', description: 'Next ad enters from left' },
  { value: 'slide_up', label: 'Slide up', description: 'Next ad enters from below' },
  { value: 'slide_down', label: 'Slide down', description: 'Next ad enters from above' },
  { value: 'zoom', label: 'Zoom', description: 'Subtle depth change' },
]

// '' means "follow whatever the screen is set to"; a number overrides it for this item
// only, which is how one portrait advert plays correctly on a landscape wall.
const rotationOptions = [
  { value: '', label: 'Follow screen' },
  { value: '0', label: 'Landscape (0°)' },
  { value: '90', label: 'Portrait (90°)' },
  { value: '180', label: 'Landscape flipped (180°)' },
  { value: '270', label: 'Portrait flipped (270°)' },
]
const rotationLabel = (value: string | null) =>
  rotationOptions.find((option) => option.value === (value ?? ''))?.label || 'Follow screen'

const transitionLabel = (value: TransitionName) => transitionOptions.find((option) => option.value === value)?.label || value

type Selection = TransitionName | 'inherit'

function previewStyle(type: TransitionName, incoming: boolean, phase: boolean, durationMs: number): CSSProperties {
  const style: CSSProperties = {
    opacity: 1,
    transform: 'translate3d(0,0,0) scale(1)',
    transitionProperty: 'transform, opacity',
    transitionDuration: `${durationMs}ms`,
    transitionTimingFunction: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
  }
  if (!phase) {
    if (type === 'fade') style.opacity = incoming ? 0 : 1
    if (type === 'slide_left') style.transform = incoming ? 'translate3d(100%,0,0)' : 'translate3d(0,0,0)'
    if (type === 'slide_right') style.transform = incoming ? 'translate3d(-100%,0,0)' : 'translate3d(0,0,0)'
    if (type === 'slide_up') style.transform = incoming ? 'translate3d(0,100%,0)' : 'translate3d(0,0,0)'
    if (type === 'slide_down') style.transform = incoming ? 'translate3d(0,-100%,0)' : 'translate3d(0,0,0)'
    if (type === 'zoom') {
      style.opacity = incoming ? 0 : 1
      style.transform = incoming ? 'translate3d(0,0,0) scale(0.7)' : 'translate3d(0,0,0) scale(1)'
    }
  } else {
    if (type === 'fade') style.opacity = incoming ? 1 : 0
    if (type === 'slide_left') style.transform = incoming ? 'translate3d(0,0,0)' : 'translate3d(-100%,0,0)'
    if (type === 'slide_right') style.transform = incoming ? 'translate3d(0,0,0)' : 'translate3d(100%,0,0)'
    if (type === 'slide_up') style.transform = incoming ? 'translate3d(0,0,0)' : 'translate3d(0,-100%,0)'
    if (type === 'slide_down') style.transform = incoming ? 'translate3d(0,0,0)' : 'translate3d(0,100%,0)'
    if (type === 'zoom') {
      style.opacity = incoming ? 1 : 0
      style.transform = incoming ? 'translate3d(0,0,0) scale(1)' : 'translate3d(0,0,0) scale(1.3)'
    }
  }
  return style
}

function TransitionPreview({ transition, durationMs, compact = false }: { transition: TransitionName; durationMs: number; compact?: boolean }) {
  const [phase, setPhase] = useState(false)
  useEffect(() => {
    if (transition === 'none') return
    const interval = setInterval(() => setPhase((current) => !current), Math.max(durationMs + 700, 1500))
    return () => clearInterval(interval)
  }, [transition, durationMs])
  return (
    <div className={cn('relative overflow-hidden rounded-xl border border-hairline bg-slate-950 font-mono text-white', compact ? 'h-16 w-24' : 'h-24 w-full sm:w-44')}>
      <div style={previewStyle(transition, false, phase, durationMs)} className="absolute inset-0 flex items-center justify-center bg-slate-800 text-[11px] font-semibold tracking-wider text-slate-200">AD 1</div>
      <div style={previewStyle(transition, true, phase, durationMs)} className="absolute inset-0 flex items-center justify-center bg-primary text-[11px] font-semibold tracking-wider text-white">AD 2</div>
    </div>
  )
}

function DefaultTransitionPanel({ playlist, disabled, pending, onSave }: {
  playlist: Playlist
  disabled: boolean
  pending: boolean
  onSave: (transition: TransitionName, durationMs: number, applyToAll: boolean) => void
}) {
  const [transition, setTransition] = useState<TransitionName>(playlist.default_transition)
  const [durationMs, setDurationMs] = useState(playlist.default_transition_ms)
  const dirty = transition !== playlist.default_transition || durationMs !== playlist.default_transition_ms
  return (
    <Card className="mb-6 border-hairline bg-card/60 shadow-[0_1px_2px_rgba(15,23,42,.04)]">
      <CardContent className="flex flex-col gap-6 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1 space-y-4">
          <div>
            <p className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Sparkles className="size-4 text-primary" /> Default handoff
            </p>
            <p className="text-muted-foreground/80 mt-1 text-xs">Used by every item that does not have its own transition.</p>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label className="text-muted-foreground mb-2 text-xs">Transition</Label>
              <Select value={transition} onValueChange={(value: TransitionName | null) => value && setTransition(value)} disabled={disabled}>
                <SelectTrigger className="w-full"><SelectValue>{(value: TransitionName | null) => (value ? transitionLabel(value) : 'Choose transition')}</SelectValue></SelectTrigger>
                <SelectContent>{transitionOptions.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between">
                <Label htmlFor="default-transition-duration" className="text-muted-foreground text-xs">Duration</Label>
                <span className="text-muted-foreground font-mono text-xs">{durationMs} ms</span>
              </div>
              <input id="default-transition-duration" type="range" min={100} max={3000} step={50} value={durationMs} disabled={disabled} onChange={(event) => setDurationMs(Number(event.target.value))} className="accent-primary h-10 w-full" />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Button size="sm" variant="outline" disabled={disabled || pending || !dirty} onClick={() => onSave(transition, durationMs, false)}>Save default</Button>
            <Button size="sm" variant="default" disabled={disabled || pending} onClick={() => onSave(transition, durationMs, true)}><Sparkles data-icon="inline-start" /> Apply to all items</Button>
          </div>
        </div>
        <TransitionPreview transition={transition} durationMs={durationMs} />
      </CardContent>
    </Card>
  )
}

// One row per item. Everything below the summary line is collapsed by default: with
// the transition and schedule editors both always open, a twenty-item loop rendered
// forty selects, forty sliders and a hundred and forty day toggles on one screen —
// and each item needed two separate saves to commit one change.
function ItemRow({ item, defaultTransition, defaultDurationMs, canEdit, saving, onRemove, onSave, highlighted = false }: {
  item: PlaylistItem
  defaultTransition: TransitionName
  defaultDurationMs: number
  canEdit: boolean
  saving: boolean
  onRemove: () => void
  onSave: (data: {
    duration: number
    start_at: string | null
    end_at: string | null
    schedule: { days_of_week: number[]; start_time: string | null; end_time: string | null } | null
    transition: TransitionName | null
    transition_ms: number | null
    rotation: number | null
  }) => void
  highlighted?: boolean
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id, disabled: !canEdit })
  const [open, setOpen] = useState(false)

  const [form, setForm] = useState({
    duration: item.duration,
    startAt: dateTimeLocal(item.start_at),
    endAt: dateTimeLocal(item.end_at),
    days: item.schedule?.days_of_week || [],
    windowStart: item.schedule?.start_time || '',
    windowEnd: item.schedule?.end_time || '',
    selection: (item.transition ?? 'inherit') as Selection,
    transitionMs: item.transition_ms ?? defaultDurationMs,
    rotation: item.rotation === null || item.rotation === undefined ? '' : String(item.rotation),
  })

  const dirty =
    form.duration !== item.duration ||
    form.startAt !== dateTimeLocal(item.start_at) ||
    form.endAt !== dateTimeLocal(item.end_at) ||
    form.selection !== (item.transition ?? 'inherit') ||
    (form.selection !== 'inherit' && form.transitionMs !== (item.transition_ms ?? defaultDurationMs)) ||
    form.rotation !== (item.rotation === null || item.rotation === undefined ? '' : String(item.rotation))

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((current) => ({ ...current, [key]: value }))

  const effectiveTransition = form.selection === 'inherit' ? defaultTransition : form.selection
  const effectiveMs = form.selection === 'inherit' ? defaultDurationMs : form.transitionMs
  const scheduled = Boolean(item.start_at || item.end_at || item.schedule)

  const save = () => {
    if (form.startAt && form.endAt && form.endAt <= form.startAt) {
      toast.error('The end date must be after the start date')
      return
    }
    const hasWindow = Boolean(form.days.length || form.windowStart || form.windowEnd)
    onSave({
      duration: form.duration,
      start_at: form.startAt || null,
      end_at: form.endAt || null,
      schedule: hasWindow ? { days_of_week: form.days, start_time: form.windowStart || null, end_time: form.windowEnd || null } : null,
      transition: form.selection === 'inherit' ? null : form.selection,
      transition_ms: form.selection === 'inherit' ? null : form.transitionMs,
      rotation: form.rotation === '' ? null : Number(form.rotation),
    })
  }

  return (
    <Card
      id={`timeline-item-${item.id}`}
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        'border-0 bg-card py-0 ring-1 ring-hairline transition-all duration-300',
        isDragging ? 'z-20 opacity-80 shadow-2xl' : 'shadow-[0_1px_2px_rgba(15,23,42,.04)]',
        item.id < 0 && 'animate-in fade-in zoom-in-95 ring-2 ring-primary/40 bg-primary/5 duration-500',
        highlighted && 'ring-2 ring-primary bg-primary/5 shadow-lg shadow-primary/25 scale-[1.015]'
      )}
    >
      <CardContent className="p-4 sm:p-5">
        <div className="flex items-center gap-3">
          <button type="button" {...attributes} {...listeners} disabled={!canEdit} className="grid size-9 shrink-0 cursor-grab place-items-center rounded-lg text-muted-foreground/40 hover:bg-muted hover:text-muted-foreground active:cursor-grabbing disabled:cursor-default focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none" aria-label={`Move ${item.content.name}`}><GripVertical className="size-5" /></button>
          <MediaThumbnail item={item.content} className="size-16 shrink-0 rounded-xl" />

          <div className="min-w-0 flex-1">
            <p className="text-foreground truncate font-semibold">{item.content.name}</p>
            <p className="text-muted-foreground/70 mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
              <span className="inline-flex items-center gap-1"><Clock3 className="size-3" /> {loopDuration(item.duration)}{item.content.type === 'video' && clipDuration(item.content.duration_ms) && <span className="text-muted-foreground/60"> of {clipDuration(item.content.duration_ms)}</span>}</span>
              <span aria-hidden="true">·</span>
              <span>{item.transition ? transitionLabel(item.transition) : `${transitionLabel(defaultTransition)} (default)`}</span>
              <span aria-hidden="true">·</span>
              {item.start_at || item.end_at || item.schedule
                ? <span className="text-amber-700 dark:text-amber-300">Scheduled</span>
                : <span>Always on</span>}
            </p>
          </div>

          <Button
            variant="ghost"
            size="sm"
            aria-expanded={open}
            aria-controls={`item-settings-${item.id}`}
            onClick={() => setOpen((current) => !current)}
            className="text-muted-foreground shrink-0"
          >
            <ChevronDown className={cn('size-4 transition-transform', open && 'rotate-180')} aria-hidden="true" />
            <span className="sr-only sm:not-sr-only">{open ? 'Close' : 'Edit'}</span>
          </Button>

          {canEdit && <Button variant="ghost" size="icon" className="text-muted-foreground/40 hover:bg-destructive/10 hover:text-destructive shrink-0" onClick={onRemove} aria-label={`Remove ${item.content.name}`}><Trash2 /></Button>}
        </div>

        {open && (
          <div id={`item-settings-${item.id}`} className="border-hairline mt-5 border-t pt-5">
            <fieldset disabled={!canEdit || saving} className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <div>
                <p className="text-muted-foreground mb-3 flex items-center gap-2 text-xs font-semibold"><Sparkles className="text-primary size-3.5" /> Handoff to next ad</p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_96px] sm:items-end">
                  <div>
                    <Label className="text-muted-foreground mb-2 text-xs">Transition</Label>
                    <Select value={form.selection} onValueChange={(value: Selection | null) => value && set('selection', value)}>
                      <SelectTrigger className="w-full"><SelectValue>{(value: Selection | null) => value === 'inherit' ? `Use default (${transitionLabel(defaultTransition)})` : value ? transitionLabel(value) : 'Choose transition'}</SelectValue></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="inherit">Use playlist default</SelectItem>
                        {transitionOptions.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <TransitionPreview transition={effectiveTransition} durationMs={effectiveMs} compact />
                </div>
                <div className={cn('mt-3', form.selection === 'inherit' && 'opacity-50')}>
                  <div className="mb-2 flex items-center justify-between">
                    <Label htmlFor={`transition-duration-${item.id}`} className="text-muted-foreground text-xs">Handoff duration</Label>
                    <span className="text-muted-foreground font-mono text-xs">{effectiveMs} ms</span>
                  </div>
                  <input id={`transition-duration-${item.id}`} type="range" min={100} max={3000} step={50} value={form.transitionMs} disabled={!canEdit || saving || form.selection === 'inherit'} onChange={(event) => set('transitionMs', Number(event.target.value))} className="accent-primary h-10 w-full" />
                </div>
              </div>

              <div>
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-muted-foreground flex items-center gap-2 text-xs font-semibold"><CalendarClock className="text-primary size-3.5" /> Playback rules</p>
                  <Badge variant={scheduled ? 'warning' : 'success'}>{scheduled ? 'Scheduled' : 'Always active'}</Badge>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div>
                    <Label htmlFor={`duration-${item.id}`} className="text-muted-foreground mb-2 text-xs">Seconds</Label>
                    {item.content.type === 'video' ? (
                      // A video's on-screen time is its own length — there is nothing to
                      // choose, so showing an editable box only invites a wrong answer.
                      <p className="border-input text-muted-foreground flex h-10 items-center rounded-lg border px-3 text-sm">
                        Plays the full clip{clipDuration(item.content.duration_ms) && ` (${clipDuration(item.content.duration_ms)})`}
                      </p>
                    ) : (
                      <Input id={`duration-${item.id}`} type="number" min={1} max={86400} value={form.duration} onChange={(event) => set('duration', Math.max(1, Number(event.target.value)))} />
                    )}
                  </div>
                  <div>
                    <Label htmlFor={`start-${item.id}`} className="text-muted-foreground mb-2 text-xs">Starts</Label>
                    <Input id={`start-${item.id}`} type="datetime-local" value={form.startAt} onChange={(event) => set('startAt', event.target.value)} />
                  </div>
                  <div>
                    <Label htmlFor={`end-${item.id}`} className="text-muted-foreground mb-2 text-xs">Expires</Label>
                    <Input id={`end-${item.id}`} type="datetime-local" value={form.endAt} onChange={(event) => set('endAt', event.target.value)} />
                  </div>
                </div>
                <div className="mt-3">
                  <Label className="text-muted-foreground mb-2 text-xs">Rotation</Label>
                  <Select value={form.rotation} onValueChange={(value: string | null) => set('rotation', value ?? '')}>
                    <SelectTrigger className="w-full">
                      <SelectValue>{(value: string | null) => rotationLabel(value)}</SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {rotationOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {/* Per-item Days / From / Until removed: an advert's timing now comes from
                    its client booking, which is the only place a sale is recorded. The
                    placement writes start_at and end_at onto the item (see
                    placements.sync_placement_window), so two editable controls for the same
                    thing meant the manual one was silently overwritten on the next booking
                    change. The backend Schedule model and the player's ScheduleEvaluator are
                    untouched, so a window already saved keeps applying and is preserved
                    through an unrelated edit. */}
              </div>
            </fieldset>

            {canEdit && (
              <div className="mt-5 flex items-center justify-end gap-3">
                {dirty && <span className="text-muted-foreground text-xs">Unsaved changes</span>}
                <Button size="sm" variant="outline" disabled={!dirty || saving} onClick={save}>
                  {saving ? 'Saving…' : <><Check data-icon="inline-start" /> Save item</>}
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface FlyingItem {
  id: string
  content: ContentItem
  startX: number
  startY: number
  targetX: number
  targetY: number
  direction?: 'forward' | 'reverse'
}

export function PlaylistBuilder({ playlistId, showHeader = true, screenId }: {
  playlistId: number
  showHeader?: boolean
  /** Set on a screen's own page. Booked adverts then join or leave THIS screen instantly. */
  screenId?: number
}) {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canEdit = user?.role === 'owner' || user?.role === 'editor'
  const playlistKey = useMemo(() => ['playlist', playlistId], [playlistId])
  const playlistQuery = useQuery({ queryKey: playlistKey, queryFn: () => api.getPlaylist(playlistId), enabled: Number.isFinite(playlistId) })
  const contentQuery = useQuery({ queryKey: ['content'], queryFn: api.getContent })
  const [localOrder, setLocalOrder] = useState<number[] | null>(null)
  const [search, setSearch] = useState('')
  const [savingItem, setSavingItem] = useState<number | null>(null)
  const [flyingItems, setFlyingItems] = useState<FlyingItem[]>([])
  const [highlightedItemId, setHighlightedItemId] = useState<number | null>(null)
  const timelineRef = useRef<HTMLElement | null>(null)
  const libraryRef = useRef<HTMLElement | null>(null)
  const flyCounterRef = useRef(0)

  const serverItems = useMemo(() => [...(playlistQuery.data?.items || [])].sort((a, b) => a.order - b.order), [playlistQuery.data?.items])
  const items = useMemo(() => {
    if (!localOrder) return serverItems
    const byId = new Map(serverItems.map((item) => [item.id, item]))
    const ordered = localOrder.map((itemId) => byId.get(itemId)).filter((item): item is PlaylistItem => Boolean(item))
    return ordered.length === serverItems.length ? ordered : serverItems
  }, [localOrder, serverItems])
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }))
  const invalidate = () => { queryClient.invalidateQueries({ queryKey: playlistKey }); queryClient.invalidateQueries({ queryKey: ['playlists'] }) }
  const reorderMutation = useMutation({ mutationFn: (orders: number[]) => api.reorderPlaylistItems(playlistId, orders), onSuccess: () => { setLocalOrder(null); invalidate(); toast.success('Order saved') }, onError: (error: Error) => { setLocalOrder(null); toast.error(error.message); playlistQuery.refetch() } })
  // An advert with no running booking opens the booking dialog: it may not reach a screen
  // without a client, because the placement is what records the sale, the paid window and the
  // proof-of-play an invoice is built from.
  const [bookingFor, setBookingFor] = useState<ContentItem | null>(null)
  // Screens the operator would expect an advert booked from THIS loop to appear on.
  // effective_playlist_id, not playlist_id, so a screen that inherits this playlist from
  // its group counts -- that is still a screen showing this loop.
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens })
  const screensShowingThisPlaylist = useMemo(
    () => (screensQuery.data || []).filter((screen) => screen.effective_playlist_id === playlistId),
    [screensQuery.data, playlistId],
  )

  // Add and remove change the timeline in the cache first and let the server catch up, so a
  // row appears or goes the moment it is pressed. Each round trip is several queries to a
  // database a region away; waiting on it is what made moving an advert feel slow. A refusal
  // restores the snapshot, so the timeline never keeps something the server did not accept.
  const snapshot = async () => {
    await queryClient.cancelQueries({ queryKey: playlistKey })
    return queryClient.getQueryData<Playlist>(playlistKey)
  }
  const restore = (previous: Playlist | undefined) => { if (previous) queryClient.setQueryData(playlistKey, previous) }

  // Removing a booked advert ends its run on this screen only (the server unplaces that
  // booking target, so the repair loop does not put it back), and the library -- which reads
  // bookings from ['content'] -- refreshes with it.
  const removeMutation = useMutation({
    mutationFn: (itemId: number) => api.removePlaylistItem(playlistId, itemId),
    onMutate: async (itemId) => {
      const previous = await snapshot()
      if (previous) queryClient.setQueryData<Playlist>(playlistKey, { ...previous, items: previous.items.filter((item) => item.id !== itemId) })
      return { previous }
    },
    onError: (error: Error, _itemId, context) => { restore(context?.previous); toast.error(error.message) },
    onSuccess: () => toast.success(screenId ? 'Removed from this screen' : 'Item removed'),
    onSettled: () => invalidateBookingViews(queryClient),
  })

  // A booked advert joins this screen on the booking it already has: same client, same paid
  // window, no new sale, so there is nothing to ask. The server still guards what matters --
  // the plan's screen count, and never the same advert twice in one loop.
  const addBookedMutation = useMutation({
    mutationFn: (content: ContentItem) => api.addPlacementTarget(content.placement_id as number, { screen_id: screenId as number }),
    onMutate: async (content) => {
      const previous = await snapshot()
      if (previous) {
        const order = previous.items.reduce((max, item) => Math.max(max, item.order), -1) + 1
        const pending: PlaylistItem = {
          id: -content.id,
          content_id: content.id,
          content,
          duration: content.duration_ms ? Math.max(1, Math.round(content.duration_ms / 1000)) : 10,
          rotation: null,
          order,
          start_at: content.placement_starts_at ?? null,
          end_at: content.placement_ends_at ?? null,
          transition: null,
          transition_ms: null,
          schedule: null,
        }
        queryClient.setQueryData<Playlist>(playlistKey, { ...previous, items: [...previous.items, pending] })
      }
      return { previous }
    },
    onError: (error: Error, content, context) => {
      restore(context?.previous)
      toast.error(error.message)
      // The plan sold fewer screens than this would make. Changing the plan is the way
      // forward, and the booking dialog is where that happens.
      if (/plan|sold \d+ screen/i.test(error.message)) setBookingFor(content)
    },
    onSuccess: () => toast.success('Added to this screen'),
    onSettled: () => invalidateBookingViews(queryClient),
  })

  // Zero-lag instant optimistic update for editing item duration, rotation, schedule, and transition
  const updateMutation = useMutation({
    mutationFn: ({ itemId, data }: { itemId: number; data: Parameters<typeof api.updatePlaylistItem>[2] }) =>
      api.updatePlaylistItem(playlistId, itemId, data),
    onMutate: async ({ itemId, data }) => {
      setSavingItem(itemId)
      const previous = await snapshot()
      if (previous) {
        queryClient.setQueryData<Playlist>(playlistKey, {
          ...previous,
          items: previous.items.map((it) => {
            if (it.id !== itemId) return it
            return {
              ...it,
              duration: data.duration !== undefined ? data.duration : it.duration,
              rotation: data.rotation !== undefined ? data.rotation : it.rotation,
              start_at: data.start_at !== undefined ? data.start_at : it.start_at,
              end_at: data.end_at !== undefined ? data.end_at : it.end_at,
              schedule: data.schedule !== undefined ? data.schedule : it.schedule,
              transition: data.transition !== undefined ? data.transition : it.transition,
              transition_ms: data.transition_ms !== undefined ? data.transition_ms : it.transition_ms,
            }
          }),
        })
      }
      return { previous }
    },
    onError: (error: Error, _vars, context) => {
      restore(context?.previous)
      toast.error(error.message)
    },
    onSuccess: () => {
      invalidate()
      invalidateBookingViews(queryClient)
      toast.success('Item settings saved')
    },
    onSettled: () => setSavingItem(null),
  })

  // Zero-lag instant optimistic update for default playlist transitions
  const transitionMutation = useMutation({
    mutationFn: ({ transition, durationMs, applyToAll }: { transition: TransitionName; durationMs: number; applyToAll: boolean }) =>
      api.updatePlaylistTransitions(playlistId, { transition, transition_ms: durationMs, apply_to_all: applyToAll }),
    onMutate: async ({ transition, durationMs, applyToAll }) => {
      const previous = await snapshot()
      if (previous) {
        queryClient.setQueryData<Playlist>(playlistKey, {
          ...previous,
          default_transition: transition,
          default_transition_ms: durationMs,
          items: applyToAll
            ? previous.items.map((it) => ({
                ...it,
                transition,
                transition_ms: durationMs,
              }))
            : previous.items,
        })
      }
      return { previous }
    },
    onError: (error: Error, _vars, context) => {
      restore(context?.previous)
      toast.error(error.message)
    },
    onSuccess: (_, variables) => {
      invalidate()
      invalidateBookingViews(queryClient)
      toast.success(variables.applyToAll ? 'Transition applied to every item' : 'Playlist default saved')
    },
  })

  const handleDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return
    const oldIndex = items.findIndex((item) => item.id === active.id)
    const newIndex = items.findIndex((item) => item.id === over.id)
    const next = arrayMove(items, oldIndex, newIndex)
    const order = next.map((item) => item.id)
    setLocalOrder(order)
    reorderMutation.mutate(order)
  }

  // The player has no notion of "the same advert", so a second copy in one loop is simply
  // the ad airing twice a cycle -- billed once, delivered twice. The server refuses it; the
  // library marks the advert as already here instead of offering something that can only fail.
  const placedContentIds = useMemo(() => new Set(items.map((item) => item.content.id)), [items])

  // Every advert, in two groups. Booked = its latest booking has not finished, including one
  // that starts later; the moment that window closes it reads as Not booked, with no job to
  // move it. The fetch time stands in for "now" so rendering stays pure, and it advances on
  // every refetch.
  // Items already placed in the loop are filtered out so they disappear when added and return on removal.
  const fetchedAt = contentQuery.dataUpdatedAt
  const library = useMemo(() => {
    const term = search.toLowerCase()
    const matches = (contentQuery.data || []).filter(
      (item) =>
        !placedContentIds.has(item.id) &&
        (item.name.toLowerCase().includes(term) || item.tags?.toLowerCase().includes(term)),
    )
    const isBooked = (item: ContentItem) =>
      Boolean(item.placement_id && item.placement_ends_at && new Date(item.placement_ends_at).getTime() > fetchedAt)
    return { booked: matches.filter(isBooked), notBooked: matches.filter((item) => !isBooked(item)) }
  }, [contentQuery.data, search, fetchedAt, placedContentIds])

  if (playlistQuery.isError || contentQuery.isError) return <ErrorState message="The playlist builder could not be loaded." onRetry={() => { playlistQuery.refetch(); contentQuery.refetch() }} />
  if (playlistQuery.isLoading) return <div className="space-y-6"><Skeleton className="h-24" /><div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_340px]"><Skeleton className="h-[520px]" /><Skeleton className="h-[520px]" /></div></div>
  const playlist = playlistQuery.data
  if (!playlist) return null
  const totalDuration = items.reduce((total, item) => total + item.duration, 0)
  const shortDate = (value?: string | null) => (value ? new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '')

  const handleAddItem = (content: ContentItem, instant: boolean, event?: React.MouseEvent) => {
    const placed = placedContentIds.has(content.id)
    if (placed) {
      const existing = items.find((it) => it.content.id === content.id)
      if (existing) {
        setHighlightedItemId(existing.id)
        const el = document.getElementById(`timeline-item-${existing.id}`)
        el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        setTimeout(() => setHighlightedItemId((prev) => (prev === existing.id ? null : prev)), 2000)
        toast.info(`"${content.name}" is already in this loop`)
      }
      return
    }

    // Capture starting position from clicked card
    let startX = window.innerWidth * 0.75
    let startY = 300
    if (event) {
      const btn = event.currentTarget as HTMLElement
      const row = btn.closest('[data-library-row]') as HTMLElement
      const rect = (row || btn).getBoundingClientRect()
      startX = rect.left
      startY = rect.top
    }

    // Target landing point in the Playback Timeline
    let targetX = window.innerWidth * 0.25
    let targetY = 350
    if (timelineRef.current) {
      const tRect = timelineRef.current.getBoundingClientRect()
      targetX = tRect.left + 24
      targetY = Math.min(window.innerHeight - 120, Math.max(120, tRect.bottom - 40))
    }

    flyCounterRef.current += 1
    const flyId = `${content.id}-${flyCounterRef.current}`
    setFlyingItems((prev) => [
      ...prev,
      { id: flyId, content, startX, startY, targetX, targetY, direction: 'forward' },
    ])
    setTimeout(() => {
      setFlyingItems((prev) => prev.filter((it) => it.id !== flyId))
    }, 520)

    if (instant) {
      addBookedMutation.mutate(content)
    } else {
      setBookingFor(content)
    }
  }

  const handleRemoveItem = (item: PlaylistItem) => {
    const rowEl = document.getElementById(`timeline-item-${item.id}`)
    let startX = window.innerWidth * 0.25
    let startY = 350
    if (rowEl) {
      const rect = rowEl.getBoundingClientRect()
      startX = rect.left
      startY = rect.top
    }

    let targetX = window.innerWidth * 0.75
    let targetY = 300
    if (libraryRef.current) {
      const lRect = libraryRef.current.getBoundingClientRect()
      targetX = lRect.left + 24
      targetY = Math.min(window.innerHeight - 120, Math.max(120, lRect.top + 80))
    }

    flyCounterRef.current += 1
    const flyId = `reverse-${item.content.id}-${flyCounterRef.current}`
    setFlyingItems((prev) => [
      ...prev,
      {
        id: flyId,
        content: item.content,
        startX,
        startY,
        targetX,
        targetY,
        direction: 'reverse',
      },
    ])
    setTimeout(() => {
      setFlyingItems((prev) => prev.filter((it) => it.id !== flyId))
    }, 520)

    removeMutation.mutate(item.id)
  }

  const libraryRow = (content: ContentItem, booked: boolean) => {
    const placed = placedContentIds.has(content.id)
    const startsLater = booked && Boolean(content.placement_starts_at) && new Date(content.placement_starts_at as string).getTime() > fetchedAt
    const adding = addBookedMutation.isPending && addBookedMutation.variables?.id === content.id
    const instant = booked && Boolean(screenId)
    return (
      <div
        key={content.id}
        data-library-row
        id={`library-item-${content.id}`}
        className={cn(
          'flex items-center gap-3 rounded-xl border border-hairline p-2.5 transition-all duration-300 hover:bg-muted animate-in fade-in duration-300',
          placed && 'bg-muted/40'
        )}
      >
        <div className="relative size-12 shrink-0">
          <MediaThumbnail item={content} className="size-12 rounded-lg" />
          {clipDuration(content.duration_ms) && (
            <span className="absolute right-0 bottom-0 rounded bg-black/75 px-1 text-[9px] font-semibold text-white">
              {clipDuration(content.duration_ms)}
            </span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">{content.name}</p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground/70">
            {booked
              ? <span className="text-emerald-700 dark:text-emerald-400">{startsLater ? `Starts ${shortDate(content.placement_starts_at)}` : `Booked until ${shortDate(content.placement_ends_at)}`}</span>
              : <span className="capitalize">{content.type}{assetOrientation(content.renditions) && ` • ${assetOrientation(content.renditions)}`}</span>}
            {content.client_name && ` • ${content.client_name}`}
          </p>
        </div>
        <Button
          size="icon-sm"
          variant={instant ? 'default' : 'outline'}
          disabled={!canEdit || adding}
          onClick={(e) => handleAddItem(content, instant, e)}
          aria-label={instant ? `Add ${content.name} to this screen` : `Book ${content.name}`}
          className={cn(
            'transition-transform active:scale-90',
            placed && 'border-primary/40 text-primary hover:bg-primary/10'
          )}
        >
          <Plus className="size-4" />
        </Button>
      </div>
    )
  }

  return (
    <div className="relative space-y-8">
      {/* Moving transition flying animation overlay */}
      {flyingItems.map((flying) => {
        const isReverse = flying.direction === 'reverse'
        return (
          <div
            key={flying.id}
            className="pointer-events-none fixed z-[99999] will-change-transform"
            style={
              {
                left: 0,
                top: 0,
                width: 290,
                animation: 'flyTranslate 520ms cubic-bezier(0.2, 0.9, 0.3, 1) forwards',
                '--fly-start-x': `${flying.startX}px`,
                '--fly-start-y': `${flying.startY}px`,
                '--fly-end-x': `${flying.targetX}px`,
                '--fly-end-y': `${flying.targetY}px`,
              } as React.CSSProperties & Record<string, string | number>
            }
          >
            <div
              className={cn(
                'flex items-center gap-3 rounded-2xl border p-3 backdrop-blur-xl shadow-2xl transition-colors will-change-transform',
                isReverse
                  ? 'border-amber-500/30 bg-card/90 ring-1 ring-amber-500/50 dark:bg-slate-900/90'
                  : 'border-primary/30 bg-card/90 ring-1 ring-primary/50 dark:bg-slate-900/90'
              )}
              style={{
                animation: isReverse
                  ? 'flyElevationReverse 520ms cubic-bezier(0.25, 1, 0.5, 1) forwards'
                  : 'flyElevationForward 520ms cubic-bezier(0.25, 1, 0.5, 1) forwards',
              }}
            >
              <div className="size-11 shrink-0 overflow-hidden rounded-xl bg-black/10 ring-1 ring-black/10 dark:ring-white/10 shadow-sm">
                <MediaThumbnail item={flying.content} className="size-11 rounded-xl object-cover" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-foreground tracking-tight">{flying.content.name}</p>
                {isReverse ? (
                  <span className="mt-0.5 inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                    <Sparkles className="size-2.5 animate-pulse" /> Returning to library
                  </span>
                ) : (
                  <span className="mt-0.5 inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                    <Sparkles className="size-2.5 animate-spin" /> Adding to timeline
                  </span>
                )}
              </div>
            </div>
          </div>
        )
      })}

      {showHeader && <PageHeader eyebrow="Playlist builder" title={playlist.name} description="Set the loop order, control each handoff, and schedule exactly when every item may play." actions={<div className="flex items-center gap-2"><Badge variant="outline">{items.length} items</Badge><Badge variant="outline">{loopDuration(totalDuration)} loop</Badge>{!canEdit && <Badge variant="warning">View only</Badge>}</div>} />}

      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section id="playback-timeline-container" ref={timelineRef} aria-labelledby="timeline-title">
          <h2 id="timeline-title" className="mb-4 text-sm font-semibold text-foreground">Playback timeline</h2>
          <DefaultTransitionPanel key={`${playlist.default_transition}-${playlist.default_transition_ms}`} playlist={playlist} disabled={!canEdit} pending={transitionMutation.isPending} onSave={(transition, durationMs, applyToAll) => transitionMutation.mutate({ transition, durationMs, applyToAll })} />
          {!items.length ? <EmptyState icon={ListVideo} title="This playlist has no content" description="Choose an asset from the library to start building the loop." /> : (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={items.map((item) => item.id)} strategy={verticalListSortingStrategy}>
                {/* A row still being added has no server id yet, so nothing can be done to it until it lands. */}
                <div className="space-y-3">
                  {items.map((item) => (
                    <ItemRow
                      key={item.id}
                      item={item}
                      defaultTransition={playlist.default_transition}
                      defaultDurationMs={playlist.default_transition_ms}
                      canEdit={canEdit && item.id > 0}
                      saving={savingItem === item.id}
                      highlighted={highlightedItemId === item.id}
                      onRemove={() => handleRemoveItem(item)}
                      onSave={(data) => updateMutation.mutate({ itemId: item.id, data })}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          )}
        </section>

        <aside ref={libraryRef} className="rounded-2xl bg-card p-4 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1 ring-hairline xl:sticky xl:top-6" aria-labelledby="library-title">
          <div><h2 id="library-title" className="font-semibold text-foreground">Content library</h2><p className="mt-1 text-xs text-muted-foreground/70">{library.booked.length + library.notBooked.length} ads{screenId ? ' · booked ones add instantly' : ''}</p></div>
          <div className="relative mt-4"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground/70" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search assets…" className="pl-9" aria-label="Search library" /></div>
          <div className="mt-4 max-h-[660px] space-y-5 overflow-y-auto pr-1">
            {contentQuery.isLoading ? Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} className="h-20" />) : (
              <>
                <div>
                  <p className="mb-2 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-muted-foreground">Booked <span className="font-normal normal-case">{library.booked.length}</span></p>
                  <div className="space-y-2">{library.booked.map((content) => libraryRow(content, true))}</div>
                  {!library.booked.length && (
                    <p className="rounded-xl border border-dashed border-hairline p-3 text-xs text-muted-foreground/70">
                      {placedContentIds.size > 0 ? 'All booked ads are in this loop.' : 'No ad has a running booking.'}
                    </p>
                  )}
                </div>
                <div>
                  <p className="mb-1 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-muted-foreground">Not booked <span className="font-normal normal-case">{library.notBooked.length}</span></p>
                  <p className="mb-2 text-[11px] text-muted-foreground/70">Adding one asks for a plan or a custom booking.</p>
                  <div className="space-y-2">{library.notBooked.map((content) => libraryRow(content, false))}</div>
                  {!library.notBooked.length && (
                    <p className="rounded-xl border border-dashed border-hairline p-3 text-xs text-muted-foreground/70">
                      {placedContentIds.size > 0 ? 'No other ads in library.' : 'Every ad is booked.'}
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        </aside>
      </div>

      {/* A new booking, or a plan change when a booked advert has run out of screens. */}
      {bookingFor && (
        <BookOrExtendDialog
          content={bookingFor}
          screens={screensShowingThisPlaylist}
          open={Boolean(bookingFor)}
          onOpenChange={(next) => { if (!next) setBookingFor(null) }}
        />
      )}
    </div>
  )
}
