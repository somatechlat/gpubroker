import Link from 'next/link'

export function Header() {
  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-3">
            <Link href="/">
              <a className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-primary-600 rounded-md" />
                <span className="font-semibold text-gray-900 dark:text-white">GPUBROKER</span>
              </a>
            </Link>
          </div>

          <nav className="flex items-center space-x-4">
            <Link href="/marketplace"><a className="text-sm text-gray-600 dark:text-gray-300">Marketplace</a></Link>
            <Link href="/analytics"><a className="text-sm text-gray-600 dark:text-gray-300">Analytics</a></Link>
            <Link href="/ai"><a className="text-sm text-gray-600 dark:text-gray-300">AI Assistant</a></Link>
            <button className="btn-secondary" onClick={async () => {
              try {
                await fetch('/api/auth/logout', { method: 'POST' })
                // reload to clear client state
                window.location.href = '/login'
              } catch (e) {
                window.location.href = '/login'
              }
            }}>Sign out</button>
          </nav>
        </div>
      </div>
    </header>
  )
}
