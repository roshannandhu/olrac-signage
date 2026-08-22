'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Package, PackagePlus, Rocket } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { PageHeader } from '@/components/dashboard/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { api } from '@/lib/api'
import type { RolloutState } from '@/lib/types'
import { relativeTime } from '@/lib/format'
import { useAuthStore } from '@/lib/store'

export default function ReleasesPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  // Pinning a screen to a build is a tenant action: it affects only that screen.
  const canPin = user?.role === 'owner' || user?.role === 'editor'
  // Publishing and promoting are platform actions: a release installs across every
  // tenant's fleet, so an organisation owner must not be able to do either.
  const canPublish = user?.role === 'super_admin'

  const [publishOpen, setPublishOpen] = useState(false)
  const [versionCode, setVersionCode] = useState('')
  const [versionName, setVersionName] = useState('')
  const [apkUrl, setApkUrl] = useState('')
  const [sha256, setSha256] = useState('')

  const releasesQuery = useQuery({ queryKey: ['releases'], queryFn: api.getReleases })
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens })

  const createMutation = useMutation({
    mutationFn: api.createRelease,
    onSuccess: () => {
      toast.success('Release published')
      queryClient.invalidateQueries({ queryKey: ['releases'] })
      setPublishOpen(false)
      setVersionCode(''); setVersionName(''); setApkUrl(''); setSha256('')
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to publish release'),
  })

  const promoteMutation = useMutation({
    mutationFn: ({ versionCode, rolloutState }: { versionCode: number; rolloutState: RolloutState }) =>
      api.promoteRelease(versionCode, rolloutState),
    onSuccess: (release) => {
      toast.success(
        release.rollout_state === 'released'
          ? `v${release.version_code} is now live for every screen without a pin`
          : `v${release.version_code} moved to ${release.rollout_state}`,
      )
      queryClient.invalidateQueries({ queryKey: ['releases'] })
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to change the rollout ring'),
  })

  const targetMutation = useMutation({
    mutationFn: ({ screenId, targetCode }: { screenId: number; targetCode: number | null }) =>
      api.patchScreen(screenId, { target_version_code: targetCode }),
    onSuccess: () => {
      toast.success('Target version updated')
      queryClient.invalidateQueries({ queryKey: ['screens'] })
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update target version'),
  })

  if (releasesQuery.isError || screensQuery.isError) {
    return <ErrorState message="Fleet releases could not be loaded." onRetry={() => { releasesQuery.refetch(); screensQuery.refetch() }} />
  }

  const releases = releasesQuery.data || []
  const screens = screensQuery.data || []
  // The highest *promoted* build: that is what a screen with no pin actually receives.
  // Labelling the highest version_code "Latest" was misleading once drafts existed --
  // an unreleased build would have worn the badge while reaching nobody.
  const latest = releases.reduce<number | null>(
    (max, release) => (release.rollout_state === 'released' ? Math.max(max ?? 0, release.version_code) : max),
    null,
  )
  // Base UI renders the raw value unless given a function, so without this the
  // trigger reads "global" rather than naming the version the screen will run.
  const ringLabel = (value: RolloutState | null) =>
    value === 'released' ? 'Released' : value === 'canary' ? 'Canary' : 'Draft'
  const versionLabel = (value: string | null) => {
    if (!value || value === 'global') return 'Follow latest'
    const release = releases.find((entry) => String(entry.version_code) === value)
    return release ? `v${release.version_code} · ${release.version_name}` : `v${value}`
  }

  const publishDialog = canPublish ? (
    <Dialog open={publishOpen} onOpenChange={setPublishOpen}>
      <DialogTrigger render={<Button />}><PackagePlus data-icon="inline-start" /> Publish release</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Publish app release</DialogTitle>
          <DialogDescription>Players pick this up on their next sync, subject to each screen&apos;s target version.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate({
              version_code: parseInt(versionCode, 10),
              version_name: versionName.trim(),
              apk_url: apkUrl.trim(),
              sha256: sha256.trim().toLowerCase(),
              mandatory: false,
            })
          }}
          className="space-y-4 pt-2"
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="version-code">Version code</Label>
              <Input id="version-code" type="number" min={1} value={versionCode} onChange={(event) => setVersionCode(event.target.value)} placeholder="5" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="version-name">Version name</Label>
              <Input id="version-name" value={versionName} onChange={(event) => setVersionName(event.target.value)} placeholder="1.2.0" required />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="apk-url">APK URL</Label>
            <Input id="apk-url" type="url" value={apkUrl} onChange={(event) => setApkUrl(event.target.value)} placeholder="https://…" required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="apk-sha">SHA256 <span className="text-muted-foreground/70 font-normal">(optional)</span></Label>
            <Input id="apk-sha" value={sha256} onChange={(event) => setSha256(event.target.value)} placeholder="Hex digest" className="font-mono" />
          </div>
          <Button type="submit" className="w-full" disabled={!versionCode || !versionName.trim() || !apkUrl.trim() || !/^[0-9a-fA-F]{64}$/.test(sha256.trim()) || createMutation.isPending}>
            {createMutation.isPending ? 'Publishing…' : 'Publish release'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  ) : <Badge variant="outline">Platform-managed</Badge>

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Player updates"
        title="Releases"
        description="Publish player builds, trial them on a few screens, then promote to the fleet."
        actions={publishDialog}
      />

      <section aria-labelledby="release-history" className="space-y-4">
        <h2 id="release-history" className="text-foreground text-sm font-semibold">Release history</h2>
        {releasesQuery.isLoading ? <Skeleton className="h-48" /> : !releases.length ? (
          <EmptyState
            icon={Package}
            title="No releases published"
            description="Publish a player build to make it available to your fleet."
            action={canPublish ? <Button onClick={() => setPublishOpen(true)}><PackagePlus data-icon="inline-start" /> Publish first release</Button> : undefined}
          />
        ) : (
          <Card className="ring-hairline bg-card border-0 py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1">
            <CardContent className="p-2 sm:p-3">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Version</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Ring</TableHead>
                    <TableHead>APK</TableHead>
                    <TableHead>SHA256</TableHead>
                    <TableHead>Published</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {releases.map((release) => (
                    <TableRow key={release.id}>
                      <TableCell className="font-medium tabular-nums">
                        {release.version_code}
                        {release.version_code === latest && <Badge variant="success" className="ml-2">Latest</Badge>}
                      </TableCell>
                      <TableCell>{release.version_name}</TableCell>
                      <TableCell>
                        {canPublish ? (
                          <Select
                            value={release.rollout_state}
                            onValueChange={(value) => promoteMutation.mutate({ versionCode: release.version_code, rolloutState: value as RolloutState })}
                            disabled={promoteMutation.isPending}
                          >
                            <SelectTrigger className="w-[130px]" aria-label={`Rollout ring for version ${release.version_code}`}>
                              <SelectValue>{(value: string | null) => ringLabel(value as RolloutState)}</SelectValue>
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="draft">Draft</SelectItem>
                              <SelectItem value="canary">Canary</SelectItem>
                              <SelectItem value="released">Released</SelectItem>
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge variant={release.rollout_state === 'released' ? 'success' : 'outline'}>{ringLabel(release.rollout_state)}</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground max-w-xs truncate" title={release.apk_url}>{release.apk_url}</TableCell>
                      <TableCell className="text-muted-foreground max-w-[120px] truncate font-mono text-xs" title={release.sha256 || undefined}>{release.sha256 || '—'}</TableCell>
                      <TableCell className="text-muted-foreground">{relativeTime(release.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </section>

      <section aria-labelledby="staged-rollout" className="space-y-4">
        <div>
          <h2 id="staged-rollout" className="text-foreground text-sm font-semibold">Staged rollout</h2>
          <p className="text-muted-foreground mt-1 text-sm">Pin individual screens to a version to trial a build before releasing it to everyone. A draft or canary build reaches only the screens pinned to it; a screen that fails to install its pinned build three times is unpinned automatically and stays on the version it is running.</p>
        </div>
        {screensQuery.isLoading ? <Skeleton className="h-48" /> : !screens.length ? (
          <EmptyState icon={Rocket} title="No screens paired" description="Pair a screen before staging a rollout." />
        ) : (
          <Card className="ring-hairline bg-card border-0 py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1">
            <CardContent className="p-2 sm:p-3">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Screen</TableHead>
                    <TableHead>Running</TableHead>
                    <TableHead>Update status</TableHead>
                    <TableHead>Target version</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {screens.map((screen) => (
                    <TableRow key={screen.id}>
                      <TableCell className="font-medium">{screen.name || `Screen ${screen.id}`}</TableCell>
                      <TableCell className="text-muted-foreground tabular-nums">{screen.app_version || 'Unknown'}</TableCell>
                      <TableCell className="text-muted-foreground">{screen.update_status || '—'}</TableCell>
                      <TableCell>
                        <Select
                          value={screen.target_version_code ? String(screen.target_version_code) : 'global'}
                          disabled={!canPin || targetMutation.isPending}
                          onValueChange={(value) => targetMutation.mutate({
                            screenId: screen.id,
                            targetCode: !value || value === 'global' ? null : parseInt(value, 10),
                          })}
                        >
                          <SelectTrigger className="w-[190px]"><SelectValue>{(value: string | null) => versionLabel(value)}</SelectValue></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="global">Follow latest</SelectItem>
                            {releases.map((release) => (
                              <SelectItem key={release.id} value={String(release.version_code)}>
                                v{release.version_code} · {release.version_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  )
}
