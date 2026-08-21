import { Skeleton } from '@/components/ui/skeleton'

export default function DashboardLoading() {
  return <div className="space-y-8"><div className="space-y-3"><Skeleton className="h-4 w-28" /><Skeleton className="h-10 w-80 max-w-full" /><Skeleton className="h-5 w-[520px] max-w-full" /></div><div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-36" />)}</div><Skeleton className="h-80" /></div>
}
