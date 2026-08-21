'use client'

import * as React from 'react'
import { Tabs as BaseTabs } from '@base-ui/react/tabs'
import { cn } from '@/lib/utils'

function Tabs({ className, ...props }: React.ComponentProps<typeof BaseTabs.Root>) {
  return <BaseTabs.Root className={cn('flex flex-col gap-6', className)} {...props} />
}

function TabsList({ className, ...props }: React.ComponentProps<typeof BaseTabs.List>) {
  return (
    <BaseTabs.List
      className={cn('border-hairline relative flex items-center gap-1 border-b', className)}
      {...props}
    />
  )
}

function TabsTrigger({ className, ...props }: React.ComponentProps<typeof BaseTabs.Tab>) {
  return (
    <BaseTabs.Tab
      className={cn(
        'text-muted-foreground data-[selected]:text-foreground focus-visible:ring-primary -mb-px cursor-pointer rounded-t-lg px-4 py-2.5 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none',
        'hover:text-foreground',
        className,
      )}
      {...props}
    />
  )
}

/** Sits under the selected tab and slides between them. */
function TabsIndicator({ className, ...props }: React.ComponentProps<typeof BaseTabs.Indicator>) {
  return (
    <BaseTabs.Indicator
      className={cn(
        'bg-primary absolute bottom-0 left-0 z-10 h-0.5 w-[var(--active-tab-width)] translate-x-[var(--active-tab-left)] rounded-full transition-all duration-200',
        className,
      )}
      {...props}
    />
  )
}

// Base UI marks a deselected panel `inert` but never gets as far as applying `hidden` or
// unmounting it, so without this every panel you have visited stays stacked on the page.
// ponytail: keyed off `inert` because that is the attribute the library reliably sets;
// drop the variant if a future Base UI unmounts closed panels on its own.
function TabsPanel({ className, ...props }: React.ComponentProps<typeof BaseTabs.Panel>) {
  return <BaseTabs.Panel className={cn('[&[inert]]:hidden focus-visible:outline-none', className)} {...props} />
}

export { Tabs, TabsList, TabsTrigger, TabsIndicator, TabsPanel }
