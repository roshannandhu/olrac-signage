'use client'

import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { closestCenter, DndContext, type DragEndEvent, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { CalendarClock, Check, ChevronDown, Clock3, GripVertical, ListVideo, Plus, Search, Sparkles, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
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
import { assetOrientation, clipDuration, dateTimeLocal, loopDuration } from '@/lib/format'
import { useAuthStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import type { Playlist, PlaylistItem, TransitionName } from '@/lib/types'

const dayLabels = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
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
    transitionProperty: 'opacity, transform',
    transitionDuration: type === 'none' ? '0ms' : `${durationMs}ms`,
    transitionTimingFunction: 'cubic-bezier(.22,1,.36,1)',
  }
  if (type === 'none' || type === 'fade') style.opacity = incoming ? (phase ? 1 : 0) : (phase ? 0 : 1)
  if (type === 'zoom') {
    style.opacity = incoming ? (phase ? 1 : 0) : (phase ? 0 : 1)
    style.transform = incoming ? `scale(${phase ? 1 : 0.86})` : `scale(${phase ? 1.12 : 1})`
  }
  const directions: Partial<Record<TransitionName, [string, string]>> = {
    slide_left: ['translateX(100%)', 'translateX(-100%)'],
    slide_right: ['translateX(-100%)', 'translateX(100%)'],
    slide_up: ['translateY(100%)', 'translateY(-100%)'],
    slide_down: ['translateY(-100%)', 'translateY(100%)'],
  }
  const direction = directions[type]
  if (direction) style.transform = incoming ? (phase ? 'translate3d(0,0,0)' : direction[0]) : (phase ? direction[1] : 'translate3d(0,0,0)')
  return style
}

function TransitionPreview({ transition, durationMs, compact = false }: { transition: TransitionName; durationMs: number; compact?: boolean }) {
  const [phase, setPhase] = useState(false)
  // One interval per preview. Depending on `phase` here instead would tear down and
  // re-create a timer on every tick, for every item on the page, forever.
  useEffect(() => {
    const interval = window.setInterval(() => setPhase((current) => !current), Math.max(900, durationMs + 450))
    return () => window.clearInterval(interval)
  }, [durationMs])
  return (
    <div className={cn('relative shrink-0 overflow-hidden rounded-xl bg-slate-950 ring-1 ring-black/10', compact ? 'h-14 w-24' : 'h-24 w-full')} aria-label={`${transitionLabel(transition)} transition preview`}>
      <div className="absolute inset-0 grid place-items-center bg-slate-800 text-xs font-bold tracking-[0.2em] text-white" style={previewStyle(transition, false, phase, durationMs)}>AD 1</div>
      <div className="absolute inset-0 grid place-items-center bg-brand text-xs font-bold tracking-[0.2em] text-rail" style={previewStyle(transition, true, phase, durationMs)}>AD 2</div>
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
  return (
    <Card className="mb-5 border-0 bg-card py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1 ring-hairline">
      <CardContent className="grid grid-cols-1 gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_220px] lg:items-center">
        <div>
          <div className="flex items-start gap-3"><span className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary dark:text-brand"><Sparkles className="size-4" /></span><div><h3 className="font-semibold text-foreground">Default handoff</h3><p className="mt-1 text-sm text-muted-foreground">Used by every item that does not have its own transition.</p></div></div>
          <fieldset disabled={disabled || pending} className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-[minmax(180px,1fr)_minmax(180px,1fr)]">
            <div><Label className="mb-2 text-xs text-muted-foreground">Transition</Label><Select value={transition} onValueChange={(value: TransitionName | null) => value && setTransition(value)}><SelectTrigger className="w-full"><SelectValue>{(value: TransitionName | null) => value ? transitionLabel(value) : 'Choose transition'}</SelectValue></SelectTrigger><SelectContent>{transitionOptions.map((option) => <SelectItem key={option.value} value={option.value}><span><span className="block">{option.label}</span><span className="block text-xs text-muted-foreground">{option.description}</span></span></SelectItem>)}</SelectContent></Select></div>
            <div><div className="mb-2 flex items-center justify-between"><Label htmlFor="default-transition-duration" className="text-xs text-muted-foreground">Duration</Label><span className="font-mono text-xs text-muted-foreground">{durationMs} ms</span></div><input id="default-transition-duration" type="range" min={100} max={3000} step={50} value={durationMs} onChange={(event) => setDurationMs(Number(event.target.value))} className="h-10 w-full accent-primary" /></div>
          </fieldset>
          {!disabled && <div className="mt-4 flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={pending} onClick={() => onSave(transition, durationMs, false)}>Save default</Button><Button size="sm" disabled={pending} onClick={() => onSave(transition, durationMs, true)}><Sparkles data-icon="inline-start" /> Apply to all items</Button></div>}
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
function ItemRow({ item, defaultTransition, defaultDurationMs, canEdit, saving, onRemove, onSave }: {
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
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id, disabled: !canEdit })
  const [open, setOpen] = useState(false)

  const initial = useMemo(() => ({
    duration: item.duration,
    rotation: item.rotation === null || item.rotation === undefined ? '' : String(item.rotation),
    selection: (item.transition || 'inherit') as Selection,
    transitionMs: item.transition_ms ?? defaultDurationMs,
    startAt: dateTimeLocal(item.start_at),
    endAt: dateTimeLocal(item.end_at),
    days: item.schedule?.days_of_week || [],
    windowStart: item.schedule?.start_time?.slice(0, 5) || '',
    windowEnd: item.schedule?.end_time?.slice(0, 5) || '',
  }), [item, defaultDurationMs])

  const [form, setForm] = useState(initial)
  // Re-sync when the server hands back a new version of this item, so a save does not
  // leave stale values sitting in an open panel. Adjusting during render rather than in
  // an effect avoids a second render pass; `initial` only changes identity when the
  // query returns a genuinely different item.
  const [syncedFrom, setSyncedFrom] = useState(initial)
  if (syncedFrom !== initial) {
    setSyncedFrom(initial)
    setForm(initial)
  }
  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => setForm((current) => ({ ...current, [key]: value }))

  const effectiveTransition = form.selection === 'inherit' ? defaultTransition : form.selection
  const effectiveMs = form.selection === 'inherit' ? defaultDurationMs : form.transitionMs
  const scheduled = Boolean(form.startAt || form.endAt || form.days.length || form.windowStart || form.windowEnd)
  const dirty = JSON.stringify(form) !== JSON.stringify(initial)

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
    <Card ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} className={cn('border-0 bg-card py-0 ring-1 ring-hairline', isDragging ? 'z-20 opacity-80 shadow-2xl' : 'shadow-[0_1px_2px_rgba(15,23,42,.04)]')}>
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
                <div className="mt-3 flex flex-wrap gap-3 sm:gap-4">
                  <div className="mr-2">
                    <span className="text-muted-foreground mb-2 block text-xs font-medium">Days <span className="text-muted-foreground/70 font-normal">(none = every day)</span></span>
                    <div className="flex gap-1.5">
                      {dayLabels.map((label, day) => (
                        <button key={day} type="button" aria-label={dayNames[day]} aria-pressed={form.days.includes(day)} disabled={!canEdit || saving}
                          onClick={() => set('days', form.days.includes(day) ? form.days.filter((value) => value !== day) : [...form.days, day].sort())}
                          className={cn('focus-visible:ring-ring grid size-9 place-items-center rounded-lg border text-xs font-bold transition-colors focus-visible:ring-2 focus-visible:outline-none', form.days.includes(day) ? 'border-primary bg-primary text-primary-foreground' : 'border-hairline bg-card text-muted-foreground hover:border-border')}>
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <Label htmlFor={`from-${item.id}`} className="text-muted-foreground mb-2 text-xs">From</Label>
                    <Input id={`from-${item.id}`} type="time" value={form.windowStart} onChange={(event) => set('windowStart', event.target.value)} className="w-[120px]" />
                  </div>
                  <div>
                    <Label htmlFor={`until-${item.id}`} className="text-muted-foreground mb-2 text-xs">Until</Label>
                    <Input id={`until-${item.id}`} type="time" value={form.windowEnd} onChange={(event) => set('windowEnd', event.target.value)} className="w-[120px]" />
                  </div>
                </div>
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

export function PlaylistBuilder({ playlistId, showHeader = true }: { playlistId: number; showHeader?: boolean }) {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canEdit = user?.role === 'owner' || user?.role === 'editor'
  const playlistQuery = useQuery({ queryKey: ['playlist', playlistId], queryFn: () => api.getPlaylist(playlistId), enabled: Number.isFinite(playlistId) })
  const contentQuery = useQuery({ queryKey: ['content'], queryFn: api.getContent })
  const [localOrder, setLocalOrder] = useState<number[] | null>(null)
  const [search, setSearch] = useState('')
  const [savingItem, setSavingItem] = useState<number | null>(null)

  const serverItems = useMemo(() => [...(playlistQuery.data?.items || [])].sort((a, b) => a.order - b.order), [playlistQuery.data?.items])
  const items = useMemo(() => {
    if (!localOrder) return serverItems
    const byId = new Map(serverItems.map((item) => [item.id, item]))
    const ordered = localOrder.map((itemId) => byId.get(itemId)).filter((item): item is PlaylistItem => Boolean(item))
    return ordered.length === serverItems.length ? ordered : serverItems
  }, [localOrder, serverItems])
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }))
  const invalidate = () => { queryClient.invalidateQueries({ queryKey: ['playlist', playlistId] }); queryClient.invalidateQueries({ queryKey: ['playlists'] }) }
  const reorderMutation = useMutation({ mutationFn: (orders: number[]) => api.reorderPlaylistItems(playlistId, orders), onSuccess: () => { setLocalOrder(null); invalidate(); toast.success('Order saved') }, onError: (error: Error) => { setLocalOrder(null); toast.error(error.message); playlistQuery.refetch() } })
  const addMutation = useMutation({ mutationFn: (contentId: number) => api.addPlaylistItem(playlistId, contentId, items.length), onSuccess: () => { invalidate(); toast.success('Added to playlist') }, onError: (error: Error) => toast.error(error.message) })
  const removeMutation = useMutation({ mutationFn: (itemId: number) => api.removePlaylistItem(playlistId, itemId), onSuccess: () => { invalidate(); toast.success('Item removed') }, onError: (error: Error) => toast.error(error.message) })
  const updateMutation = useMutation({
    mutationFn: ({ itemId, data }: { itemId: number; data: Parameters<typeof api.updatePlaylistItem>[2] }) => api.updatePlaylistItem(playlistId, itemId, data),
    onMutate: ({ itemId }) => setSavingItem(itemId),
    onSuccess: () => { invalidate(); toast.success('Item settings saved') },
    onError: (error: Error) => toast.error(error.message),
    onSettled: () => setSavingItem(null),
  })
  const transitionMutation = useMutation({
    mutationFn: ({ transition, durationMs, applyToAll }: { transition: TransitionName; durationMs: number; applyToAll: boolean }) => api.updatePlaylistTransitions(playlistId, { transition, transition_ms: durationMs, apply_to_all: applyToAll }),
    onSuccess: (_, variables) => { invalidate(); toast.success(variables.applyToAll ? 'Transition applied to every item' : 'Playlist default saved') },
    onError: (error: Error) => toast.error(error.message),
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
  const availableContent = useMemo(() => (contentQuery.data || []).filter((item) => item.name.toLowerCase().includes(search.toLowerCase()) || item.tags?.toLowerCase().includes(search.toLowerCase())), [contentQuery.data, search])

  if (playlistQuery.isError || contentQuery.isError) return <ErrorState message="The playlist builder could not be loaded." onRetry={() => { playlistQuery.refetch(); contentQuery.refetch() }} />
  if (playlistQuery.isLoading) return <div className="space-y-6"><Skeleton className="h-24" /><div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_340px]"><Skeleton className="h-[520px]" /><Skeleton className="h-[520px]" /></div></div>
  const playlist = playlistQuery.data
  if (!playlist) return null
  const totalDuration = items.reduce((total, item) => total + item.duration, 0)

  return (
    <div className="space-y-8">
      {showHeader && <PageHeader eyebrow="Playlist builder" title={playlist.name} description="Set the loop order, control each handoff, and schedule exactly when every item may play." actions={<div className="flex items-center gap-2"><Badge variant="outline">{items.length} items</Badge><Badge variant="outline">{loopDuration(totalDuration)} loop</Badge>{!canEdit && <Badge variant="warning">View only</Badge>}</div>} />}

      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section aria-labelledby="timeline-title">
          <h2 id="timeline-title" className="mb-4 text-sm font-semibold text-foreground">Playback timeline</h2>
          <DefaultTransitionPanel key={`${playlist.default_transition}-${playlist.default_transition_ms}`} playlist={playlist} disabled={!canEdit} pending={transitionMutation.isPending} onSave={(transition, durationMs, applyToAll) => transitionMutation.mutate({ transition, durationMs, applyToAll })} />
          {!items.length ? <EmptyState icon={ListVideo} title="This playlist has no content" description="Choose an asset from the library to start building the loop." /> : (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={items.map((item) => item.id)} strategy={verticalListSortingStrategy}>
                <div className="space-y-3">{items.map((item) => <ItemRow key={item.id} item={item} defaultTransition={playlist.default_transition} defaultDurationMs={playlist.default_transition_ms} canEdit={canEdit} saving={savingItem === item.id} onRemove={() => removeMutation.mutate(item.id)} onSave={(data) => updateMutation.mutate({ itemId: item.id, data })} />)}</div>
              </SortableContext>
            </DndContext>
          )}
        </section>

        <aside className="rounded-2xl bg-card p-4 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1 ring-hairline xl:sticky xl:top-6" aria-labelledby="library-title">
          <div className="flex items-center justify-between"><div><h2 id="library-title" className="font-semibold text-foreground">Content library</h2><p className="mt-1 text-xs text-muted-foreground/70">{availableContent.length} assets available</p></div><Badge variant="secondary">Add to loop</Badge></div>
          <div className="relative mt-4"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground/70" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search assets…" className="pl-9" aria-label="Search library" /></div>
          <div className="mt-4 max-h-[660px] space-y-2 overflow-y-auto pr-1">
            {contentQuery.isLoading ? Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} className="h-20" />) : availableContent.map((content) => <div key={content.id} className="flex items-center gap-3 rounded-xl border border-hairline p-2.5 hover:bg-muted"><div className="relative size-12 shrink-0"><MediaThumbnail item={content} className="size-12 rounded-lg" />{clipDuration(content.duration_ms) && <span className="absolute right-0 bottom-0 rounded bg-black/75 px-1 text-[9px] font-semibold text-white">{clipDuration(content.duration_ms)}</span>}</div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-foreground">{content.name}</p><p className="mt-0.5 text-xs text-muted-foreground/70"><span className="capitalize">{content.type}</span>{assetOrientation(content.renditions) && ` • ${assetOrientation(content.renditions)}`}{clipDuration(content.duration_ms) && ` • ${clipDuration(content.duration_ms)}`}</p></div><Button size="icon-sm" variant="outline" disabled={!canEdit || addMutation.isPending} onClick={() => addMutation.mutate(content.id)} aria-label={`Add ${content.name}`}><Plus /></Button></div>)}
            {!availableContent.length && <div className="py-10 text-center"><Search className="mx-auto size-5 text-muted-foreground/40" /><p className="mt-2 text-sm text-muted-foreground/70">No matching assets</p></div>}
          </div>
        </aside>
      </div>
    </div>
  )
}
