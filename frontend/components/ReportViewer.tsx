'use client'
import { usePipelineStore } from '@/lib/store'

export default function ReportViewer() {
  const { reportHtml, status, pdfUrl } = usePipelineStore()

  if (status !== 'completed' || !reportHtml) return null

  return (
    <div className="panel rounded-xl p-6 animate-in">
      <div className="flex items-end justify-between gap-3 mb-4 flex-wrap">
        <div>
          <p className="eyebrow mb-1">Classified · your eyes only</p>
          <h2 className="font-display text-2xl text-[var(--bone)]" style={{ letterSpacing: '-0.01em' }}>
            Competitive dossier
          </h2>
        </div>
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

      <div className="rounded-lg overflow-hidden border border-[var(--line-2)] ring-1 ring-black/50">
        <iframe
          srcDoc={reportHtml}
          title="Competitive intelligence dossier"
          className="w-full block"
          style={{ height: '78vh', background: '#fff' }}
          sandbox="allow-scripts allow-same-origin"
        />
      </div>
    </div>
  )
}
