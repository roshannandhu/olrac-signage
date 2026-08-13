'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { RadioTower } from 'lucide-react'
import { useAuthStore } from '@/lib/store'

export default function Home() {
  const router = useRouter()
  const { token, hydrated } = useAuthStore()

  useEffect(() => {
    if (hydrated) router.replace(token ? '/dashboard' : '/login')
  }, [hydrated, token, router])

  return (
    <main className="grid min-h-screen place-items-center bg-rail text-brand">
      <div className="flex items-center gap-3 text-sm font-semibold tracking-[0.16em]">
        <RadioTower className="size-5 animate-pulse motion-reduce:animate-none" /> OLRAC
      </div>
    </main>
  )
}
