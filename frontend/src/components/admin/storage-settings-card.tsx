'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle, KeyRound, Plug } from 'lucide-react'
import { adminApi } from '@/lib/api'

/**
 * Storage credentials, set from here rather than from the server's environment.
 *
 * The environment is not always reachable by the person who needs to change it. This product
 * ran with `AWS_ACCESS_KEY_ID=mock` — a value indistinguishable from an unconfigured one —
 * while its operator edited that variable on a second Render service and watched nothing
 * change. The console is a place they can always reach, and what they type here wins.
 *
 * The secret is write-only. It is sent, never returned, and the field stays blank on reload
 * rather than showing dots that imply it could be read back.
 */
export function StorageSettingsCard() {
  const queryClient = useQueryClient()
  const { data } = useQuery({ queryKey: ['admin', 'storage-settings'], queryFn: adminApi.getStorageSettings })

  const [keyId, setKeyId] = useState('')
  const [secret, setSecret] = useState('')
  const [bucket, setBucket] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'storage-settings'] })
    queryClient.invalidateQueries({ queryKey: ['admin', 'storage'] })
    queryClient.invalidateQueries({ queryKey: ['health'] })
  }

  const save = useMutation({
    mutationFn: () =>
      adminApi.saveStorageSettings({
        // Only what was typed. An untouched field must not clear a setting that is working.
        ...(keyId.trim() ? { access_key_id: keyId.trim() } : {}),
        ...(secret.trim() ? { secret_access_key: secret.trim() } : {}),
        ...(bucket.trim() ? { bucket: bucket.trim() } : {}),
        ...(endpoint.trim() ? { endpoint_url: endpoint.trim() } : {}),
      }),
    onSuccess: (result) => {
      setError('')
      // Cleared immediately: the secret should not sit in the page after it has been sent.
      setSecret('')
      setKeyId('')
      setMessage(
        result.storage_enabled
          ? 'Saved. Storage is connected — uploads are now stored permanently.'
          : 'Saved, but storage still reports as not configured. Check the key and try Test.',
      )
      refresh()
    },
    onError: (e: Error) => { setMessage(''); setError(e.message) },
  })

  const test = useMutation({
    mutationFn: adminApi.testStorageSettings,
    onSuccess: (result) => {
      if (result.ok) { setError(''); setMessage(result.detail) }
      else { setMessage(''); setError(result.detail) }
    },
    onError: (e: Error) => { setMessage(''); setError(e.message) },
  })

  const field = (
    label: string,
    value: string,
    onChange: (v: string) => void,
    placeholder: string,
    secretField = false,
  ) => (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-foreground">{label}</label>
      <input
        type={secretField ? 'password' : 'text'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck={false}
        className="w-full rounded-lg border border-border bg-muted px-3 py-2 font-mono text-sm text-foreground placeholder:font-sans placeholder:text-muted-foreground/60"
      />
    </div>
  )

  return (
    <section className="rounded-2xl border border-border bg-card p-5">
      <div className="flex items-start gap-3">
        <div className="grid size-9 shrink-0 place-items-center rounded-xl border border-violet-500/20 bg-violet-500/10">
          <KeyRound className="size-4 text-violet-400" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-foreground">Storage credentials</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Set the Cloudflare R2 (or S3) key here and it takes effect immediately, overriding
            whatever the server&apos;s environment says. No redeploy.
          </p>
        </div>
        {data && (
          <span
            className={`shrink-0 rounded-lg border px-2.5 py-1 text-xs ${
              data.storage_enabled
                ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
                : 'border-amber-500/20 bg-amber-500/10 text-amber-400'
            }`}
          >
            {data.storage_enabled ? 'Connected' : 'Not configured'}
          </span>
        )}
      </div>

      {data && (
        <p className="mt-3 text-xs text-muted-foreground">
          In use: key <span className="font-mono text-foreground">{data.access_key_id ?? 'none'}</span>
          {' · '}bucket <span className="font-mono text-foreground">{data.bucket ?? 'none'}</span>
          {' · '}secret {data.secret_is_set ? 'set' : 'not set'}
          {data.from_console.length > 0 && ' · set from this page'}
        </p>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {field('Access Key ID', keyId, setKeyId, data?.access_key_id ? `keeping ${data.access_key_id}` : 'paste the Access Key ID')}
        {field('Secret Access Key', secret, setSecret, data?.secret_is_set ? 'keeping the saved secret' : 'paste the Secret Access Key', true)}
        {field('Bucket', bucket, setBucket, data?.bucket ?? 'olrac')}
        {field('Endpoint URL', endpoint, setEndpoint, data?.endpoint_url ?? 'https://<account>.r2.cloudflarestorage.com')}
      </div>

      <p className="mt-2 text-xs text-muted-foreground/70">
        Leave a field blank to keep what is already saved. The secret is never shown again
        after saving — it is stored, not displayed.
      </p>

      {message && (
        <p className="mt-3 flex items-start gap-2 rounded-lg bg-emerald-500/10 p-2.5 text-xs text-emerald-400">
          <CheckCircle className="mt-0.5 size-3.5 shrink-0" />{message}
        </p>
      )}
      {error && (
        <p className="mt-3 flex items-start gap-2 rounded-lg bg-rose-500/10 p-2.5 text-xs text-rose-400">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />{error}
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={() => { setMessage(''); setError(''); save.mutate() }}
          disabled={save.isPending || (!keyId.trim() && !secret.trim() && !bucket.trim() && !endpoint.trim())}
          className="rounded-lg bg-violet-500 px-4 py-2 text-sm font-medium text-white hover:bg-violet-600 disabled:opacity-40"
        >
          {save.isPending ? 'Saving…' : 'Save credentials'}
        </button>
        <button
          onClick={() => { setMessage(''); setError(''); test.mutate() }}
          disabled={test.isPending}
          className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted disabled:opacity-40"
        >
          <Plug className="size-3.5" />
          {test.isPending ? 'Testing…' : 'Test connection'}
        </button>
      </div>
    </section>
  )
}
