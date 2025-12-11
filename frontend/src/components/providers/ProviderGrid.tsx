'use client'

import { useEffect, useState } from 'react'
import { BookingModal } from '../booking/BookingModal'
import { fetchProviders } from '@/lib/api/providers'
import { connectPriceStream, PriceUpdateMessage } from '@/lib/realtime/priceUpdates'

export function ProviderGrid() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [items, setItems] = useState<any[]>([])
  const [selected, setSelected] = useState<any | null>(null)
  const [flashes, setFlashes] = useState<Record<string, boolean>>({})

  useEffect(() => {
    let mounted = true
    let disconnectWs: (() => void) | null = null

    const applyPriceUpdate = (msg: PriceUpdateMessage) => {
      if (!mounted) return
      const matchId = msg.external_id ? msg.external_id : undefined
      setItems((prev) =>
        prev.map((it) => {
          const matches =
            (matchId && it.id.includes(matchId)) ||
            (msg.gpu_type && it.gpu === msg.gpu_type && (!msg.region || it.region === msg.region))
          if (!matches) return it
          const updated = { ...it, price_per_hour: msg.new_price }
          const id = it.id
          setFlashes((f) => ({ ...f, [id]: true }))
          setTimeout(() => setFlashes((f) => ({ ...f, [id]: false })), 2000)
          return updated
        })
      )
    }

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const url = new URL(window.location.href)
        const page = Number(url.searchParams.get('page') || '1')
        const gpu = url.searchParams.get('gpu') || undefined
        const memory_min = url.searchParams.get('memory_min') || undefined
        const resp = await fetchProviders({ page, per_page: 12, filters: { gpu, memory_min } })
        if (!mounted) return
        setItems(resp.items || [])
      } catch (err: any) {
        if (!mounted) return
        setError(err.message)
      } finally {
        mounted && setLoading(false)
      }
    }

    load()

    const onFilters = () => { load() }
      window.addEventListener('filters:changed', onFilters)
      window.addEventListener('popstate', onFilters)

      disconnectWs = connectPriceStream(applyPriceUpdate)

    return () => {
      mounted = false
      window.removeEventListener('filters:changed', onFilters)
      window.removeEventListener('popstate', onFilters)
      disconnectWs?.()
    }
  }, [])

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div className="card animate-pulse h-40" key={i} />
        ))}
      </div>
    )
  }

  if (error) {
    return <div className="card text-red-600">Error loading providers: {error}</div>
  }

  if (items.length === 0) {
    return <div className="card">No provider offers available. Connect your provider integrations to feed data into the dashboard.</div>
  }

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {items.map((p: any) => (
          <div key={p.id} className={`card ${flashes[p.id] ? 'price-flash' : ''}`}>
            <div className="flex items-start justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600">{p.name}</div>
                <div className="text-lg font-bold mt-2">{p.gpu || '—'}</div>
                <div className="mt-2 text-sm text-gray-500">{p.price_per_hour ? `$${p.price_per_hour} / hr` : 'Price N/A'}</div>
              </div>
              <div className="flex flex-col items-end">
                <button className="btn-primary" onClick={() => setSelected(p)}>Book</button>
                <a href={`/marketplace/${p.id}`} className="btn-secondary mt-2">Details</a>
              </div>
            </div>
          </div>
        ))}
      </div>

      <BookingModal open={!!selected} onClose={() => setSelected(null)} provider={selected} />

      <div className="mt-6 flex justify-center items-center space-x-3">
        <button className="btn-secondary" onClick={() => {
          const url = new URL(window.location.href)
          const page = Number(url.searchParams.get('page') || '1')
          if (page > 1) {
            url.searchParams.set('page', String(page - 1))
            window.history.pushState({}, '', url.toString())
            window.dispatchEvent(new Event('filters:changed'))
          }
        }}>Prev</button>
        <button className="btn-secondary" onClick={() => {
          const url = new URL(window.location.href)
          const page = Number(url.searchParams.get('page') || '1')
          url.searchParams.set('page', String(page + 1))
          window.history.pushState({}, '', url.toString())
          window.dispatchEvent(new Event('filters:changed'))
        }}>Next</button>
      </div>
    </div>
  )
}
