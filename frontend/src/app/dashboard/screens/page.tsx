'use client'

import { useMemo, useState, useSyncExternalStore } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { LayoutGrid, Layers3, List, ListVideo, MonitorPlay, Search, Settings2, Tv2 } from 'lucide-react'
import { toast } from 'sonner'
import { AssetCard, AssetGrid, OverlayBadge } from '@/components/dashboard/asset-card'
import { BulkActionBar, SelectAllCheckbox } from '@/components/dashboard/bulk-action-bar'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { ListToolbar, commonSorts, sortItems, type CommonSort } from '@/components/dashboard/list-toolbar'
import { StatusIndicator } from '@/components/dashboard/status-indicator'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useBulkSelection } from '@/hooks/use-bulk-selection'
import { api } from '@/lib/api'
import { relativeTime } from '@/lib/format'
import { useAuthStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import type { Screen, ScreenGroup } from '@/lib/types'

type StatusFilter = 'all' | 'online' | 'offline'
type ViewMode = 'cards' | 'list'
const VIEW_KEY = 'olrac.screens.view'
const VIEW_EVENT = 'olrac:screens-view'

/**
 * The saved layout choice, read from localStorage without a render-time side effect.
 *
 * useSyncExternalStore gives the server (and the hydration pass) the "cards" default and
 * the client the stored value, so there is no markup mismatch and no setState in an
 * effect — the same approach the theme toggle uses.
 */
function useStoredView(): ViewMode {
  return useSyncExternalStore(
    (onChange) => {
      window.addEventListener(VIEW_EVENT, onChange)
      window.addEventListener('storage', onChange)
      return () => {
        window.removeEventListener(VIEW_EVENT, onChange)
        window.removeEventListener('storage', onChange)
      }
    },
    () => (window.localStorage.getItem(VIEW_KEY) === 'list' ? 'list' : 'cards'),
    () => 'cards',
  )
}

export default function ScreensPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canEdit = user?.role === 'owner' || user?.role === 'editor'

  // Screens report in on their own cadence; a slow poll keeps the wall of thumbnails
  // roughly live without hammering the API at 500 screens.
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens, refetchInterval: 30000 })
  const groupsQuery = useQuery({ queryKey: ['groups'], queryFn: api.getGroups })
  const playlistsQuery = useQuery({ queryKey: ['playlists'], queryFn: api.getPlaylists })

  const screens = useMemo(() => screensQuery.data || [], [screensQuery.data])
  const groups = useMemo(() => (groupsQuery.data || []) as ScreenGroup[], [groupsQuery.data])
  const playlists = playlistsQuery.data || []

  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<CommonSort>('newest')
  const [status, setStatus] = useState<StatusFilter>('all')
  const view = useStoredView()
  const [pairOpen, setPairOpen] = useState(false)
  const [pairCode, setPairCode] = useState('')

  const chooseView = (next: ViewMode) => {
    window.localStorage.setItem(VIEW_KEY, next)
    // Notify this tab: the storage event only fires in *other* tabs.
    window.dispatchEvent(new Event(VIEW_EVENT))
  }

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    const matches = screens.filter((screen: Screen) => {
      const label = (screen.name || `Screen ${screen.id}`).toLowerCase()
      const matchesSearch = !term || label.includes(term) || String(screen.device_id || '').toLowerCase().includes(term)
      const matchesStatus = status === 'all' || (status === 'online' ? screen.status === 'online' : screen.status !== 'online')
      return matchesSearch && matchesStatus
    })
    return sortItems(matches, sort, (s) => s.name || `Screen ${s.id}`, (s) => s.last_seen)
  }, [screens, search, sort, status])

  const bulk = useBulkSelection(filtered)
  const groupName = (id: number | null) => groups.find((g) => g.id === id)?.name

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['screens'] })
    queryClient.invalidateQueries({ queryKey: ['groups'] })
  }
  const fail = (error: Error) => toast.error(error.message)

  const pairMutation = useMutation({
    mutationFn: api.pairScreen,
    onSuccess: () => { refresh(); toast.success('Screen paired'); setPairOpen(false); setPairCode('') },
    onError: fail,
  })

  // Sequential rather than parallel: 80 simultaneous writes to the same rows is how you
  // turn a bulk action into a pile of lock timeouts.
  const bulkAssign = useMutation({
    mutationFn: async (playlistId: number) => {
      for (const id of bulk.selected) await api.assignPlaylist(id, playlistId)
    },
    onSuccess: () => { refresh(); toast.success(`Playlist assigned to ${bulk.selected.length} screens`); bulk.clear() },
    onError: fail,
  })

  const bulkGroup = useMutation({
    mutationFn: async (groupId: number) => {
      for (const id of bulk.selected) await api.patchScreen(id, { group_id: groupId })
    },
    onSuccess: () => { refresh(); toast.success(`Moved ${bulk.selected.length} screens`); bulk.clear() },
    onError: fail,
  })

  const addScreen = (
    <Dialog open={pairOpen} onOpenChange={setPairOpen}>
      <DialogTrigger render={<Button variant="outline" className="bg-card" />}>Add Screen</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add a screen</DialogTitle>
          <DialogDescription>
            Open Olrac on the TV and sign in with your account — it joins this workspace on its own. No keyboard on hand? Type the six-digit code it shows.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <div className="space-y-2">
            <Label htmlFor="pair-code">Pairing code</Label>
            <Input
              id="pair-code"
              value={pairCode}
              onChange={(event) => setPairCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              inputMode="numeric"
              autoFocus
              className="text-center font-mono text-2xl tracking-[0.4em]"
            />
          </div>
          <Button className="w-full" disabled={pairCode.length !== 6 || pairMutation.isPending} onClick={() => pairMutation.mutate(pairCode)}>
            {pairMutation.isPending ? 'Pairing…' : 'Pair screen'}
          </Button>
          <p className="text-muted-foreground text-center text-xs">
            Rolling out many screens? <Link href="/dashboard/provisioning" className="text-primary dark:text-brand underline underline-offset-2">Use zero-touch provisioning</Link>
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )

  const viewToggle = (
    <div className="border-hairline bg-card flex items-center rounded-lg border p-0.5" role="group" aria-label="Layout">
      {([['cards', LayoutGrid, 'Card view'], ['list', List, 'List view']] as const).map(([mode, Icon, label]) => (
        <button
          key={mode}
          onClick={() => chooseView(mode)}
          aria-label={label}
          aria-pressed={view === mode}
          className={cn(
            'grid size-8 cursor-pointer place-items-center rounded-md transition-colors',
            view === mode ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground',
          )}
        >
          <Icon className="size-4" aria-hidden="true" />
        </button>
      ))}
    </div>
  )

  if (screensQuery.isError) {
    return <ErrorState message="Your screens could not be loaded." onRetry={() => screensQuery.refetch()} />
  }

  return (
    <div>
      <ListToolbar
        title="Screens"
        action={canEdit ? addScreen : undefined}
        menu={viewToggle}
        sort={{ value: sort, onChange: setSort, options: commonSorts }}
        search={{ value: search, onChange: setSearch }}
        filters={
          <>
            {(['all', 'online', 'offline'] as const).map((value) => (
              <DropdownMenuItem key={value} onClick={() => setStatus(value)} className={status === value ? 'bg-accent font-medium' : undefined}>
                <span className="capitalize">{value === 'all' ? 'All screens' : value}</span>
              </DropdownMenuItem>
            ))}
          </>
        }
      />

      {canEdit && filtered.length > 0 && (
        <div className="mb-3 flex items-center gap-4">
          <SelectAllCheckbox
            checked={bulk.allVisibleSelected}
            indeterminate={bulk.someVisibleSelected}
            onChange={bulk.toggleAll}
            label={`Select all ${filtered.length}`}
          />
        </div>
      )}

      {canEdit && (
        <BulkActionBar count={bulk.selected.length} noun="screen" onClear={bulk.clear}>
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button size="sm" variant="outline" />}>
              <ListVideo data-icon="inline-start" /> Assign playlist
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              {playlists.length === 0 && <p className="text-muted-foreground px-3 py-2 text-sm">No playlists yet</p>}
              {playlists.map((playlist) => (
                <DropdownMenuItem key={playlist.id} onClick={() => bulkAssign.mutate(playlist.id)}>
                  {playlist.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger render={<Button size="sm" variant="outline" />}>
              <Layers3 data-icon="inline-start" /> Add to group
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              {groups.length === 0 && <p className="text-muted-foreground px-3 py-2 text-sm">No groups yet</p>}
              {groups.map((group) => (
                <DropdownMenuItem key={group.id} onClick={() => bulkGroup.mutate(group.id)}>
                  {group.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </BulkActionBar>
      )}

      {screensQuery.isLoading ? (
        <AssetGrid>{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-64 rounded-xl" />)}</AssetGrid>
      ) : !screens.length ? (
        <EmptyState
          icon={Tv2}
          title="No screens yet"
          description="Open Olrac on a TV and sign in with your account — the screen joins this workspace on its own."
          action={canEdit ? <Button onClick={() => setPairOpen(true)}>Add Screen</Button> : undefined}
        />
      ) : !filtered.length ? (
        <EmptyState
          icon={Search}
          title="No matching screens"
          description="Try a different search term or clear the status filter."
          action={<Button variant="outline" onClick={() => { setSearch(''); setStatus('all') }}>Clear filters</Button>}
        />
      ) : view === 'list' ? (
        <div className="ring-hairline divide-hairline bg-card grid grid-cols-1 divide-y overflow-hidden rounded-xl ring-1">
          {filtered.map((screen: Screen) => {
            const label = screen.name || `Screen ${screen.id}`
            return (
              <div key={screen.id} className="hover:bg-muted/40 flex items-center gap-3 p-3">
                {canEdit && (
                  <input
                    type="checkbox"
                    className="accent-primary size-4 shrink-0"
                    checked={bulk.isSelected(screen.id)}
                    onChange={(event) => bulk.toggle(screen.id, event.target.checked)}
                    aria-label={`Select ${label}`}
                  />
                )}
                <div className="bg-muted h-9 w-16 shrink-0 overflow-hidden rounded">
                  {screen.latest_screenshot ? (
                    // eslint-disable-next-line @next/next/no-img-element -- player uploads are arbitrary remote URLs
                    <img src={screen.latest_screenshot} alt="" className="size-full object-cover" />
                  ) : (
                    <div className="text-muted-foreground/40 grid size-full place-items-center"><MonitorPlay className="size-4" /></div>
                  )}
                </div>
                <Link href={`/dashboard/screens/${screen.id}`} className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-sm font-medium">{label}</p>
                  <p className="text-muted-foreground truncate text-xs">
                    {screen.status === 'online' ? 'Online now' : `Last seen ${relativeTime(screen.last_seen)}`}
                    {groupName(screen.group_id) && ` · ${groupName(screen.group_id)}`}
                  </p>
                </Link>
                {screen.app_version && <Badge variant="outline" className="hidden sm:inline-flex">v{screen.app_version}</Badge>}
                <StatusIndicator status={screen.status} />
              </div>
            )
          })}
        </div>
      ) : (
        <AssetGrid>
          {filtered.map((screen: Screen) => {
            const label = screen.name || `Screen ${screen.id}`
            const online = screen.status === 'online'
            return (
              <div key={screen.id} className="relative">
                {canEdit && (
                  <label className="absolute top-2.5 right-2.5 z-10 grid size-7 cursor-pointer place-items-center rounded-md bg-black/50 backdrop-blur">
                    <input
                      type="checkbox"
                      className="accent-primary size-4"
                      checked={bulk.isSelected(screen.id)}
                      onChange={(event) => bulk.toggle(screen.id, event.target.checked)}
                      aria-label={`Select ${label}`}
                    />
                  </label>
                )}
                <AssetCard
                  href={`/dashboard/screens/${screen.id}`}
                  title={label}
                  subtitle={online ? 'Online now' : `Last seen ${relativeTime(screen.last_seen)}`}
                  preview={
                    screen.latest_screenshot ? (
                      // eslint-disable-next-line @next/next/no-img-element -- player uploads are arbitrary remote URLs
                      <img src={screen.latest_screenshot} alt={`What ${label} is showing`} className="size-full object-cover" />
                    ) : (
                      <div className="text-muted-foreground/40 grid size-full place-items-center">
                        <MonitorPlay className="size-9" aria-hidden="true" />
                      </div>
                    )
                  }
                  badges={<OverlayBadge tone={online ? 'online' : 'offline'}>{online ? 'Online' : 'Offline'}</OverlayBadge>}
                  menu={
                    <>
                      <DropdownMenuItem render={<Link href={`/dashboard/screens/${screen.id}`} />}>
                        <Settings2 aria-hidden="true" /> Open screen
                      </DropdownMenuItem>
                      <DropdownMenuItem render={<Link href="/dashboard/groups" />}>
                        <Layers3 aria-hidden="true" /> Manage groups
                      </DropdownMenuItem>
                    </>
                  }
                />
              </div>
            )
          })}
        </AssetGrid>
      )}
    </div>
  )
}
