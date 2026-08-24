'use client'

import Image from 'next/image'
import { ImageIcon } from 'lucide-react'
import type { ContentItem } from '@/lib/types'

import { resolveMediaUrl } from '@/lib/api'

export function MediaThumbnail({ item, className = '' }: { item: ContentItem; className?: string }) {
  const imageSource = resolveMediaUrl(item.thumbnail || (item.type === 'image' ? item.file_url : null))
  const videoSource = resolveMediaUrl(item.file_url)
  return (
    <div className={`bg-muted relative overflow-hidden ${className}`}>
      {imageSource ? (
        <Image
          src={imageSource}
          alt=""
          fill
          unoptimized
          sizes="(max-width: 768px) 100vw, 25vw"
          className="object-cover transition-transform duration-500 group-hover/card:scale-[1.03] motion-reduce:transition-none"
        />
      ) : item.type === 'video' ? (
        <video src={videoSource} muted preload="metadata" className="size-full object-cover" aria-label={`${item.name} preview`} />
      ) : (
        <div className="text-muted-foreground grid size-full place-items-center">
          <ImageIcon className="size-7" />
        </div>
      )}
      <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-slate-950/35 to-transparent" aria-hidden="true" />
    </div>
  )
}
