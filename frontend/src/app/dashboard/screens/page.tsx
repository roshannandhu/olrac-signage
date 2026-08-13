'use client'

import { useMemo, useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { AlertTriangle, CirclePause, CirclePlay, FolderPlus, Layers3, MonitorPlay, Plus, Radio, Tv2 } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { PageHeader } from '@/components/dashboard/page-header'
import { StatusIndicator } from '@/components/dashboard/status-indicator'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { api, WS_BASE } from '@/lib/api'
import { relativeTime } from '@/lib/format'
import { useAuthStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import type { Playlist, Screen, ScreenGroup } from '@/lib/types'

function PlaylistSelect({ value, playlists, disabled, includeInherited, onChange }: {
  value: number | null
  playlists: Playlist[]
  disabled: boolean
  includeInherited?: boolean
  onChange: (value: number | null) => void
}) {
  return (
    <Select value={value ? String(value) : includeInherited ? 'inherit' : null} disabled={disabled} onValueChange={(next: string | null) => onChange(next && next !== 'inherit' ? Number(next) : null)}>
      <SelectTrigger className="w-full bg-card" aria-label="Assign playlist">
        <SelectValue>{(selected: string | null) => {
          if (selected === 'inherit') return 'Use group playlist'
          return playlists.find((playlist) => String(playlist.id) === selected)?.name || 'Select playlist'
        }}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {includeInherited && <SelectItem value="inherit">Use group playlist</SelectItem>}
        {playlists.map((playlist) => <SelectItem key={playlist.id} value={String(playlist.id)}>{playlist.name}</SelectItem>)}
      </SelectContent>
    </Select>
  )
}

function ScreenCard({ screen, group, groups, playlists, canEdit, onAssign, onUpdate, onRevoke, index = 0 }: {
  screen: Screen
  group?: ScreenGroup
  groups: ScreenGroup[]
  playlists: Playlist[]
  canEdit: boolean
  onAssign: (screenId: number, playlistId: number | null) => void
  onUpdate: (screenId: number, data: { name: string, group_id: number | null }) => void
  onRevoke: (screenId: number) => void
  index?: number
}) {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [editName, setEditName] = useState(screen.name || '')
  const [editGroup, setEditGroup] = useState<number | null>(screen.group_id)
  const [confirmingRevoke, setConfirmingRevoke] = useState(false)

  const effective = playlists.find((playlist) => playlist.id === screen.effective_playlist_id)
  const currentItem = playlists.flatMap((playlist) => playlist.items).find((item) => item.id === screen.current_item_id)
  const isReachable = screen.status === 'online'
  const stateLabel = !isReachable ? 'Offline' : screen.playback_state === 'playing' ? 'Playing' : screen.playback_state === 'error' ? 'Error' : 'Idle'
  const StateIcon = !isReachable || screen.playback_state === 'idle' ? CirclePause : screen.playback_state === 'error' ? AlertTriangle : CirclePlay
  
  // A device is considered "Enrolled" if it has an installation_id (added during token enrollment) or if we want to just base it on legacy vs new. 
  // For UI, we'll label it as Enrolled if it's not waiting_pairing.
  const isEnrolled = screen.status !== 'waiting_pairing'
  
  return (
    <Card style={{ '--i': index } as React.CSSProperties} className="lift ring-hairline bg-card border-0 py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1 hover:shadow-[0_14px_40px_rgba(15,23,42,.08)]">
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <span className={`grid size-11 shrink-0 place-items-center rounded-xl ${isReachable ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-muted text-muted-foreground/70'}`}>
            <MonitorPlay className="size-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="truncate font-semibold text-foreground flex items-center gap-2">
                  <Link href={`/dashboard/screens/${screen.id}`} className="hover:underline">
                    {screen.name || `Screen ${screen.id}`}
                  </Link>
                  <Badge variant="secondary" className="text-[10px] uppercase font-bold tracking-wider">{isEnrolled ? 'Enrolled' : 'Paired'}</Badge>
                </h3>
                <p className="mt-1 text-xs text-muted-foreground/70">Seen {relativeTime(screen.last_seen)}</p>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-2">
                <StatusIndicator status={screen.status} />
                <Badge
                  variant="outline"
                  title={screen.last_error || undefined}
                  className={!isReachable ? 'text-muted-foreground' : screen.playback_state === 'playing' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' : screen.playback_state === 'error' ? 'border-destructive/30 bg-destructive/10 text-destructive' : 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300'}
                >
                  <StateIcon className="size-3" /> {stateLabel}
                </Badge>
                
                {canEdit && (
                  <Dialog open={settingsOpen} onOpenChange={(open) => {
                    setSettingsOpen(open)
                    setConfirmingRevoke(false)
                    if (open) {
                      setEditName(screen.name || '')
                      setEditGroup(screen.group_id)
                    }
                  }}>
                    <DialogTrigger render={<Button variant="ghost" size="icon" className="h-6 w-6 -mr-2 text-muted-foreground hover:text-foreground"><Radio className="size-4" /></Button>} />
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Screen Settings</DialogTitle>
                        <DialogDescription>Manage {screen.name || `Screen ${screen.id}`}</DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4 pt-4">
                        <div className="space-y-2">
                          <Label>Screen Name</Label>
                          <Input value={editName} onChange={(e) => setEditName(e.target.value)} placeholder="e.g. Lobby TV" />
                        </div>
                        <div className="space-y-2">
                          <Label>Screen Group</Label>
                          <Select value={editGroup ? String(editGroup) : 'none'} onValueChange={(val) => setEditGroup(val === 'none' ? null : Number(val))}>
                            <SelectTrigger>
                              {/* Without this function Base UI shows the raw value —
                                  here a bare group id, or the literal "none". */}
                              <SelectValue>{(value: string | null) => {
                                if (!value || value === 'none') return 'Ungrouped'
                                return groups.find((group) => String(group.id) === value)?.name || 'Ungrouped'
                              }}</SelectValue>
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">Ungrouped</SelectItem>
                              {groups.map(g => <SelectItem key={g.id} value={String(g.id)}>{g.name}</SelectItem>)}
                            </SelectContent>
                          </Select>
                        </div>
                        <Button className="w-full" onClick={() => {
                          onUpdate(screen.id, { name: editName, group_id: editGroup })
                          setSettingsOpen(false)
                        }}>Save Changes</Button>
                        
                        <div className="mt-8 pt-4 border-t border-hairline">
                          <h4 className="text-sm font-semibold text-destructive mb-2">Danger zone</h4>
                          {/* Inline two-step rather than window.confirm: a native modal blocks
                              the whole tab and cannot be styled or dismissed with the dialog. */}
                          {confirmingRevoke ? (
                            <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-3">
                              <p className="text-sm text-foreground">Revoke this device&apos;s access?</p>
                              <p className="mt-1 text-xs text-muted-foreground">It goes offline immediately and has to be enrolled again before it can play anything.</p>
                              <div className="mt-3 flex gap-2">
                                <Button variant="outline" size="sm" className="flex-1" onClick={() => setConfirmingRevoke(false)}>Cancel</Button>
                                <Button variant="destructive" size="sm" className="flex-1" onClick={() => {
                                  onRevoke(screen.id)
                                  setConfirmingRevoke(false)
                                  setSettingsOpen(false)
                                }}>Revoke access</Button>
                              </div>
                            </div>
                          ) : (
                            <Button variant="outline" className="w-full text-destructive border-destructive/30 hover:bg-destructive/10" onClick={() => setConfirmingRevoke(true)}>
                              Revoke device access
                            </Button>
                          )}
                        </div>
                      </div>
                    </DialogContent>
                  </Dialog>
                )}
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 rounded-xl bg-muted p-3 text-xs">
              <div><p className="text-muted-foreground/70">Now playing</p><p className="mt-1 truncate font-semibold text-foreground">{currentItem?.content.name || (screen.playback_state === 'idle' ? 'Idle' : 'Awaiting telemetry')}</p><p className="mt-0.5 truncate text-[11px] text-muted-foreground">{effective?.name || 'No playlist'}</p></div>
              <div><p className="text-muted-foreground/70">Player</p><p className="mt-1 font-semibold text-foreground">{screen.app_version || screen.device_version || 'Version unknown'}</p>{screen.last_error && <p className="mt-1 truncate text-[11px] text-destructive" title={screen.last_error}>Last error: {screen.last_error}</p>}</div>
            </div>
            <div className="mt-4">
              <Label className="mb-2 text-xs text-muted-foreground">Playlist override</Label>
              <PlaylistSelect value={screen.playlist_id} playlists={playlists} disabled={!canEdit} includeInherited={Boolean(group)} onChange={(playlistId) => onAssign(screen.id, playlistId)} />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function ScreensPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canEdit = user?.role === 'owner' || user?.role === 'editor'
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens, refetchInterval: 30_000 })
  const playlistsQuery = useQuery({ queryKey: ['playlists'], queryFn: api.getPlaylists })
  const groupsQuery = useQuery({ queryKey: ['groups'], queryFn: api.getGroups })
  const screens = useMemo(() => screensQuery.data || [], [screensQuery.data])
  const playlists = playlistsQuery.data || []
  const groups = useMemo(() => groupsQuery.data || [], [groupsQuery.data])
  const alerts = useMemo(() => screens.filter((screen) => {
    const offlineForMs = screensQuery.dataUpdatedAt - new Date(screen.last_seen).getTime()
    return screen.playback_state === 'error' || (screen.status === 'offline' && offlineForMs > 30 * 60 * 1000)
  }), [screens, screensQuery.dataUpdatedAt])

  useEffect(() => {
    const token = useAuthStore.getState().token
    if (!token) return

    // The browser WebSocket API cannot set an Authorization header, so the backend
    // takes the token as a query param. WS_BASE is derived from the API origin —
    // window.location points at Next.js, where this route does not exist.
    const ws = new WebSocket(`${WS_BASE}/ws/dashboard/ws?token=${encodeURIComponent(token)}`)
    
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'playback_progress') {
          // You could update specific screen progress in the query client cache here
          // For now, we rely on the normal 30s refetch, or we can force a refetch if needed
          // But to avoid spamming the backend, we just update the cache directly if we want
          queryClient.setQueryData(['screens'], (oldData: Screen[] | undefined) => {
            if (!oldData) return oldData
            return oldData.map(s => {
              if (s.id === msg.screen_id) {
                return { ...s, playback_state: 'playing', current_item_id: msg.item_id }
              }
              return s
            })
          })
        }
      } catch {
        // ignore parsing error
      }
    }
    
    return () => {
      ws.close()
    }
  }, [queryClient])

  // Screens are shown by group by default, which mirrors how playlists are published.
  // But once every screen belongs to a group there is no way to see the whole fleet at
  // once or find one display by name, so a flat view is the other half of this page.
  const [view, setView] = useState<'groups' | 'all'>('groups')
  const [screenSearch, setScreenSearch] = useState('')
  const [pairOpen, setPairOpen] = useState(false)
  const [pairCode, setPairCode] = useState('')
  const [groupOpen, setGroupOpen] = useState(false)
  const [groupName, setGroupName] = useState('')
  const [selectedScreens, setSelectedScreens] = useState<number[]>([])

  const pairMutation = useMutation({
    mutationFn: api.pairScreen,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['screens'] }); toast.success('Screen paired'); setPairOpen(false); setPairCode('') },
    onError: (error: Error) => toast.error(error.message),
  })
  const createGroupMutation = useMutation({
    mutationFn: async () => {
      const group = await api.createGroup(groupName.trim())
      if (selectedScreens.length) await api.setGroupScreens(group.id, selectedScreens)
      return group
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['groups'] }); queryClient.invalidateQueries({ queryKey: ['screens'] })
      toast.success('Screen group created'); setGroupOpen(false); setGroupName(''); setSelectedScreens([])
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const directAssignMutation = useMutation({
    mutationFn: ({ screenId, playlistId }: { screenId: number; playlistId: number | null }) => playlistId ? api.assignPlaylist(screenId, playlistId) : api.clearScreenAssignment(screenId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['screens'] }); toast.success('Screen assignment updated') },
    onError: (error: Error) => toast.error(error.message),
  })
  const groupAssignMutation = useMutation({
    mutationFn: ({ groupId, playlistId }: { groupId: number; playlistId: number }) => api.assignGroupPlaylist(groupId, playlistId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['groups'] }); queryClient.invalidateQueries({ queryKey: ['screens'] }); toast.success('Playlist published to group') },
    onError: (error: Error) => toast.error(error.message),
  })

  const updateScreenMutation = useMutation({
    mutationFn: ({ id, data }: { id: number, data: { name: string, group_id: number | null } }) => api.patchScreen(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['screens'] }); toast.success('Screen updated') },
    onError: (error: Error) => toast.error(error.message),
  })

  const revokeScreenMutation = useMutation({
    mutationFn: api.revokeScreenDeviceSecret,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['screens'] }); toast.success('Device revoked') },
    onError: (error: Error) => toast.error(error.message),
  })

  const groupedScreens = useMemo(() => {
    const result = new Map<number | null, Screen[]>()
    groups.forEach((group) => result.set(group.id, []))
    result.set(null, [])
    screens.forEach((screen) => (result.get(screen.group_id) || result.get(null))?.push(screen))
    return result
  }, [groups, screens])

  const groupNameById = useMemo(
    () => new Map(groups.map((group) => [group.id, group.name])),
    [groups],
  )

  const filteredScreens = useMemo(() => {
    const term = screenSearch.trim().toLowerCase()
    if (!term) return screens
    return screens.filter((screen) => {
      const groupName = screen.group_id ? groupNameById.get(screen.group_id) || '' : ''
      return (
        (screen.name || `Screen ${screen.id}`).toLowerCase().includes(term) ||
        (screen.device_id || '').toLowerCase().includes(term) ||
        groupName.toLowerCase().includes(term)
      )
    })
  }, [screens, screenSearch, groupNameById])

  if (screensQuery.isError || playlistsQuery.isError || groupsQuery.isError) {
    return <ErrorState message="Screens and groups could not be loaded." onRetry={() => { screensQuery.refetch(); playlistsQuery.refetch(); groupsQuery.refetch() }} />
  }

  const actions = canEdit ? <>
    <Dialog open={groupOpen} onOpenChange={setGroupOpen}>
      <DialogTrigger render={<Button variant="outline" className="bg-card" />}><FolderPlus data-icon="inline-start" /> New group</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Create screen group</DialogTitle><DialogDescription>Group displays by location or purpose, then publish once to reach all of them.</DialogDescription></DialogHeader>
        <div className="space-y-5 pt-2">
          <div className="space-y-2"><Label htmlFor="group-name">Group name</Label><Input id="group-name" value={groupName} onChange={(event) => setGroupName(event.target.value)} placeholder="Reception screens" /></div>
          <fieldset><legend className="text-sm font-medium">Add screens</legend><div className="mt-2 max-h-52 space-y-2 overflow-y-auto rounded-xl border border-hairline p-2">
            {screens.map((screen) => <label key={screen.id} className="flex cursor-pointer items-center gap-3 rounded-lg p-2.5 text-sm hover:bg-muted"><input type="checkbox" className="size-4 accent-primary" checked={selectedScreens.includes(screen.id)} onChange={(event) => setSelectedScreens((current) => event.target.checked ? [...current, screen.id] : current.filter((id) => id !== screen.id))} /><span className="flex-1">{screen.name || `Screen ${screen.id}`}</span>{screen.group_id && <Badge variant="secondary">Will move</Badge>}</label>)}
            {!screens.length && <p className="p-3 text-sm text-muted-foreground/70">Pair a screen first, or create the empty group now.</p>}
          </div></fieldset>
          <Button className="w-full" disabled={!groupName.trim() || createGroupMutation.isPending} onClick={() => createGroupMutation.mutate()}>{createGroupMutation.isPending ? 'Creating…' : 'Create group'}</Button>
        </div>
      </DialogContent>
    </Dialog>
    <Dialog open={pairOpen} onOpenChange={(open) => { setPairOpen(open); if (!open) setPairCode('') }}>
      <DialogTrigger render={<Button />}><Plus data-icon="inline-start" /> Pair screen</DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Pair a new screen</DialogTitle><DialogDescription>Enter the six-digit code currently shown by the OLRAC player.</DialogDescription></DialogHeader>
        <div className="space-y-4 pt-2"><div className="space-y-2"><Label htmlFor="pair-code">Pairing code</Label><Input id="pair-code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={pairCode} onChange={(event) => setPairCode(event.target.value.replace(/\D/g, ''))} placeholder="000000" className="h-14 text-center font-mono text-2xl tracking-[0.35em]" /></div><Button className="w-full" disabled={pairCode.length !== 6 || pairMutation.isPending} onClick={() => pairMutation.mutate(pairCode)}>{pairMutation.isPending ? 'Pairing…' : 'Pair screen'}</Button></div>
      </DialogContent>
    </Dialog>
  </> : <Badge variant="outline">View only</Badge>

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Fleet management" title="Screens" description="See what is live, organize displays into groups, and publish a playlist across an entire location in one action." actions={actions} />

      {alerts.length > 0 && <section aria-labelledby="fleet-alerts" className="rounded-2xl border border-destructive/20 bg-destructive/5 p-4">
        <div className="flex items-center gap-2 text-destructive"><AlertTriangle className="size-4" /><h2 id="fleet-alerts" className="text-sm font-semibold">Fleet alerts</h2></div>
        <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          {alerts.map((screen) => <li key={screen.id} className="rounded-xl bg-card/80 px-3 py-2"><span className="font-medium text-foreground">{screen.name || `Screen ${screen.id}`}</span><span className="ml-2 text-muted-foreground">{screen.playback_state === 'error' ? screen.last_error || 'Playback error' : `Offline since ${relativeTime(screen.last_seen)}`}</span></li>)}
        </ul>
      </section>}

      {screens.length > 0 && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div role="tablist" aria-label="Screen view" className="border-hairline inline-flex rounded-xl border p-1">
            {([['groups', 'By group'], ['all', `All screens (${screens.length})`]] as const).map(([value, label]) => (
              <button
                key={value}
                role="tab"
                aria-selected={view === value}
                onClick={() => setView(value)}
                className={cn(
                  'focus-visible:ring-ring cursor-pointer rounded-lg px-4 py-1.5 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none',
                  view === value ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {label}
              </button>
            ))}
          </div>
          {view === 'all' && (
            <Input
              value={screenSearch}
              onChange={(event) => setScreenSearch(event.target.value)}
              placeholder="Search by screen, device id or group…"
              aria-label="Search screens"
              className="bg-card w-full sm:max-w-xs"
            />
          )}
        </div>
      )}

      {screensQuery.isLoading ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-72" />)}</div> : !screens.length && !groups.length ? (
        <EmptyState icon={Tv2} title="No screens yet" description="Open OLRAC on a TV and sign in with your account — the screen joins this workspace on its own. No keyboard on hand? Use the six-digit code it can show instead." action={canEdit ? <Button onClick={() => setPairOpen(true)}><Radio data-icon="inline-start" /> Pair with a code</Button> : undefined} />
      ) : view === 'all' ? (
        filteredScreens.length === 0 ? (
          <EmptyState
            icon={Tv2}
            title="No screens match that search"
            description="Try a different name, device id, or group."
            action={<Button variant="outline" onClick={() => setScreenSearch('')}>Clear search</Button>}
          />
        ) : (
          <div className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredScreens.map((screen, index) => (
              <ScreenCard
                key={screen.id}
                index={index}
                screen={screen}
                group={groups.find((g) => g.id === screen.group_id)}
                groups={groups}
                playlists={playlists}
                canEdit={canEdit}
                onUpdate={(id, data) => updateScreenMutation.mutate({ id, data })}
                onRevoke={(id) => revokeScreenMutation.mutate(id)}
                onAssign={(screenId, playlistId) => directAssignMutation.mutate({ screenId, playlistId })}
              />
            ))}
          </div>
        )
      ) : (
        <div className="space-y-8">
          {groups.map((group) => {
            const members = groupedScreens.get(group.id) || []
            return <section key={group.id} aria-labelledby={`group-${group.id}`}>
              <div className="mb-4 flex flex-col gap-3 rounded-2xl border border-hairline bg-card/70 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary dark:text-brand"><Layers3 className="size-5" /></span><div><h2 id={`group-${group.id}`} className="font-semibold text-foreground">{group.name}</h2><p className="text-xs text-muted-foreground/70">{members.length} screen{members.length === 1 ? '' : 's'}</p></div></div>
                <div className="w-full sm:w-72"><PlaylistSelect value={group.playlist_id} playlists={playlists} disabled={!canEdit || groupAssignMutation.isPending} onChange={(playlistId) => playlistId && groupAssignMutation.mutate({ groupId: group.id, playlistId })} /></div>
              </div>
              {members.length ? <div className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-3">{members.map((screen, index) => <ScreenCard key={screen.id} index={index} screen={screen} group={group} groups={groups} playlists={playlists} canEdit={canEdit} onUpdate={(id, data) => updateScreenMutation.mutate({ id, data })} onRevoke={(id) => revokeScreenMutation.mutate(id)} onAssign={(screenId, playlistId) => directAssignMutation.mutate({ screenId, playlistId })} />)}</div> : <div className="rounded-2xl border border-dashed border-border px-5 py-8 text-center text-sm text-muted-foreground/70">This group is ready for screens.</div>}
            </section>
          })}

          {(groupedScreens.get(null)?.length || 0) > 0 && <section aria-labelledby="ungrouped"><div className="mb-4"><h2 id="ungrouped" className="font-semibold text-foreground">Ungrouped screens</h2><p className="mt-1 text-sm text-muted-foreground">Displays managed individually.</p></div><div className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-3">{groupedScreens.get(null)?.map((screen, index) => <ScreenCard key={screen.id} index={index} screen={screen} groups={groups} playlists={playlists} canEdit={canEdit} onUpdate={(id, data) => updateScreenMutation.mutate({ id, data })} onRevoke={(id) => revokeScreenMutation.mutate(id)} onAssign={(screenId, playlistId) => directAssignMutation.mutate({ screenId, playlistId })} />)}</div></section>}
        </div>
      )}
    </div>
  )
}
