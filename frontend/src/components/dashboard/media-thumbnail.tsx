'use client'

import { useState } from 'react'
import { ImageIcon, Video } from 'lucide-react'
import type { ContentItem } from '@/lib/types'
import { resolveMediaUrl } from '@/lib/api'

export function MediaThumbnail({ item, className = '' }: { item: ContentItem; className?: string }) {
  const [hasError, setHasError] = useState(false)
  
  // `type` is what the row actually says it is. This used to sniff the URL for ".mp4",
  // which broke the moment the URL grew a query string or a proxy path -- a video whose
  // signed URL happened not to contain the extension was handed to an <img>, and the
  // failure was indistinguishable from a missing file.
  //
  // A video whose poster frame could not be generated (no ffmpeg on the box) has its
  // thumbnail set to the video itself, so only a thumbnail that DIFFERS from the source is
  // a real poster image.
  const posterSource =
    item.type === 'image'
      ? item.thumbnail || item.file_url
      : item.thumbnail && item.thumbnail !== item.file_url
        ? item.thumbnail
        : null

  const resolvedImage = hasError ? undefined : resolveMediaUrl(posterSource)
  const isHttpImage = Boolean(resolvedImage && /^(https?:\/\/|\/)/.test(resolvedImage))

  const resolvedVideo = resolveMediaUrl(item.file_url)
  const isHttpVideo = Boolean(resolvedVideo && /^(https?:\/\/|\/)/.test(resolvedVideo))
  // The fragment makes the player paint its first frame instead of a black rectangle.
  const videoPosterSource = isHttpVideo ? `${resolvedVideo}${resolvedVideo!.includes('#') ? '' : '#t=0.001'}` : undefined

  return (
    <div className={`bg-muted relative overflow-hidden ${className}`}>
      {isHttpImage ? (
        <img
          src={resolvedImage}
          alt={item.name}
          onError={() => setHasError(true)}
          loading="lazy"
          className="size-full object-cover transition-transform duration-500 group-hover/card:scale-[1.03] motion-reduce:transition-none"
        />
      ) : item.type === 'video' ? (
        videoPosterSource ? (
          <video
            src={videoPosterSource}
            muted
            playsInline
            preload="metadata"
            className="size-full object-cover"
            aria-label={`${item.name} preview`}
          />
        ) : (
          <div className="text-muted-foreground/50 grid size-full place-items-center bg-gradient-to-br from-slate-900 to-slate-800">
            <Video className="size-7 text-primary/70" />
          </div>
        )
      ) : (
        <div className="text-muted-foreground/50 grid size-full place-items-center bg-gradient-to-br from-slate-900 to-slate-800">
          <ImageIcon className="size-7" />
        </div>
      )}
      <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-slate-950/35 to-transparent" aria-hidden="true" />
    </div>
  )
}

