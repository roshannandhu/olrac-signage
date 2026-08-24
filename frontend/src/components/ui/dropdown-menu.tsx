'use client'

import * as React from 'react'
import { Menu } from '@base-ui/react/menu'
import { cn } from '@/lib/utils'

const DropdownMenu = Menu.Root
const DropdownMenuTrigger = Menu.Trigger

function DropdownMenuContent({
  className,
  align = 'end',
  sideOffset = 8,
  ...props
}: React.ComponentProps<typeof Menu.Popup> &
  Pick<React.ComponentProps<typeof Menu.Positioner>, 'align' |'sideOffset' |'side'>) {
  return (
    <Menu.Portal>
      <Menu.Positioner align={align} sideOffset={sideOffset} className="z-50">
        <Menu.Popup
          className={cn(
            'bg-popover text-popover-foreground ring-hairline min-w-52 origin-(--transform-origin) rounded-xl p-1.5 shadow-lg ring-1',
            className,
          )}
          {...props}
        />
      </Menu.Positioner>
    </Menu.Portal>
  )
}

function DropdownMenuItem({ className, ...props }: React.ComponentProps<typeof Menu.Item>) {
  return (
    <Menu.Item
      className={cn(
        'data-highlighted:bg-accent data-highlighted:text-accent-foreground flex h-10 cursor-pointer items-center gap-3 rounded-lg px-3 text-sm outline-none select-none',
        '[&_svg]:text-muted-foreground [&_svg]:size-[18px] [&_svg]:shrink-0',
        className,
      )}
      {...props}
    />
  )
}

/** Same row, but it navigates — keeps the anchor so middle-click and copy-link work. */
function DropdownMenuLinkItem({ className, ...props }: React.ComponentProps<typeof Menu.LinkItem>) {
  return (
    <Menu.LinkItem
      className={cn(
        'data-highlighted:bg-accent data-highlighted:text-accent-foreground flex h-10 cursor-pointer items-center gap-3 rounded-lg px-3 text-sm outline-none select-none',
        '[&_svg]:text-muted-foreground [&_svg]:size-[18px] [&_svg]:shrink-0',
        className,
      )}
      {...props}
    />
  )
}

function DropdownMenuSeparator({ className, ...props }: React.ComponentProps<typeof Menu.Separator>) {
  return <Menu.Separator className={cn('bg-border -mx-1.5 my-1.5 h-px', className)} {...props} />
}

/** A heading row inside the menu — the account block's name, email and role.
 *
 * Wraps its own Menu.Group. Menu.GroupLabel reads MenuGroupContext and THROWS
 * "MenuGroupContext is missing" when it cannot find one, and a label is normally written
 * as a standalone header rather than as part of a group. Bare, this crashed the account
 * menu the instant its popup rendered — and because the menu lives in dashboard/layout.tsx,
 * the throw skipped dashboard/error.tsx (a segment's error boundary wraps its children,
 * never its own layout), so the whole dashboard fell through to Next's built-in
 * "This page couldn't load" with nothing logged anywhere.
 *
 * The group lives here rather than at the call site so every future label is safe by
 * construction.
 */
function DropdownMenuLabel({ className, ...props }: React.ComponentProps<typeof Menu.GroupLabel>) {
  return (
    <Menu.Group>
      <Menu.GroupLabel className={cn('px-3 py-2', className)} {...props} />
    </Menu.Group>
  )
}

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLinkItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
}
