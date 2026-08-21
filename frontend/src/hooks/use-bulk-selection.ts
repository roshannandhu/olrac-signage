'use client'

import { useCallback, useMemo, useState } from 'react'

/**
 * Multi-select over a filtered list.
 *
 * Selection is kept as ids rather than objects so it survives a refetch, and every
 * derived value is intersected with what is currently visible — otherwise filtering a
 * list down and hitting "delete 12" would act on rows the operator can no longer see.
 */
export function useBulkSelection<T extends { id: number }>(visible: T[]) {
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const visibleIds = useMemo(() => visible.map((item) => item.id), [visible])

  // Only ever report a selection the operator can actually see.
  const selected = useMemo(
    () => selectedIds.filter((id) => visibleIds.includes(id)),
    [selectedIds, visibleIds],
  )
  const selectedItems = useMemo(
    () => visible.filter((item) => selected.includes(item.id)),
    [visible, selected],
  )

  const isSelected = useCallback((id: number) => selected.includes(id), [selected])

  const toggle = useCallback((id: number, on?: boolean) => {
    setSelectedIds((current) => {
      const has = current.includes(id)
      const next = on ?? !has
      if (next === has) return current
      return next ? [...current, id] : current.filter((value) => value !== id)
    })
  }, [])

  const allVisibleSelected = visible.length > 0 && selected.length === visible.length
  const someVisibleSelected = selected.length > 0 && !allVisibleSelected

  const toggleAll = useCallback(() => {
    setSelectedIds((current) =>
      // Comparing against the ids present now, not a stale count.
      visibleIds.every((id) => current.includes(id))
        ? current.filter((id) => !visibleIds.includes(id))
        : [...new Set([...current, ...visibleIds])],
    )
  }, [visibleIds])

  const clear = useCallback(() => setSelectedIds([]), [])

  return { selected, selectedItems, isSelected, toggle, toggleAll, clear, allVisibleSelected, someVisibleSelected }
}
