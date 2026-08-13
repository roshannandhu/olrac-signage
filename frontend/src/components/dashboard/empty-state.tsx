import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

export function EmptyState({ icon: Icon, title, description, action }: {
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="border-border bg-card/60 flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed px-6 py-12 text-center">
      <div className="ring-primary/15 text-primary mb-4 grid size-12 place-items-center rounded-2xl bg-primary/10 ring-1 dark:text-brand">
        <Icon className="size-5" aria-hidden="true" />
      </div>
      <h2 className="text-foreground text-base font-semibold">{title}</h2>
      <p className="text-muted-foreground mt-1 max-w-sm text-sm leading-6">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
