import { useEffect, useState } from 'react'

export function KPIOverview() {
  const [data, setData] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    async function load() {
      setLoading(true)
      try {
        const res = await fetch('/api/kpi', { cache: 'no-store', credentials: 'same-origin' })
        if (!res.ok) throw new Error('kpi fetch failed')
        const json = await res.json()
        if (mounted) setData(json)
      } catch (e) {
        // leave data null and fall back to placeholders
      } finally {
        mounted && setLoading(false)
      }
    }
    load()
    return () => { mounted = false }
  }, [])

  const cards = data ? [
    { label: 'Active Providers', value: data.active_providers },
    { label: 'Available GPUs', value: data.available_gpus },
    { label: 'Avg. Market Price', value: `$${data.avg_price_per_hour} / hr` },
    { label: 'Weekly Cost Savings', value: `$${data.weekly_savings}` }
  ] : [
    { label: 'Active Providers', value: '—' },
    { label: 'Available GPUs', value: '—' },
    { label: 'Avg. Market Price', value: '—' },
    { label: 'Weekly Cost Savings', value: '—' }
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="card">
          <h4 className="text-sm text-gray-500">{c.label}</h4>
          <p className="text-2xl font-bold">{loading ? '...' : c.value}</p>
        </div>
      ))}
    </div>
  )
}
