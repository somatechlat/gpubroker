import { Header } from '@/components/layout/Header'
import { ChatUI } from '@/components/ai/ChatUI'

export default function AIPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold">AI Assistant</h1>
        <p className="mt-4 text-gray-600">Conversational assistant and project wizard UI.</p>
        {!process.env.NEXT_PUBLIC_AI_API_URL && (
          <div className="mt-4 rounded border border-yellow-300 bg-yellow-50 text-yellow-800 px-4 py-3 text-sm">
            Configure NEXT_PUBLIC_AI_API_URL to connect the assistant to the backend service.
          </div>
        )}
        <div className="mt-6">
          <ChatUI />
        </div>
      </main>
    </div>
  )
}
