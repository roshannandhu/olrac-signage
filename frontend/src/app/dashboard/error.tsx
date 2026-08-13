'use client'

import { useEffect } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function DashboardError({ error, unstable_retry }: { error: Error & { digest?: string }; unstable_retry: () => void }) {
  useEffect(() => { console.error(error) }, [error])
  return (
    <div className="grid min-h-[60vh] place-items-center"><div className="max-w-md text-center"><span className="mx-auto grid size-14 place-items-center rounded-2xl bg-rose-500/10 text-rose-600 dark:text-rose-400"><AlertTriangle className="size-6" /></span><h1 className="mt-5 text-2xl font-semibold tracking-tight">The dashboard hit a snag</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">Your data is safe. Retry this view, or return after checking the backend connection.</p><Button className="mt-6" onClick={unstable_retry}><RotateCcw data-icon="inline-start" /> Retry view</Button></div></div>
  )
}
