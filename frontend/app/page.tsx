'use client'
import { useState } from 'react'
import PipelineForm from '@/components/PipelineForm'
import PipelineStatus from '@/components/PipelineStatus'
import CompetitorMap from '@/components/CompetitorMap'
import ReportViewer from '@/components/ReportViewer'
import History from '@/components/History'

type Tab = 'scout' | 'history'

export default function Home() {
  const [tab, setTab] = useState<Tab>('scout')

  return (
    <main className="min-h-screen">
      {/* Terminal top bar */}
      <header className="sticky top-0 z-20 border-b border-[var(--line)] backdrop-blur-md bg-[var(--ink)]/75">
        <div className="mx-auto max-w-6xl px-5 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg className="h-7 w-7 text-[var(--signal)]" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" strokeOpacity=".5" />
              <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.5" />
              <path d="M12 1v4M12 19v4M1 12h4M19 12h4" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="12" cy="12" r="1.5" fill="currentColor" />
            </svg>
            <div className="leading-none">
              <div className="font-display text-2xl text-[var(--bone)] tracking-wide">GeoScout</div>
              <div className="italic text-[var(--bone)]" style={{ fontSize: '10px', letterSpacing: '.28em' }}>Proximity Intelligence, Simplified!</div>
            </div>
          </div>

          {/* Tab navigation */}
          <nav className="flex items-center gap-1 ml-8">
            <button
              onClick={() => setTab('scout')}
              className={`px-4 py-1.5 rounded-md font-mono text-[11px] uppercase tracking-wider transition-colors ${
                tab === 'scout'
                  ? 'bg-[rgba(245,165,36,.15)] text-[var(--signal)] border border-[rgba(245,165,36,.35)]'
                  : 'text-[var(--dim)] hover:text-[var(--mute)] border border-transparent'
              }`}
            >
              Scout
            </button>
            <button
              onClick={() => setTab('history')}
              className={`px-4 py-1.5 rounded-md font-mono text-[11px] uppercase tracking-wider transition-colors ${
                tab === 'history'
                  ? 'bg-[rgba(245,165,36,.15)] text-[var(--signal)] border border-[rgba(245,165,36,.35)]'
                  : 'text-[var(--dim)] hover:text-[var(--mute)] border border-transparent'
              }`}
            >
              History
            </button>
          </nav>

          <div className="flex-1" />

          <div className="flex items-center gap-2 font-mono text-[11px] text-[var(--dim)]">
            <span className="inline-flex h-1.5 w-1.5 rounded-full bg-[var(--confirm)]" style={{ boxShadow: '0 0 6px var(--confirm)' }} />
            <span className="hidden sm:inline">SYSTEM</span> ONLINE
          </div>
        </div>
      </header>

      {/* Content */}
      <section className="mx-auto max-w-6xl px-5 pt-8 pb-10">
        {tab === 'scout' ? (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
            <div className="lg:col-span-2 lg:sticky lg:top-20">
              <PipelineForm />
            </div>
            <div className="lg:col-span-3 space-y-6">
              <PipelineStatus />
              <CompetitorMap />
              <ReportViewer />
            </div>
          </div>
        ) : (
          <History />
        )}
      </section>
    </main>
  )
}
