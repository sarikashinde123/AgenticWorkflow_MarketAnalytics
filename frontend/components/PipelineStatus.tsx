'use client'
import { usePipelineStore, AgentState } from '@/lib/store'

function Node({ status }: { status: AgentState['status'] }) {
  const base = 'relative grid place-items-center h-8 w-8 rounded-md border shrink-0 transition-colors font-mono text-xs'
  if (status === 'done')
    return <div className={`${base} border-[rgba(55,208,166,.4)] bg-[rgba(55,208,166,.12)] text-[var(--confirm)]`}>
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
    </div>
  if (status === 'failed')
    return <div className={`${base} border-[rgba(242,84,45,.4)] bg-[rgba(242,84,45,.12)] text-[var(--alert)]`}>
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" /></svg>
    </div>
  if (status === 'running')
    return <div className={`${base} border-[rgba(245,165,36,.6)] bg-[rgba(245,165,36,.12)] text-[var(--signal)] ring-pulse`}>
      <svg className="spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8" stroke="currentColor" strokeOpacity=".3" strokeWidth="2.5" /><path d="M20 12a8 8 0 0 0-8-8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" /></svg>
    </div>
  return <div className={`${base} border-[var(--line-2)] bg-[rgba(255,255,255,.02)] text-[var(--mute)]`}>—</div>
}

const CHIP: Record<AgentState['status'], string> = {
  pending: 'border-[var(--line-2)] text-[var(--mute)]',
  running: 'border-[rgba(245,165,36,.3)] text-[var(--signal)] bg-[rgba(245,165,36,.1)]',
  done:    'border-[rgba(55,208,166,.3)] text-[var(--confirm)] bg-[rgba(55,208,166,.1)]',
  failed:  'border-[rgba(242,84,45,.3)] text-[var(--alert)] bg-[rgba(242,84,45,.1)]',
}
const CHIP_TEXT: Record<AgentState['status'], string> = {
  pending: 'standby', running: 'scanning', done: 'confirmed', failed: 'lost',
}

const fmt = (n: number) => n.toLocaleString()

function Unit({ agent, last }: { agent: AgentState; last: boolean }) {
  const active = agent.status === 'running'
  const hasTokens = agent.tokensIn > 0 || agent.tokensOut > 0
  return (
    <div className="relative flex gap-4 pb-3 last:pb-0">
      {!last && <span className="absolute left-4 top-9 bottom-0 w-px bg-gradient-to-b from-[var(--line-2)] to-transparent" />}
      <Node status={agent.status} />
      <div className={`flex-1 min-w-0 rounded-lg border p-3 transition-colors ${
        active ? 'border-[rgba(245,165,36,.28)] bg-[rgba(245,165,36,.05)]' : 'border-[var(--line)] bg-[rgba(255,255,255,.015)]'
      }`}>
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-baseline gap-2 min-w-0">
            <span className="font-mono text-[10px] text-[var(--mute)]">UNIT {String(agent.id).padStart(2, '0')}</span>
            <span className="text-sm text-[var(--bone)] truncate">{agent.label.replace(/^Agent \d+\s*[—-]\s*/, '')}</span>
          </div>
          <div className="flex items-center gap-2">
            {hasTokens && (
              <span className="font-mono text-[10px] text-[var(--dim)]" title="tokens: input / output">
                ↑{fmt(agent.tokensIn)} <span className="text-[var(--mute)]">·</span> ↓{fmt(agent.tokensOut)} tok
              </span>
            )}
            <span className={`chip border ${CHIP[agent.status]}`}>{CHIP_TEXT[agent.status]}</span>
          </div>
        </div>

        {/* live commentary while this agent runs */}
        {active && (
          <div className="mt-2 flex items-center gap-2 font-mono text-[11px] text-[var(--signal)]">
            <span className="blink">▸</span>{agent.activity}<span className="caret">&nbsp;</span>
          </div>
        )}
        {!active && (
          <div className="mt-1 font-mono text-[10px] text-[var(--mute)] truncate">{agent.model}</div>
        )}

        {active && agent.tokens && (
          <pre className="mt-2 text-[11px] leading-relaxed text-[var(--dim)] font-mono bg-black/40 rounded-md p-2.5
                          max-h-20 overflow-y-auto whitespace-pre-wrap break-words border border-[var(--line)]">
            {agent.tokens.slice(-300)}<span className="caret">&nbsp;</span>
          </pre>
        )}
      </div>
    </div>
  )
}

export default function PipelineStatus() {
  const { agents, status, error, runId, reset } = usePipelineStore()
  const total = agents.length
  const done = agents.filter(a => a.status === 'done').length
  const pct = Math.round((done / total) * 100)
  const idle = status === 'idle'
  const totalTokens = agents.reduce((s, a) => s + a.tokensIn + a.tokensOut, 0)
  const running = agents.find(a => a.status === 'running')

  return (
    <div className="panel rounded-xl p-6 animate-in">
      <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
        <div>
          <p className="eyebrow mb-1">
            Operation {runId && <span className="text-[var(--dim)]">#{runId.slice(0, 8)}</span>}
          </p>
          <h2 className="font-display text-2xl text-[var(--bone)]" style={{ letterSpacing: '-0.01em' }}>Recon sequence</h2>
        </div>
        {!idle && (
          <button onClick={reset} className="chip border border-[var(--line-2)] text-[var(--dim)] hover:text-[var(--bone)] hover:border-[var(--bone)] transition-colors">
            ↻ New op
          </button>
        )}
      </div>

      {!idle && (
        <>
          <div className="flex items-center justify-between font-mono text-[11px] text-[var(--mute)] mb-1.5">
            <span>{done} / {total} units confirmed</span>
            <span className="text-[var(--dim)]">
              {totalTokens > 0 && <>{fmt(totalTokens)} tokens · </>}{status === 'completed' ? '100%' : `${pct}%`}
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden mb-4">
            <div className={`h-full rounded-full transition-all duration-500 ${
              status === 'failed' ? 'bg-[var(--alert)]' :
              status === 'completed' ? 'bg-[var(--confirm)]' :
              'bg-[var(--signal)] bar-stripe'}`}
              style={{ width: `${status === 'completed' ? 100 : Math.max(pct, 5)}%` }} />
          </div>

          <div className={`flex items-center gap-2 font-mono text-[13px] px-3.5 py-2.5 rounded-lg mb-5 border ${
            status === 'completed' ? 'bg-[rgba(55,208,166,.08)] text-[var(--confirm)] border-[rgba(55,208,166,.2)]' :
            status === 'failed'    ? 'bg-[rgba(242,84,45,.08)] text-[var(--alert)] border-[rgba(242,84,45,.2)]' :
            'bg-[rgba(245,165,36,.08)] text-[var(--signal)] border-[rgba(245,165,36,.2)]'}`}>
            {status === 'running' && <><span className="blink">▸</span> {running ? `${running.activity}…` : 'Scanning your area of operations…'}</>}
            {status === 'completed' && <>✓ Recon complete — dossier ready.</>}
            {status === 'failed' && <>✗ {error || 'Recon failed'}</>}
          </div>
        </>
      )}

      {idle && (
        <p className="text-sm text-[var(--dim)] mb-5 rounded-lg border border-[var(--line)] bg-[rgba(255,255,255,.015)] px-3.5 py-2.5 leading-relaxed">
          Five units run in sequence — each hands its findings to the next, from discovery to the final dossier.
        </p>
      )}

      <div>{agents.map((a, i) => <Unit key={a.id} agent={a} last={i === agents.length - 1} />)}</div>
    </div>
  )
}
