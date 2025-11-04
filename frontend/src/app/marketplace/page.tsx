import { Header } from '@/components/layout/Header'
import { ProviderGrid } from '@/components/providers/ProviderGrid'
import { FilterPanel } from '@/components/filters/FilterPanel'

export default function MarketplacePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-1">
            <FilterPanel />
          </div>
          <div className="lg:col-span-3">
            <ProviderGrid />
          </div>
        </div>
      </main>
    </div>
  )
}
