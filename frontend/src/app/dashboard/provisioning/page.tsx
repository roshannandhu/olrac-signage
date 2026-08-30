'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import { isSuperAdmin } from '@/lib/roles'

export default function ProvisioningPageRedirect() {
  const router = useRouter()
  const user = useAuthStore((state) => state.user)

  useEffect(() => {
    if (isSuperAdmin(user)) {
      router.replace('/admin/provisioning')
    } else {
      router.replace('/dashboard/screens')
    }
  }, [user, router])

  return <div className="p-8 text-center text-sm text-muted-foreground">Redirecting...</div>
}
