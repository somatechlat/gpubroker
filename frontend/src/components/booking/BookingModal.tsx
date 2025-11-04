import { useState } from 'react'

export function BookingModal({ open, onClose, provider }: { open: boolean; onClose: () => void; provider: any | null }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open || !provider) return null

  async function confirm() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ provider_id: provider.id, sku: provider.gpu })
      })
      if (!res.ok) throw new Error('booking failed')
      onClose()
      // optionally show success toast (left as TODO)
    } catch (e: any) {
      setError(e.message || 'Booking error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black opacity-40" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-lg p-6 z-10 w-full max-w-md">
        <h3 className="text-lg font-semibold">Book {provider.name}</h3>
        <p className="text-sm text-gray-600 mt-2">SKU: {provider.gpu}</p>
        <div className="mt-4">
          {error && <div className="text-red-600 mb-2">{error}</div>}
          <div className="flex justify-end space-x-2">
            <button className="btn-secondary" onClick={onClose} disabled={loading}>Cancel</button>
            <button className="btn-primary" onClick={confirm} disabled={loading}>{loading ? 'Booking…' : 'Confirm booking'}</button>
          </div>
        </div>
      </div>
    </div>
  )
}
