import { create } from 'zustand'

export type AgentStatus = 'pending' | 'running' | 'done' | 'failed'
export type PipelineStatus = 'idle' | 'running' | 'completed' | 'failed'

export interface AgentState {
  id: number
  label: string
  model: string
  status: AgentStatus
  tokens: string
  tokensIn: number
  tokensOut: number
  activity: string   // human-readable "what it's doing"
}

const AGENTS: Omit<AgentState, 'status' | 'tokens' | 'tokensIn' | 'tokensOut'>[] = [
  { id: 0, label: 'Agent 0 — Business Discovery',  model: 'claude-sonnet-4-6',              activity: 'Searching the web for local competitors' },
  { id: 1, label: 'Agent 1 — Scraper Generator',   model: 'claude-opus-4-8',                activity: 'Planning what to research per competitor' },
  { id: 2, label: 'Agent 2 — Website Scraper',     model: 'claude-haiku-4-5-20251001',      activity: 'Gathering competitor data via web search' },
  { id: 3, label: 'Agent 3 — Deep Analyst',        model: 'claude-opus-4-8 + Extended Thinking', activity: 'Analysing pricing, features, reviews & gaps' },
  { id: 4, label: 'Agent 4 — Report Writer',       model: 'claude-opus-4-8 + Streaming',    activity: 'Writing the intelligence dossier' },
]

function freshAgents(): AgentState[] {
  return AGENTS.map(a => ({ ...a, status: 'pending', tokens: '', tokensIn: 0, tokensOut: 0 }))
}

interface PipelineStore {
  status: PipelineStatus
  runId: string | null
  agents: AgentState[]
  reportHtml: string
  pdfUrl: string | null
  error: string | null

  startPipeline: (input: {
    business_name: string
    business_type: string
    location: string
    search_radius_km: number
    mode?: 'market_overview' | 'gap_analysis'
    own_offerings?: string
  }) => Promise<void>
  reset: () => void
}

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  status: 'idle',
  runId: null,
  agents: freshAgents(),
  reportHtml: '',
  pdfUrl: null,
  error: null,

  reset: () => set({ status: 'idle', runId: null, agents: freshAgents(), reportHtml: '', pdfUrl: null, error: null }),

  startPipeline: async (input) => {
    set({ status: 'running', agents: freshAgents(), reportHtml: '', pdfUrl: null, error: null })

    // 1. Start the pipeline
    const res = await fetch(`${API}/api/pipeline/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
    if (!res.ok) {
      set({ status: 'failed', error: 'Failed to start pipeline' })
      return
    }
    const { run_id } = await res.json()
    set({ runId: run_id })

    // 2. Subscribe to SSE stream
    const es = new EventSource(`${API}/api/pipeline/${run_id}/stream`)

    es.addEventListener('agent_start', (e) => {
      const d = JSON.parse(e.data)
      set(s => ({
        agents: s.agents.map(a => a.id === d.agent_id ? { ...a, status: 'running' } : a)
      }))
    })

    es.addEventListener('agent_token', (e) => {
      const d = JSON.parse(e.data)
      set(s => ({
        agents: s.agents.map(a =>
          a.id === d.agent_id ? { ...a, tokens: a.tokens + (d.data ?? '') } : a
        )
      }))
    })

    es.addEventListener('agent_usage', (e) => {
      const d = JSON.parse(e.data)
      set(s => ({
        agents: s.agents.map(a =>
          a.id === d.agent_id ? { ...a, tokensIn: d.input_tokens, tokensOut: d.output_tokens } : a
        )
      }))
    })

    es.addEventListener('agent_done', (e) => {
      const d = JSON.parse(e.data)
      set(s => ({
        agents: s.agents.map(a => a.id === d.agent_id ? { ...a, status: 'done' } : a)
      }))
    })

    es.addEventListener('pipeline_done', async (e) => {
      const d = JSON.parse(e.data)
      // Fetch the rendered HTML report
      const rr = await fetch(`${API}/api/pipeline/${run_id}/report`)
      const html = rr.ok ? await rr.text() : ''
      // pdf_url is a relative path (/reports/...) served by the backend, not
      // the frontend — resolve it against the API base so the link works.
      const pdf = d.pdf_url ? `${API}${d.pdf_url}` : null
      set({ status: 'completed', reportHtml: html, pdfUrl: pdf })
      es.close()
    })

    es.addEventListener('error', (e: any) => {
      const d = e.data ? JSON.parse(e.data) : {}
      set({ status: 'failed', error: d.message ?? 'Pipeline error' })
      es.close()
    })

    es.onerror = () => {
      const s = get()
      // A server-sent "error" event (a real pipeline error) already set status
      // to 'failed' with a specific message and closed the stream — don't
      // clobber it with the generic connection message.
      if (s.status !== 'completed' && s.status !== 'failed') {
        set({ status: 'failed', error: 'SSE connection lost' })
      }
      es.close()
    }
  },
}))
