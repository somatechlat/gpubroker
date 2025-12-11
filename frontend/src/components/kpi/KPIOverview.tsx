'use client'

import { useEffect, useState } from 'react'

export function KPIOverview() {
  const [data, setData] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch('/api/kpi', { cache: 'no-store', credentials: 'same-origin' })
        if (!res.ok) throw new Error(`kpi fetch failed (${res.status})`)
        const json = await res.json()
        if (mounted) setData(json)
      } catch (e) {
        if (mounted) setError((e as Error).message || 'Failed to load KPI data')
      } finally {
        mounted && setLoading(false)
      }
    }
    load()
    return () => { mounted = false }
  }, [])

  const cards = data ? [
    { label: 'Providers Tracked', value: data.total_providers ?? '—' },
    { label: 'Offers Ingested', value: data.total_offers ?? '—' },
    { label: 'Avg Market Price', value: data.avg_market_price != null ? `$${Number(data.avg_market_price).toFixed(4)} / hr` : '—' },
    { label: 'Price Trend (7d)', value: data.price_trend_7d != null ? `${Number(data.price_trend_7d).toFixed(2)}%` : '—' },
  ] : [
    { label: 'Providers Tracked', value: '—' },
    { label: 'Offers Ingested', value: '—' },
    { label: 'Avg Market Price', value: '—' },
    { label: 'Price Trend (7d)', value: '—' },
  ]

  return (
    <div className="space-y-3">
      {error && <div className="card text-red-600 text-sm">KPI error: {error}</div>}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="card">
            <h4 className="text-sm text-gray-500">{c.label}</h4>
            <p className="text-2xl font-bold">{loading ? '...' : c.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
