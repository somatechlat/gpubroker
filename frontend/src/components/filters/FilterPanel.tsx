export function FilterPanel() {
  // simple URL-driven filters: gpu and memory_min for now
  // This keeps state in the URL so ProviderGrid can read it without lifting state
  return (
    <div className="card">
      <h3 className="text-lg font-medium mb-3">Filters</h3>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <div>
          <label className="text-sm text-gray-600">GPU Type</label>
          <select name="gpu" className="input-field mt-1" defaultValue="">
            <option value="">Any</option>
            <option value="A100">A100</option>
            <option value="V100">V100</option>
          </select>
        </div>
        <div>
          <label className="text-sm text-gray-600">Memory (GB) min</label>
          <input name="memory_min" className="input-field mt-1" type="number" min={8} max={1024} />
        </div>
        <div className="flex space-x-2">
          <button className="btn-primary" onClick={(e) => {
            e.preventDefault()
            const form = (e.target as HTMLElement).closest('form') as HTMLFormElement
            const fd = new FormData(form)
            const params = new URLSearchParams()
            for (const [k, v] of fd.entries()) {
              if (String(v).length) params.set(k, String(v))
            }
            const q = params.toString()
            const url = new URL(window.location.href)
            url.search = q
            window.history.pushState({}, '', url.toString())
            // dispatch an event so ProviderGrid can optionally listen
            window.dispatchEvent(new Event('filters:changed'))
          }}>Apply</button>
          <button className="btn-secondary" onClick={(e) => {
            e.preventDefault()
            const url = new URL(window.location.href)
            url.search = ''
            window.history.pushState({}, '', url.toString())
            window.dispatchEvent(new Event('filters:changed'))
          }}>Reset</button>
        </div>
      </form>
    </div>
  )
}
