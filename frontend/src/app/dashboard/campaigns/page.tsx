'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { BarChart3 } from 'lucide-react'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { PageHeader } from '@/components/dashboard/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'

export default function CampaignsPage() {
  const campaignsQuery = useQuery({ queryKey: ['campaigns'], queryFn: api.getCampaigns })

  if (campaignsQuery.isError) return <ErrorState message="Campaigns could not be loaded." onRetry={() => campaignsQuery.refetch()} />
  const campaigns = campaignsQuery.data || []

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Reporting" title="Campaigns" description="Proof-of-play reporting for every campaign running across your network." />

      {campaignsQuery.isLoading ? (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-40" />)}</div>
      ) : !campaigns.length ? (
        <EmptyState icon={BarChart3} title="No campaigns yet" description="Assign a campaign to a playlist and its playback analytics will appear here." />
      ) : (
        <div className="stagger grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {campaigns.map((campaign, index) => (
            <Link
              key={campaign.id}
              href={`/dashboard/campaigns/${campaign.id}`}
              style={{ '--i': index } as React.CSSProperties}
              className="group focus-visible:ring-primary rounded-2xl focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
            >
              <Card className="lift ring-hairline bg-card h-full border-0 py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1 hover:shadow-[0_14px_40px_rgba(15,23,42,.08)]">
                <CardContent className="p-5">
                  <span className="bg-primary/10 text-primary dark:text-brand grid size-11 place-items-center rounded-xl">
                    <BarChart3 className="size-5" aria-hidden="true" />
                  </span>
                  <h2 className="text-foreground mt-4 font-semibold tracking-[-0.02em]">{campaign.name}</h2>
                  <p className="text-muted-foreground/70 mt-1 text-sm">View detailed analytics</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
