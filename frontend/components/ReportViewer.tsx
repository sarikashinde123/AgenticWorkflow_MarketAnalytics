'use client'
import { usePipelineStore } from '@/lib/store'

export default function ReportViewer() {
  const { reportHtml, status, pdfUrl } = usePipelineStore()

  if (status !== 'completed' || !reportHtml) return null

  // Open the full dossier as a standalone page in a new browser tab.
  function openInNewTab() {
    const blob = new Blob([reportHtml], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    // Give the new tab time to load before releasing the object URL.
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }

  return (
    <div className="panel rounded-xl p-6 animate-in">
      <div className="flex items-end justify-between gap-3 mb-4 flex-wrap">
        <div>
          <p className="eyebrow mb-1">Classified · your eyes only</p>
          <h2 className="font-display text-2xl text-[var(--bone)]" style={{ letterSpacing: '-0.01em' }}>
            Competitive dossier
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button" onClick={openInNewTab}
            className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-wider px-4 py-2.5 rounded-md
                       border border-[rgba(245,165,36,.35)] text-[var(--signal)] bg-[rgba(245,165,36,.1)]
                       hover:bg-[rgba(245,165,36,.18)] transition-colors">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none"><path d="M14 4h6v6M20 4l-9 9M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Open in new tab
          </button>
          {pdfUrl && (
            <a href={pdfUrl} target="_blank" rel="noopener noreferrer"
               className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-wider px-4 py-2.5 rounded-md
                          border border-[rgba(55,208,166,.35)] text-[var(--confirm)] bg-[rgba(55,208,166,.1)]
                          hover:bg-[rgba(55,208,166,.18)] transition-colors">
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
              Download PDF
            </a>
          )}
        </div>
      </div>

      <p className="text-sm text-[var(--dim)] rounded-lg border border-[var(--line)] bg-[rgba(255,255,255,.015)] px-4 py-3 leading-relaxed">
        Your dossier is ready. Open it in a new tab for the full report, or download the PDF.
      </p>
    </div>
  )
}
