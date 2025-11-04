import { Header } from '@/components/layout/Header'

export default function ProviderDetail({ params }: { params: { id: string } }) {
  // Per repository policy this UI contains no mocked provider data or fake API calls.
  // This page is a UI placeholder which will be wired to real provider data at integration time.

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold">Provider details</h1>
        <div className="mt-4 card">
          <p className="text-gray-600">This is a UI placeholder for provider <strong>{params.id}</strong>.</p>
          <p className="mt-2 text-sm text-gray-500">No mock data is rendered here. Integrate real provider APIs when ready.</p>
        </div>
      </main>
    </div>
  )
}
