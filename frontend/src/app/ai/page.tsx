import { Header } from '@/components/layout/Header'
import { ChatUI } from '@/components/ai/ChatUI'

export default function AIPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold">AI Assistant</h1>
        <p className="mt-4 text-gray-600">Conversational assistant and project wizard UI.</p>
        <div className="mt-6">
          <ChatUI />
        </div>
      </main>
    </div>
  )
}
