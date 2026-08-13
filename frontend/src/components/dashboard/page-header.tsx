import type { ReactNode } from 'react'

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description: string
  actions?: ReactNode
}) {
  return (
    <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        {eyebrow && <p className="text-primary mb-2 text-xs font-bold tracking-[0.18em] uppercase dark:text-brand">{eyebrow}</p>}
        <h1 className="text-foreground text-3xl font-semibold text-balance tracking-[-0.035em] sm:text-4xl">{title}</h1>
        <p className="text-muted-foreground mt-2 text-sm leading-6 sm:text-base">{description}</p>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}
