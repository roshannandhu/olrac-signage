'use client'

import * as React from 'react'
import { ArrowUpDown, Search, SlidersHorizontal } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export type SortOption<T extends string> = { value: T; label: string }

/** Sorts every list page shares. Pages add their own (start date, expiry) on top. */
export const commonSorts = [
  { value: 'newest', label: 'Date added (newest first)' },
  { value: 'oldest', label: 'Date added (oldest first)' },
  { value: 'az', label: 'Alphabetical (ascending)' },
  { value: 'za', label: 'Alphabetical (descending)' },
] as const

export type CommonSort = (typeof commonSorts)[number]['value']

/** Applies the shared sorts. `date` is whatever timestamp the page sorts on. */
export function sortItems<T>(items: T[], sort: string, name: (item: T) => string, date: (item: T) => string) {
  const sorted = [...items]
  switch (sort) {
    case 'oldest':
      return sorted.sort((a, b) => Date.parse(date(a)) - Date.parse(date(b)))
    case 'az':
      return sorted.sort((a, b) => name(a).localeCompare(name(b)))
    case 'za':
      return sorted.sort((a, b) => name(b).localeCompare(name(a)))
    default:
      return sorted.sort((a, b) => Date.parse(date(b)) - Date.parse(date(a)))
  }
}

export function ListToolbar<T extends string>({
  title,
  action,
  menu,
  sort,
  filters,
  search,
  className,
}: {
  title: string
  action?: React.ReactNode
  menu?: React.ReactNode
  sort?: { value: T; onChange: (value: T) => void; options: readonly SortOption<T>[] }
  filters?: React.ReactNode
  search?: { value: string; onChange: (value: string) => void; placeholder?: string }
  className?: string
}) {
  return (
    <div className={cn('mb-6 flex flex-wrap items-center gap-x-4 gap-y-3', className)}>
      <h1 className="text-foreground text-2xl font-bold tracking-tight">{title}</h1>
      {menu}
      {action}

      <div className="ml-auto flex flex-wrap items-center gap-1">
        {sort && (
          <DropdownMenu>
            <DropdownMenuTrigger className="text-primary dark:text-brand hover:bg-accent focus-visible:ring-ring flex h-10 cursor-pointer items-center gap-2 rounded-lg px-3 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none">
              <ArrowUpDown className="size-4" aria-hidden="true" /> Sort
            </DropdownMenuTrigger>
            <DropdownMenuContent className="min-w-64">
              {sort.options.map((option) => (
                <DropdownMenuItem
                  key={option.value}
                  onClick={() => sort.onChange(option.value)}
                  className={cn(sort.value === option.value && 'bg-accent text-accent-foreground font-medium')}
                >
                  {option.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {filters && (
          <DropdownMenu>
            <DropdownMenuTrigger className="text-primary dark:text-brand hover:bg-accent focus-visible:ring-ring flex h-10 cursor-pointer items-center gap-2 rounded-lg px-3 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none">
              <SlidersHorizontal className="size-4" aria-hidden="true" /> Filters
            </DropdownMenuTrigger>
            <DropdownMenuContent className="min-w-60">{filters}</DropdownMenuContent>
          </DropdownMenu>
        )}

        {search && (
          <div className="relative w-full sm:w-64">
            <Input
              value={search.value}
              onChange={(event) => search.onChange(event.target.value)}
              placeholder={search.placeholder || 'Search'}
              aria-label={search.placeholder || 'Search'}
              className="bg-card h-10 pr-9"
            />
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 right-3 size-[18px] -translate-y-1/2" aria-hidden="true" />
          </div>
        )}
      </div>
    </div>
  )
}
