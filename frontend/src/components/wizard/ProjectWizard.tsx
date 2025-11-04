import { useState } from 'react'

export function ProjectWizard() {
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [region, setRegion] = useState('us-west')

  function exportJSON() {
    const payload = { name, region, created_at: new Date().toISOString() }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${name || 'project'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-4 border rounded">
      <h3 className="text-lg font-semibold">Project Wizard</h3>
      {step === 1 && (
        <div className="mt-3">
          <label className="block text-sm">Project name</label>
          <input className="input-field mt-1" value={name} onChange={e => setName(e.target.value)} />
          <div className="mt-4 flex justify-end">
            <button className="btn-primary" onClick={() => setStep(2)} disabled={!name}>Next</button>
          </div>
        </div>
      )}
      {step === 2 && (
        <div className="mt-3">
          <label className="block text-sm">Region</label>
          <select className="input-field mt-1" value={region} onChange={e => setRegion(e.target.value)}>
            <option value="us-west">US West</option>
            <option value="us-east">US East</option>
            <option value="eu-central">EU Central</option>
          </select>
          <div className="mt-4 flex justify-between">
            <button className="btn-secondary" onClick={() => setStep(1)}>Back</button>
            <div>
              <button className="btn-secondary mr-2" onClick={() => setStep(1)}>Back</button>
              <button className="btn-primary" onClick={exportJSON}>Export JSON</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
