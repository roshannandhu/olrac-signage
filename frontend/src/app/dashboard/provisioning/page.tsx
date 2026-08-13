"use client"

import React, { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'

export default function ProvisioningPage() {
  const [wifiSsid, setWifiSsid] = useState('')
  const [wifiPassword, setWifiPassword] = useState('')
  const [wifiSecurity, setWifiSecurity] = useState('WPA')
  const [maxUses, setMaxUses] = useState(1)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [qrPayload, setQrPayload] = useState<string | null>(null)

  async function generateQr(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setQrPayload(null)

    try {
      const res = await fetch('/api/provisioning/qr', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          wifi_ssid: wifiSsid,
          wifi_password: wifiPassword,
          wifi_security_type: wifiSecurity,
          max_uses: maxUses,
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `HTTP Error ${res.status}`)
      }

      const payload = await res.json()
      setQrPayload(JSON.stringify(payload))
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 text-gray-200">
      <h1 className="text-3xl font-light mb-2">Zero-Touch Provisioning</h1>
      <p className="text-sm text-gray-400 mb-8">
        Generate a device-owner QR code to configure OLRAC Signage on factory-reset Android TVs.
        This enables kiosk mode and silent updates without ADB.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <form onSubmit={generateQr} className="bg-gray-800/50 p-6 rounded-lg border border-gray-700/50">
            <h2 className="text-xl font-medium mb-4">Site Configuration</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-400 mb-1">Wi-Fi SSID</label>
              <input
                type="text"
                required
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-green-500"
                value={wifiSsid}
                onChange={(e) => setWifiSsid(e.target.value)}
                placeholder="Site Network Name"
              />
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-400 mb-1">Wi-Fi Password</label>
              <input
                type="password"
                required
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-green-500"
                value={wifiPassword}
                onChange={(e) => setWifiPassword(e.target.value)}
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-400 mb-1">Wi-Fi Security</label>
              <select
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-green-500"
                value={wifiSecurity}
                onChange={(e) => setWifiSecurity(e.target.value)}
              >
                <option value="WPA">WPA/WPA2/WPA3</option>
                <option value="WEP">WEP</option>
                <option value="NONE">None</option>
              </select>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-400 mb-1">Number of TVs (Max uses)</label>
              <input
                type="number"
                required
                min="1"
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-green-500"
                value={maxUses}
                onChange={(e) => setMaxUses(parseInt(e.target.value) || 1)}
              />
              <p className="text-xs text-gray-500 mt-1">
                The enrollment token embedded in this QR code will expire after this many uses.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-500 hover:bg-green-400 text-gray-900 font-medium py-2 px-4 rounded disabled:opacity-50"
            >
              {loading ? 'Generating...' : 'Generate QR Code'}
            </button>

            {error && (
              <div className="mt-4 bg-red-900/50 border border-red-500/50 text-red-200 p-3 rounded text-sm">
                {error}
              </div>
            )}
          </form>
        </div>

        <div className="flex flex-col items-center justify-center bg-gray-800/30 p-8 rounded-lg border border-gray-700/50 min-h-[400px]">
          {qrPayload ? (
            <div className="flex flex-col items-center">
              <div className="bg-white p-4 rounded-lg shadow-xl mb-6">
                <QRCodeSVG
                  value={qrPayload}
                  size={300}
                  level="M"
                  includeMargin={false}
                />
              </div>
              <p className="text-sm text-gray-400 text-center max-w-sm">
                Tap 6 times on the Android TV setup welcome screen to launch the QR scanner, then scan this code.
              </p>
            </div>
          ) : (
            <div className="text-gray-500 text-center">
              <p>Fill out the site configuration to generate a provisioning QR code.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
