'use client'

export function FilterPanel() {
  const complianceOptions = [
    { value: 'gdpr_compliant', label: 'GDPR' },
    { value: 'soc2_compliant', label: 'SOC2' },
    { value: 'hipaa_compliant', label: 'HIPAA' },
    { value: 'iso27001', label: 'ISO27001' },
  ]

  const applyFilters = (form: HTMLFormElement) => {
    const fd = new FormData(form)
    const params = new URLSearchParams()

    // Simple scalar fields
    const scalarFields = [
      'gpu',
      'gpu_memory_min',
      'gpu_memory_max',
      'price_min',
      'price_max',
      'region',
      'availability',
      'provider_name',
    ]
    scalarFields.forEach((field) => {
      const v = fd.get(field)
      if (v !== null && String(v).length > 0) {
        params.set(field, String(v))
      }
    })

    // Compliance tags (multi-select)
    const complianceTags = fd.getAll('compliance_tags').map(String).filter(Boolean)
    if (complianceTags.length) {
      params.set('compliance_tags', complianceTags.join(','))
    }

    const url = new URL(window.location.href)
    url.search = params.toString()
    window.history.pushState({}, '', url.toString())
    window.dispatchEvent(new Event('filters:changed'))
  }

  return (
    <div className="card">
      <h3 className="text-lg font-medium mb-3">Filters</h3>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <div>
          <label className="text-sm text-gray-600">GPU Type</label>
          <input name="gpu" className="input-field mt-1" type="text" placeholder="e.g., A100, H100, L40S" />
        </div>
        <div>
          <label className="text-sm text-gray-600">Memory (GB) min</label>
          <input name="gpu_memory_min" className="input-field mt-1" type="number" min={1} max={1024} />
        </div>
        <div>
          <label className="text-sm text-gray-600">Memory (GB) max</label>
          <input name="gpu_memory_max" className="input-field mt-1" type="number" min={1} max={1024} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm text-gray-600">Price min ($/h)</label>
            <input name="price_min" className="input-field mt-1" type="number" min={0} step="0.01" />
          </div>
          <div>
            <label className="text-sm text-gray-600">Price max ($/h)</label>
            <input name="price_max" className="input-field mt-1" type="number" min={0} step="0.01" />
          </div>
        </div>
        <div>
          <label className="text-sm text-gray-600">Region</label>
          <input name="region" className="input-field mt-1" type="text" placeholder="e.g., us-east, eu-west" />
        </div>
        <div>
          <label className="text-sm text-gray-600">Availability</label>
          <select name="availability" className="input-field mt-1" defaultValue="">
            <option value="">Any</option>
            <option value="available">Available</option>
            <option value="stale">Stale</option>
            <option value="unavailable">Unavailable</option>
          </select>
        </div>
        <div>
          <label className="text-sm text-gray-600">Compliance</label>
          <div className="mt-2 space-y-2">
            {complianceOptions.map((opt) => (
              <label key={opt.value} className="flex items-center space-x-2 text-sm text-gray-700">
                <input type="checkbox" name="compliance_tags" value={opt.value} className="h-4 w-4" />
                <span>{opt.label}</span>
              </label>
            ))}
          </div>
        </div>
        <div>
          <label className="text-sm text-gray-600">Provider</label>
          <input name="provider_name" className="input-field mt-1" type="text" placeholder="e.g., runpod, vastai" />
        </div>
        <div className="flex space-x-2">
          <button
            className="btn-primary"
            onClick={(e) => {
              e.preventDefault()
              const form = (e.currentTarget as HTMLElement).closest('form') as HTMLFormElement
              applyFilters(form)
            }}
          >
            Apply
          </button>
          <button
            className="btn-secondary"
            onClick={(e) => {
              e.preventDefault()
              const url = new URL(window.location.href)
              url.search = ''
              window.history.pushState({}, '', url.toString())
              window.dispatchEvent(new Event('filters:changed'))
            }}
          >
            Reset
          </button>
        </div>
      </form>
    </div>
  )
}
