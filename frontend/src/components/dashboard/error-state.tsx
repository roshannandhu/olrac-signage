import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function ErrorState({ message = 'We could not load this view.', onRetry }: { message?: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex min-h-52 flex-col items-center justify-center rounded-2xl border border-rose-500/25 bg-rose-500/10 px-6 text-center">
      <AlertTriangle className="mb-3 size-6 text-rose-600 dark:text-rose-400" aria-hidden="true" />
      <p className="font-semibold text-rose-950 dark:text-rose-100">Something went wrong</p>
      <p className="mt-1 text-sm text-rose-700 dark:text-rose-300/80">{message}</p>
      <Button variant="outline" className="bg-card mt-4 h-10" onClick={onRetry}>
        <RotateCcw data-icon="inline-start" /> Try again
      </Button>
    </div>
  )
}
