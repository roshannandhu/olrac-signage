import type { User } from './types'

/**
 * Who a signed-in account is, and where it belongs.
 *
 * One module, because every previous version of this logic was copy-pasted and then
 * drifted. First it was a hardcoded list of operator email addresses in four files, whose
 * copies disagreed about which addresses counted. That was replaced by a role column, and
 * the checks promptly drifted again in a subtler way: /login and the dashboard resolved the
 * role from the SERVER, while the /admin guard read the browser's cached copy — so a
 * genuine platform operator was redirected out of /admin and into a tenant workspace they
 * have no features in, while the API served them /api/admin/* without complaint.
 *
 * The rule is one line and it lives here: platform status is the role, and the role is
 * whatever the server last said it was.
 */
export function isSuperAdmin(account: Pick<User, 'role'> | null | undefined): boolean {
  return account?.role === 'super_admin'
}

/** May change tenant content: screens, playlists, bookings. */
export function canEditTenantContent(account: Pick<User, 'role'> | null | undefined): boolean {
  return account?.role === 'owner' || account?.role === 'editor' || isSuperAdmin(account)
}

/**
 * Where a user lands after signing in.
 *
 * A platform operator goes to /admin, which deliberately has none of the tenant features;
 * everyone else goes to their own workspace, or to the pending screen while their
 * organisation is waiting for approval.
 */
export function destinationFor(
  account: Pick<User, 'role' | 'organization_status'> | null | undefined,
): string {
  if (isSuperAdmin(account)) return '/admin'
  if (account?.organization_status === 'pending_approval') return '/dashboard/pending'
  return '/dashboard/screens'
}
