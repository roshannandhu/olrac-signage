import { cn } from '@/lib/utils'

export function StatusIndicator({ status }: { status: 'online' | 'offline' | 'waiting_pairing' }) {
  const label = status === 'waiting_pairing' ? 'Pairing' : status === 'online' ? 'Online' : 'Offline'
  return (
    <span className={cn(
      'inline-flex items-center gap-2 text-xs font-semibold',
      status === 'online' ? 'text-emerald-600 dark:text-emerald-400' : status === 'waiting_pairing' ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground',
    )}>
      <span className="relative flex size-2" aria-hidden="true">
        {status === 'online' && <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-50 motion-reduce:animate-none" />}
        <span className={cn('relative inline-flex size-2 rounded-full', status === 'online' ? 'bg-emerald-500' : status === 'waiting_pairing' ? 'bg-amber-500' : 'bg-muted-foreground/60')} />
      </span>
      {label}
    </span>
  )
}
