'use client'
import { useState } from 'react'
import { usePipelineStore } from '@/lib/store'
import Radar from './Radar'

export default function PipelineForm() {
  const { startPipeline, status } = usePipelineStore()
  const [form, setForm] = useState({
    business_name: '',
    business_type: '',
    location: '',
    search_radius_km: 5,
  })

  const busy = status === 'running'
  const radarState = busy ? 'scanning' : status === 'completed' ? 'complete' : status === 'failed' ? 'failed' : 'idle'

  function handle(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target
    setForm(f => ({ ...f, [name]: name === 'search_radius_km' ? Number(value) : value }))
  }

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.business_name || !form.business_type || !form.location) return
    startPipeline(form)
  }

  return (
    <form onSubmit={submit} className="panel rounded-xl p-6 animate-in">
      <p className="eyebrow mb-1">Operation setup</p>
      <h2 className="font-display text-2xl text-[var(--bone)] mb-5" style={{ letterSpacing: '-0.01em' }}>
        Define your target
      </h2>

      {/* Signature: live radar scope */}
      <div className="flex justify-center py-2 mb-5">
        <Radar radiusKm={form.search_radius_km} state={radarState} />
      </div>

      <div className="space-y-4">
        <Field id="business_name" label="Business name">
          <input id="business_name" name="business_name" value={form.business_name} onChange={handle}
                 placeholder="Sara Bakery" required disabled={busy} className="field" />
        </Field>
        <Field id="business_type" label="Sector">
          <input id="business_type" name="business_type" value={form.business_type} onChange={handle}
                 placeholder="Bakery · Gym · Salon · Clinic" required disabled={busy} className="field" />
        </Field>
        <Field id="location" label="Location">
          <input id="location" name="location" value={form.location} onChange={handle}
                 placeholder="Baner, Pune" required disabled={busy} className="field" />
        </Field>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="radius" className="eyebrow" style={{ letterSpacing: '.16em' }}>Search radius</label>
            <span className="font-mono text-sm text-[var(--signal)]">{form.search_radius_km} km</span>
          </div>
          <input id="radius" type="range" name="search_radius_km" min={1} max={25}
                 value={form.search_radius_km} onChange={handle} disabled={busy} className="w-full"
                 style={{ background: `linear-gradient(90deg, var(--signal) ${((form.search_radius_km - 1) / 24) * 100}%, rgba(210,190,150,0.18) ${((form.search_radius_km - 1) / 24) * 100}%)` }} />
        </div>
      </div>

      <button type="submit" disabled={busy} className="btn-recon mt-6">
        <span className="flex items-center justify-center gap-2">
          {busy ? (
            <>
              <svg className="spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="8" stroke="currentColor" strokeOpacity=".35" strokeWidth="3" />
                <path d="M20 12a8 8 0 0 0-8-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>
              Scanning…
            </>
          ) : 'Run recon'}
        </span>
      </button>
    </form>
  )
}

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="eyebrow block mb-1.5" style={{ letterSpacing: '.16em' }}>{label}</label>
      {children}
    </div>
  )
}
