import { Header } from '@/components/layout/Header'

export default function ComparePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold">Compare Providers</h1>
        <p className="mt-4 text-gray-600">Select up to 4 providers to compare their specs, pricing and benchmarks.</p>
      </main>
    </div>
  )
}
