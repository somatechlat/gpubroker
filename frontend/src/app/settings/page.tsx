'use client'

import { useState, useEffect } from 'react'
import { Header } from '@/components/layout/Header'
import { Button } from '@/components/ui/Button'

interface IntegrationStatus {
  provider: string
  status: 'active' | 'error' | 'not_configured'
  message?: string
  last_checked: string
}

const API_BASE_URL =
  (process.env.NEXT_PUBLIC_PROVIDER_API_URL ||
    process.env.PROVIDER_API_URL ||
    '').replace(/\/$/, '')

export default function SettingsPage() {
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([])
  const [loading, setLoading] = useState(true)

  // Form State
  const [selectedProvider, setSelectedProvider] = useState('vastai')
  const [apiKey, setApiKey] = useState('')
  const [apiUrl, setApiUrl] = useState('')
  const [saveStatus, setSaveStatus] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const fetchIntegrations = async () => {
    try {
      if (!API_BASE_URL) {
        setSaveStatus('❌ Configure NEXT_PUBLIC_PROVIDER_API_URL first.')
        return
      }
      const res = await fetch(`${API_BASE_URL}/config/integrations`)
      if (res.ok) {
        const data = await res.json()
        setIntegrations(data)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchIntegrations()
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setSaveStatus(null)

    try {
      if (!API_BASE_URL) {
        throw new Error('NEXT_PUBLIC_PROVIDER_API_URL is not set')
      }
      const res = await fetch(`${API_BASE_URL}/config/integrations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: selectedProvider,
          api_key: apiKey,
          api_url: apiUrl || undefined
        })
      })

      if (!res.ok) throw new Error('Failed to save')

      setSaveStatus('✅ Saved successfully.')
      setApiKey('') // Clear sensitive field
      fetchIntegrations() // Refresh list
    } catch (err) {
      console.error(err)
      setSaveStatus('❌ Error saving configuration.')
    } finally {
      setSaving(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <span className="h-3 w-3 rounded-full bg-green-500 inline-block mr-2" title="Connected" />
      case 'error': return <span className="h-3 w-3 rounded-full bg-red-500 inline-block mr-2" title="Error" />
      default: return <span className="h-3 w-3 rounded-full bg-gray-300 inline-block mr-2" title="Not Configured" />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />

      <main className="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 md:grid-cols-2 gap-8">

        {/* Left Column: Active Integrations List */}
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Active Integrations
          </h2>
          {loading ? (
            <div className="animate-pulse space-y-4">
              {[...Array(3)].map((_, i) => <div key={i} className="h-16 bg-white rounded-lg shadow" />)}
            </div>
          ) : (
            <div className="space-y-4">
              {integrations.map((item) => (
                <div key={item.provider} className="bg-white dark:bg-gray-800 shadow rounded-lg p-4 flex items-center justify-between">
                  <div className="flex items-center">
                    {getStatusIcon(item.status)}
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-white capitalize">{item.provider}</h3>
                      <p className="text-xs text-gray-500 capitalize">{item.status.replace('_', ' ')}</p>
                    </div>
                  </div>
                  {item.status !== 'not_configured' && (
                    <Button variant="ghost" className="text-xs text-red-600 hover:text-red-800">
                      Disconnect
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Add/Edit Integration Form */}
        <div>
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 sticky top-8">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
              Connect New Provider
            </h2>

            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Select Provider
                </label>
                <select
                  value={selectedProvider}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 bg-gray-50 dark:bg-gray-700 dark:text-white capitalize"
                >
                  {integrations.map(i => (
                    <option key={i.provider} value={i.provider}>{i.provider}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  API Key / Token
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 bg-gray-50 dark:bg-gray-700 dark:text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  API Base URL (Optional Override)
                </label>
                <input
                  type="text"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 bg-gray-50 dark:bg-gray-700 dark:text-white"
                />
              </div>

              <div className="pt-4">
                <Button type="submit" disabled={saving}>
                  {saving ? 'Connecting...' : 'Connect Provider'}
                </Button>
              </div>

              {saveStatus && (
                <div className={`p-4 rounded-md ${saveStatus.startsWith('✅') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                  {saveStatus}
                </div>
              )}
            </form>
          </div>
        </div>

      </main>
    </div>
  )
}
