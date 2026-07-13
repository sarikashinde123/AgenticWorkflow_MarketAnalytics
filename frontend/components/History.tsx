'use client'
import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

interface HistoryRun {
  run_id: string
  status: string
  business_name: string
  business_type: string
  location: string
  mode: string
  created_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  tokens_in: number
  tokens_out: number
  tokens_total: number
  report_ready: boolean
  pdf_url: string | null
  error: string | null
}

const fmt = (n: number) => n.toLocaleString()

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}m ${s}s`
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
    + ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

function estimateCost(tokensIn: number, tokensOut: number): string {
  // Sonnet 4.6: $3/M input, $15/M output (dominant model)
  const usd = (tokensIn * 3 + tokensOut * 15) / 1_000_000
  const inr = usd * 84
  if (inr < 1) return `₹${inr.toFixed(2)}`
  return `₹${inr.toFixed(1)}`
}

const STATUS_STYLE: Record<string, string> = {
  completed: 'bg-[rgba(55,208,166,.12)] text-[var(--confirm)] border-[rgba(55,208,166,.3)]',
  failed:    'bg-[rgba(242,84,45,.12)] text-[var(--alert)] border-[rgba(242,84,45,.3)]',
  running:   'bg-[rgba(245,165,36,.12)] text-[var(--signal)] border-[rgba(245,165,36,.3)]',
  pending:   'bg-[rgba(255,255,255,.04)] text-[var(--mute)] border-[var(--line-2)]',
}

export default function History() {
  const [runs, setRuns] = useState<HistoryRun[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/api/pipeline/history?limit=50`)
      .then(r => r.json())
      .then(data => { setRuns(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  function openReport(runId: string) {
    window.open(`${API}/api/pipeline/${runId}/report`, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="panel rounded-xl p-6 animate-in">
      <p className="eyebrow mb-1">Mission log</p>
      <h2 className="font-display text-[var(--bone)] mb-5" style={{ fontSize: '20px', letterSpacing: '-0.01em' }}>
        History
      </h2>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <svg className="spin h-5 w-5 text-[var(--signal)]" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="8" stroke="currentColor" strokeOpacity=".3" strokeWidth="2.5" />
            <path d="M20 12a8 8 0 0 0-8-8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
          <span className="ml-2 text-sm text-[var(--dim)]">Loading history...</span>
        </div>
      ) : runs.length === 0 ? (
        <p className="text-sm text-[var(--dim)] rounded-lg border border-[var(--line)] bg-[rgba(255,255,255,.015)] px-4 py-3">
          No runs yet. Start a scout to see your history here.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left" style={{ minWidth: '800px' }}>
            <thead>
              <tr className="border-b border-[var(--line-2)]">
                <th className="pb-2 pr-3 text-[10px] font-mono uppercase tracking-wider text-[var(--signal)]">Business</th>
                <th className="pb-2 pr-3 text-[10px] font-mono uppercase tracking-wider text-[var(--signal)]">Type</th>
                <th className="pb-2 pr-3 text-[10px] font-mono uppercase tracking-wider text-[var(--signal)]">Location</th>
                <th className="pb-2 pr-3 text-[10px] font-mono uppercase tracking-wider text-[var(--signal)]">Status</th>
                <th className="pb-2 pr-3 text-[10px] font-mono uppercase tracking-wider text-[var(--signal)]">Date</th>
                <th className="pb-2 pr-3 text-[10px] font-mono uppercase tracking-wider text-[var(--signal)] text-right">Time</th>
                <th className="pb-2 pr-3 text-[10px] font-mono uppercase tracking-wider text-[var(--signal)] text-right">Tokens</th>
                <th className="pb-2 pr-3 text-[10px] font-mono uppercase tracking-wider text-[var(--signal)] text-right">Cost</th>
                <th className="pb-2 text-[10px] font-mono uppercase tracking-wider text-[var(--signal)] text-center">Report</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(run => (
                <tr key={run.run_id} className="border-b border-[var(--line)] hover:bg-[rgba(255,255,255,.02)] transition-colors">
                  {/* Business Name */}
                  <td className="py-3 pr-3">
                    <span className="text-[13px] font-semibold text-[var(--bone)]">{run.business_name || '—'}</span>
                  </td>

                  {/* Type */}
                  <td className="py-3 pr-3">
                    <span className="text-[11px] font-mono text-[var(--mute)]">{run.business_type || '—'}</span>
                  </td>

                  {/* Location */}
                  <td className="py-3 pr-3">
                    <span className="text-[11px] font-mono text-[var(--mute)] block max-w-[180px] truncate">{run.location || '—'}</span>
                  </td>

                  {/* Status */}
                  <td className="py-3 pr-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider border ${STATUS_STYLE[run.status] || STATUS_STYLE.pending}`}>
                      {run.status}
                    </span>
                  </td>

                  {/* Date */}
                  <td className="py-3 pr-3">
                    <span className="text-[11px] font-mono text-[var(--dim)] whitespace-nowrap">
                      {run.created_at ? formatDate(run.created_at) : '—'}
                    </span>
                  </td>

                  {/* Duration */}
                  <td className="py-3 pr-3 text-right">
                    <span className="text-[11px] font-mono text-[var(--mute)] whitespace-nowrap">
                      {run.duration_seconds != null ? formatDuration(run.duration_seconds) : '—'}
                    </span>
                  </td>

                  {/* Tokens */}
                  <td className="py-3 pr-3 text-right">
                    {run.tokens_total > 0 ? (
                      <div>
                        <span className="text-[12px] font-mono font-semibold text-[var(--bone)]">{fmt(run.tokens_total)}</span>
                        <div className="text-[9px] font-mono text-[var(--dim)]">
                          ↑{fmt(run.tokens_in)} · ↓{fmt(run.tokens_out)}
                        </div>
                      </div>
                    ) : (
                      <span className="text-[11px] font-mono text-[var(--dim)]">—</span>
                    )}
                  </td>

                  {/* Cost */}
                  <td className="py-3 pr-3 text-right">
                    {run.tokens_total > 0 ? (
                      <span className="text-[12px] font-mono font-semibold text-[var(--signal)]">
                        {estimateCost(run.tokens_in, run.tokens_out)}
                      </span>
                    ) : (
                      <span className="text-[11px] font-mono text-[var(--dim)]">—</span>
                    )}
                  </td>

                  {/* Report */}
                  <td className="py-3 text-center">
                    {run.report_ready ? (
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => openReport(run.run_id)}
                          className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider px-2.5 py-1.5 rounded-md
                                     border border-[rgba(245,165,36,.35)] text-[var(--signal)] bg-[rgba(245,165,36,.08)]
                                     hover:bg-[rgba(245,165,36,.18)] transition-colors"
                        >
                          <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none"><path d="M14 4h6v6M20 4l-9 9M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          View
                        </button>
                        {run.pdf_url && (
                          <a
                            href={`${API}${run.pdf_url}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            download
                            className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider px-2.5 py-1.5 rounded-md
                                       border border-[rgba(55,208,166,.35)] text-[var(--confirm)] bg-[rgba(55,208,166,.08)]
                                       hover:bg-[rgba(55,208,166,.18)] transition-colors"
                          >
                            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                            PDF
                          </a>
                        )}
                      </div>
                    ) : (
                      <span className="text-[11px] font-mono text-[var(--dim)]">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
