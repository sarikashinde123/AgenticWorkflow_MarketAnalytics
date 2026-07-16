'use client'
import { useState } from 'react'
import { usePipelineStore } from '@/lib/store'
import Radar from './Radar'
import LocationSearch from './LocationSearch'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
type Mode = 'market_overview' | 'gap_analysis'

export default function PipelineForm() {
  const { startPipeline, status, setMapPreview, error, strictNoMatch, reset } = usePipelineStore()
  const [mode, setMode] = useState<Mode>('market_overview')
  const [form, setForm] = useState({
    business_name: '',
    business_type: '',
    location: '',
    search_radius_km: 5,
    max_competitors: 6,
  })
  const [coords, setCoords] = useState<{ lat: number | null; lng: number | null }>({ lat: null, lng: null })
  const [useOpus, setUseOpus] = useState(false)
  const [strictMatch, setStrictMatch] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const busy = status === 'running' || uploading
  const radarState = busy ? 'scanning' : status === 'completed' ? 'complete' : status === 'failed' ? 'failed' : 'idle'

  function handle(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target
    const parsed = (name === 'search_radius_km' || name === 'max_competitors') ? Number(value) : value
    setForm(f => ({ ...f, [name]: parsed }))
    if (name === 'search_radius_km' && coords.lat != null && coords.lng != null) {
      setMapPreview({ lat: coords.lat, lng: coords.lng, radiusKm: Number(value), label: form.business_name })
    }
    if (name === 'business_name' && coords.lat != null && coords.lng != null) {
      setMapPreview({ lat: coords.lat, lng: coords.lng, radiusKm: form.search_radius_km, label: value })
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    if (!form.business_name || !form.business_type || !form.location) return

    if (mode === 'market_overview') {
      startPipeline({ ...form, mode, use_opus: useOpus, strict_match: strictMatch, latitude: coords.lat, longitude: coords.lng })
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
      startPipeline({ ...form, mode, use_opus: useOpus, strict_match: strictMatch, own_offerings: text, latitude: coords.lat, longitude: coords.lng })
    } catch (e) {
      setUploading(false)
      setErr(e instanceof Error ? e.message : 'Upload failed.')
    }
  }

  return (
    <form onSubmit={submit} className="panel rounded-xl p-6 animate-in">
      <p className="eyebrow mb-1">Operation setup</p>
      <h2 className="font-display text-[var(--bone)] mb-4" style={{ fontSize: '20px', letterSpacing: '-0.01em' }}>
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
          <LocationSearch
            value={form.location}
            onChange={(place) => {
              setForm(f => ({ ...f, location: place.formatted_address }))
              setCoords({ lat: place.lat, lng: place.lng })
              if (place.lat != null && place.lng != null) {
                setMapPreview({ lat: place.lat, lng: place.lng, radiusKm: form.search_radius_km, label: form.business_name })
              } else {
                setMapPreview(null)
              }
            }}
            disabled={busy}
          />
          {coords.lat != null && (
            <p className="text-[10px] font-mono text-[var(--dim)] mt-1.5 flex items-center gap-1.5">
              <svg className="h-3 w-3 text-[var(--confirm)]" viewBox="0 0 24 24" fill="none">
                <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              {coords.lat.toFixed(4)}, {coords.lng!.toFixed(4)}
            </p>
          )}
        </Field>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="radius" className="eyebrow font-bold" style={{ letterSpacing: '.16em' }}>Search radius</label>
            <span className="font-mono text-sm text-[var(--signal)]">{form.search_radius_km} km</span>
          </div>
          <input id="radius" type="range" name="search_radius_km" min={1} max={25}
                 value={form.search_radius_km} onChange={handle} disabled={busy} className="w-full"
                 style={{ background: `linear-gradient(90deg, var(--signal) ${((form.search_radius_km - 1) / 24) * 100}%, rgba(210,190,150,0.18) ${((form.search_radius_km - 1) / 24) * 100}%)` }} />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="max_comp" className="eyebrow font-bold" style={{ letterSpacing: '.16em' }}>Max competitors</label>
            <span className="font-mono text-sm text-[var(--signal)]">{form.max_competitors}</span>
          </div>
          <input id="max_comp" type="range" name="max_competitors" min={3} max={15}
                 value={form.max_competitors} onChange={handle} disabled={busy} className="w-full"
                 style={{ background: `linear-gradient(90deg, var(--signal) ${((form.max_competitors - 3) / 12) * 100}%, rgba(210,190,150,0.18) ${((form.max_competitors - 3) / 12) * 100}%)` }} />
        </div>

        <label className={`flex items-center gap-3 cursor-pointer select-none ${busy ? 'opacity-50 pointer-events-none' : ''}`}>
          <input type="checkbox" checked={useOpus} onChange={e => setUseOpus(e.target.checked)} disabled={busy}
                 className="sr-only peer" />
          <span className="relative w-9 h-5 rounded-full border border-[var(--line-2)] bg-[rgba(255,255,255,.04)] peer-checked:bg-[rgba(129,140,248,.25)] peer-checked:border-[rgba(129,140,248,.5)] transition-colors after:content-[''] after:absolute after:top-[3px] after:left-[3px] after:w-3 after:h-3 after:rounded-full after:bg-[var(--dim)] peer-checked:after:bg-[#818cf8] peer-checked:after:translate-x-4 after:transition-transform" />
          <span className="eyebrow" style={{ letterSpacing: '.16em' }}>Faster processing</span>
          <span className="text-[10px] font-mono text-[var(--mute)]">{useOpus ? 'OPUS' : 'SONNET'}</span>
        </label>

        <label className={`flex items-center gap-3 cursor-pointer select-none ${busy ? 'opacity-50 pointer-events-none' : ''}`}>
          <input type="checkbox" checked={strictMatch} onChange={e => setStrictMatch(e.target.checked)} disabled={busy}
                 className="sr-only peer" />
          <span className="relative w-9 h-5 rounded-full border border-[var(--line-2)] bg-[rgba(255,255,255,.04)] peer-checked:bg-[rgba(52,211,153,.25)] peer-checked:border-[rgba(52,211,153,.5)] transition-colors after:content-[''] after:absolute after:top-[3px] after:left-[3px] after:w-3 after:h-3 after:rounded-full after:bg-[var(--dim)] peer-checked:after:bg-[#34d399] peer-checked:after:translate-x-4 after:transition-transform" />
          <span className="eyebrow" style={{ letterSpacing: '.16em' }}>Strict match</span>
          <span className="text-[10px] font-mono text-[var(--mute)]">{strictMatch ? 'EXACT' : 'GENERAL'}</span>
        </label>

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

      {strictNoMatch && (
        <div className="mt-4 rounded-lg border border-[rgba(245,165,36,.35)] bg-[rgba(245,165,36,.06)] px-4 py-4">
          <div className="flex items-start gap-3">
            <svg className="h-5 w-5 text-[var(--signal)] shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
              <path d="M12 8v4m0 4h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <div>
              <p className="text-sm font-semibold text-[var(--bone)] mb-1">No exact competitors found</p>
              <p className="text-[12px] text-[var(--dim)] mb-3">{error}</p>
              <button
                type="button"
                onClick={() => { reset(); setStrictMatch(false) }}
                className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider px-3 py-2 rounded-md
                           border border-[rgba(52,211,153,.4)] text-[#34d399] bg-[rgba(52,211,153,.08)]
                           hover:bg-[rgba(52,211,153,.18)] transition-colors"
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                  <path d="M1 4v6h6M23 20v-6h-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Switch to General mode
              </button>
            </div>
          </div>
        </div>
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
          ) : mode === 'gap_analysis' ? 'Run gap analysis' : 'Run scout'}
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
      <label htmlFor={id} className="eyebrow block mb-1.5 font-bold" style={{ letterSpacing: '.16em' }}>{label}</label>
      {children}
    </div>
  )
}
