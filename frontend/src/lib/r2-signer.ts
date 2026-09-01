import { sha256 } from 'js-sha256'

const R2_ACCESS_KEY_ID = '734d432aeb20a3f4bbd484ca83a8a82b'
const R2_SECRET_ACCESS_KEY = 'ef6c0c74667843ec08f396b12ab0e8929d409c8c8062713da09cd17c6c628acf'
const R2_ENDPOINT_HOST = '3fe4487a2b8fd1e2e541bf0e0f4c7c42.r2.cloudflarestorage.com'
const R2_BUCKET = 'olrac'
const R2_REGION = 'auto'
const R2_SERVICE = 's3'

function getSigningKey(secretKey: string, dateStr: string, region: string, service: string): number[] {
  const kDate = sha256.hmac.create('AWS4' + secretKey).update(dateStr).array()
  const kRegion = sha256.hmac.create(kDate).update(region).array()
  const kService = sha256.hmac.create(kRegion).update(service).array()
  return sha256.hmac.create(kService).update('aws4_request').array()
}

/**
 * Synchronously converts any `s3://` storage key or URL into a 7-day presigned Cloudflare R2 URL.
 * Works seamlessly across browser clients, Next.js server components, and Cloudflare Workers.
 */
export function presignR2Url(keyOrUrl: string | null | undefined): string | undefined {
  if (!keyOrUrl) return undefined
  if (!keyOrUrl.startsWith('s3://') && !keyOrUrl.startsWith('r2://')) {
    return keyOrUrl
  }

  try {
    const now = new Date()
    const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, '')
    const dateStamp = amzDate.substring(0, 8)

    const cleanKey = keyOrUrl.replace(/^(s3|r2):\/\//, '').replace(/^\/+/, '')
    const canonicalUri = `/${R2_BUCKET}/${cleanKey}`
    const credential = `${R2_ACCESS_KEY_ID}/${dateStamp}/${R2_REGION}/${R2_SERVICE}/aws4_request`

    const queryParams: Record<string, string> = {
      'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
      'X-Amz-Credential': credential,
      'X-Amz-Date': amzDate,
      'X-Amz-Expires': '604800',
      'X-Amz-SignedHeaders': 'host',
    }

    const canonicalQueryString = Object.keys(queryParams)
      .sort()
      .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(queryParams[k])}`)
      .join('&')

    const canonicalHeaders = `host:${R2_ENDPOINT_HOST}\n`
    const signedHeaders = 'host'
    const payloadHash = 'UNSIGNED-PAYLOAD'

    const canonicalRequest = ['GET', canonicalUri, canonicalQueryString, canonicalHeaders, signedHeaders, payloadHash].join('\n')
    const stringToSign = ['AWS4-HMAC-SHA256', amzDate, `${dateStamp}/${R2_REGION}/${R2_SERVICE}/aws4_request`, sha256(canonicalRequest)].join('\n')

    const signingKey = getSigningKey(R2_SECRET_ACCESS_KEY, dateStamp, R2_REGION, R2_SERVICE)
    const signature = sha256.hmac.create(signingKey).update(stringToSign).hex()

    return `https://${R2_ENDPOINT_HOST}${canonicalUri}?${canonicalQueryString}&X-Amz-Signature=${signature}`
  } catch (error) {
    console.error('Failed to presign R2 URL:', error)
    return keyOrUrl
  }
}
