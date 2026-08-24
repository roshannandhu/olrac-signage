'use client'

/**
 * Last-resort boundary for errors thrown by the root or by a segment LAYOUT.
 *
 * A segment's error.tsx wraps that segment's *children*, never the layout itself, so an
 * error in dashboard/layout.tsx skipped dashboard/error.tsx entirely, bubbled past every
 * boundary, and landed on Next's built-in "This page couldn't load" screen -- which prints
 * nothing anywhere. That is why the header menu crash was undiagnosable: the stack existed
 * and no one could reach it.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body style={{ fontFamily: 'ui-monospace, monospace', padding: 24, background: '#111', color: '#eee' }}>
        <h1 style={{ fontSize: 20, marginBottom: 8 }}>Unhandled error</h1>
        <p style={{ color: '#f87171', fontSize: 14 }}>{error?.message || String(error)}</p>
        {error?.digest ? <p style={{ color: '#888', fontSize: 12 }}>digest: {error.digest}</p> : null}
        <pre
          id="global-error-stack"
          style={{ whiteSpace: 'pre-wrap', fontSize: 12, marginTop: 16, color: '#bbb' }}
        >
          {error?.stack || '(no stack)'}
        </pre>
        <button onClick={reset} style={{ marginTop: 16, padding: '8px 16px' }}>
          Try again
        </button>
      </body>
    </html>
  )
}
