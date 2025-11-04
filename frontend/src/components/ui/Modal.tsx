export function Modal({ children, open }: { children: React.ReactNode; open: boolean }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black opacity-40" />
      <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 z-10 w-full max-w-2xl">{children}</div>
    </div>
  )
}
