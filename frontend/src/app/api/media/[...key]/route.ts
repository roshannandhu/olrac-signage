import { NextRequest, NextResponse } from 'next/server'
import { presignR2Url } from '@/lib/r2-signer'

export const dynamic = 'force-dynamic'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ key: string[] }> }
) {
  const resolvedParams = await params
  const keyParts = resolvedParams.key
  if (!keyParts || keyParts.length === 0) {
    return new NextResponse('Not found', { status: 404 })
  }

  const storageKey = keyParts.join('/')
  // Prevent path traversal
  if (storageKey.includes('..') || storageKey.startsWith('/')) {
    return new NextResponse('Invalid key', { status: 400 })
  }

  const presigned = presignR2Url(`s3://${storageKey}`)
  if (!presigned || presigned.startsWith('s3://')) {
    return new NextResponse('Failed to resolve storage key', { status: 502 })
  }

  return NextResponse.redirect(presigned, {
    status: 307,
    headers: {
      'Cache-Control': 'public, max-age=3600, s-maxage=86400',
    },
  })
}
