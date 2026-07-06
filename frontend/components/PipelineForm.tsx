'use client'
import { useState } from 'react'
import { usePipelineStore } from '@/lib/store'
import Radar from './Radar'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
type Mode = 'market_overview' | 'gap_analysis'

export default function PipelineForm() {
  const { startPipeline, status } = usePipelineStore()
  const [mode, setMode] = useState<Mode>('market_overview')
  const [form, setForm] = useState({
    business_name: '',
    business_type: '',
    location: '',
    search_radius_km: 5,
  })
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const busy = status === 'running' || uploading
  const radarState = busy ? 'scanning' : status === 'completed' ? 'complete' : status === 'failed' ? 'failed' : 'idle'

  function handle(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target
    setForm(f => ({ ...f, [name]: name === 'search_radius_km' ? Number(value) : value }))
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    if (!form.business_name || !form.business_type || !form.location) return

    if (mode === 'market_overview') {
      startPipeline({ ...form, mode })
      return
    }

    // Gap analysis: extract the owner's offerings from their PDF first.
    if (!file) {
      setErr('Upload a PDF of your offerings to run a gap analysis.')
      return
    }
    try {
      setUploading(true)
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`${API}/api/offerings/extract`, { method: 'POST', body: fd })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || 'Could not read that PDF.')
      }
      const { text } = await res.json()
      setUploading(false)
      startPipeline({ ...form, mode, own_offerings: text })
    } catch (e) {
      setUploading(false)
      setErr(e instanceof Error ? e.message : 'Upload failed.')
    }
  }

  return (
    <form onSubmit={submit} className="panel rounded-xl p-6 animate-in">
      <p className="eyebrow mb-1">Operation setup</p>
      <h2 className="font-display text-2xl text-[var(--bone)] mb-4" style={{ letterSpacing: '-0.01em' }}>
        Define your target
      </h2>

      {/* Mode toggle */}
      <div className="grid grid-cols-2 gap-2 mb-5" role="tablist" aria-label="Analysis mode">
        <ModeButton
          active={mode === 'market_overview'} disabled={busy}
          onClick={() => setMode('market_overview')}
          title="Market overview" desc="Scope competitors for a new business"
        />
        <ModeButton
          active={mode === 'gap_analysis'} disabled={busy}
          onClick={() => setMode('gap_analysis')}
          title="Gap analysis" desc="Benchmark your own offerings"
        />
      </div>

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

        {/* Gap analysis: upload own offerings */}
        {mode === 'gap_analysis' && (
          <Field id="offerings" label="Your offerings (PDF)">
            <label className={`flex items-center gap-3 rounded-lg border border-dashed px-4 py-3 cursor-pointer transition-colors
                               ${file ? 'border-[rgba(245,165,36,.4)] bg-[rgba(245,165,36,.06)]' : 'border-[var(--line-2)] hover:border-[rgba(210,190,150,.4)]'}
                               ${busy ? 'opacity-50 pointer-events-none' : ''}`}>
              <svg className="h-5 w-5 text-[var(--signal)] shrink-0" viewBox="0 0 24 24" fill="none"><path d="M12 16V4m0 0L8 8m4-4l4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
              <span className="text-sm text-[var(--dim)] truncate">
                {file ? file.name : 'Upload your services / menu / brochure PDF'}
              </span>
              <input type="file" accept="application/pdf" className="hidden" disabled={busy}
                     onChange={e => { setErr(null); setFile(e.target.files?.[0] ?? null) }} />
            </label>
            <p className="text-[11px] text-[var(--mute)] mt-1.5">We read the text to compare against the market.</p>
          </Field>
        )}
      </div>

      {err && (
        <p className="mt-4 text-sm font-mono text-[var(--alert)] bg-[rgba(242,84,45,.08)] border border-[rgba(242,84,45,.2)] rounded-lg px-3.5 py-2.5">
          {err}
        </p>
      )}

      <button type="submit" disabled={busy} className="btn-recon mt-6">
        <span className="flex items-center justify-center gap-2">
          {busy ? (
            <>
              <svg className="spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="8" stroke="currentColor" strokeOpacity=".35" strokeWidth="3" />
                <path d="M20 12a8 8 0 0 0-8-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>
              {uploading ? 'Reading PDF…' : 'Scanning…'}
            </>
          ) : mode === 'gap_analysis' ? 'Run gap analysis' : 'Run recon'}
        </span>
      </button>
    </form>
  )
}

function ModeButton({ active, disabled, onClick, title, desc }: {
  active: boolean; disabled: boolean; onClick: () => void; title: string; desc: string
}) {
  return (
    <button type="button" role="tab" aria-selected={active} disabled={disabled} onClick={onClick}
      className={`text-left rounded-lg border px-3.5 py-3 transition-colors ${
        active
          ? 'border-[rgba(245,165,36,.5)] bg-[rgba(245,165,36,.08)]'
          : 'border-[var(--line-2)] bg-[rgba(255,255,255,.015)] hover:border-[rgba(210,190,150,.35)]'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
      <div className={`font-mono text-[11px] uppercase tracking-wider ${active ? 'text-[var(--signal)]' : 'text-[var(--dim)]'}`}>{title}</div>
      <div className="text-[11px] text-[var(--mute)] mt-1 leading-snug">{desc}</div>
    </button>
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
