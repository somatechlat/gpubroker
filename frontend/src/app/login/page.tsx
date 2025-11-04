import LoginForm from '@/components/auth/LoginForm'
import { Header } from '@/components/layout/Header'

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />
      <main className="max-w-2xl mx-auto px-4 py-12">
        <LoginForm />
      </main>
    </div>
  )
}
