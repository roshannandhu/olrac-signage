'use client'

import * as React from 'react'
import { Button } from '@/components/ui/button'

/**
 * Appears once something is selected and states the count plainly.
 *
 * Saying the number out loud matters: a bulk action taken against a filtered list should
 * never turn out to be bigger than it looked.
 */
export function BulkActionBar({
  count,
  noun,
  onClear,
  children,
}: {
  count: number
  /** Singular noun, pluralised with a trailing s. */
  noun: string
  onClear: () => void
  children: React.ReactNode
}) {
  if (count === 0) return null
  return (
    <div className="ring-hairline bg-secondary/70 mb-4 flex flex-wrap items-center gap-3 rounded-xl p-3 ring-1 backdrop-blur">
      <span className="text-foreground text-sm font-medium">
        {count} {noun}{count === 1 ? '' : 's'} selected
      </span>
      <div className="ml-auto flex flex-wrap items-center gap-2">
        {children}
        <Button size="sm" variant="ghost" onClick={onClear}>Clear</Button>
      </div>
    </div>
  )
}

/** Checkbox that also renders the partial state when only some rows are ticked. */
export function SelectAllCheckbox({
  checked,
  indeterminate,
  onChange,
  label = 'Select all',
}: {
  checked: boolean
  indeterminate: boolean
  onChange: () => void
  label?: string
}) {
  const ref = React.useRef<HTMLInputElement>(null)
  // `indeterminate` is a DOM property with no HTML attribute, so it has to be set here.
  React.useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate
  }, [indeterminate])

  return (
    <label className="text-muted-foreground hover:text-foreground flex cursor-pointer items-center gap-2 text-sm">
      <input ref={ref} type="checkbox" className="accent-primary size-4" checked={checked} onChange={onChange} aria-label={label} />
      {label}
    </label>
  )
}
