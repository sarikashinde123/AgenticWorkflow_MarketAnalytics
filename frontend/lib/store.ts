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
  { id: 1, label: 'Agent 1 — Scraper Generator',   model: 'claude-sonnet-4-6',              activity: 'Planning what to research per competitor' },
  { id: 2, label: 'Agent 2 — Website Scraper',     model: 'claude-haiku-4-5-20251001',      activity: 'Gathering competitor data via web search' },
  { id: 3, label: 'Agent 3 — Deep Analyst',        model: 'claude-sonnet-4-6 + Thinking',   activity: 'Analysing pricing, features, reviews & gaps' },
  { id: 4, label: 'Agent 4 — Report Writer',       model: 'claude-sonnet-4-6 + Streaming',  activity: 'Writing the intelligence dossier' },
]

function freshAgents(): AgentState[] {
  return AGENTS.map(a => ({ ...a, status: 'pending', tokens: '', tokensIn: 0, tokensOut: 0 }))
}

export interface CompetitorLocation {
  name: string
  website: string
  address: string
  phone?: string
  source?: string
  priority?: string
  notes?: string
  lat?: number
  lng?: number
}

export interface MapData {
  business: { name: string; location: string }
  competitors: CompetitorLocation[]
  center: { lat: number | null; lng: number | null }
  search_radius_km: number
}

export interface MapPreview {
  lat: number
  lng: number
  radiusKm: number
  label: string
}

interface PipelineStore {
  status: PipelineStatus
  runId: string | null
  agents: AgentState[]
  reportHtml: string
  pdfUrl: string | null
  error: string | null
  strictNoMatch: boolean
  mapData: MapData | null
  mapPreview: MapPreview | null

  setMapPreview: (p: MapPreview | null) => void
  startPipeline: (input: {
    business_name: string
    business_type: string
    location: string
    search_radius_km: number
    max_competitors?: number
    use_opus?: boolean
    strict_match?: boolean
    mode?: 'market_overview' | 'gap_analysis'
    own_offerings?: string
    latitude?: number | null
    longitude?: number | null
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
  strictNoMatch: false,

  mapData: null,
  mapPreview: null,

  setMapPreview: (p) => set({ mapPreview: p }),
  reset: () => set({ status: 'idle', runId: null, agents: freshAgents(), reportHtml: '', pdfUrl: null, error: null, strictNoMatch: false, mapData: null }),

  startPipeline: async (input) => {
    set({ status: 'running', agents: freshAgents(), reportHtml: '', pdfUrl: null, error: null, strictNoMatch: false })

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

    es.addEventListener('agent_done', async (e) => {
      const d = JSON.parse(e.data)
      set(s => ({
        agents: s.agents.map(a => a.id === d.agent_id ? { ...a, status: 'done' } : a)
      }))

      // When Agent 0 (Discovery) finishes, fetch competitor data for the map
      if (d.agent_id === 0 && !get().mapData) {
        console.log('[SSE] Agent 0 done, fetching competitor data via REST...')
        // Small delay to let the DB write complete
        await new Promise(r => setTimeout(r, 1000))
        try {
          const cr = await fetch(`${API}/api/pipeline/${run_id}/competitors`)
          console.log('[SSE] Agent 0 REST fetch status:', cr.status)
          if (cr.ok) {
            const data = await cr.json()
            console.log('[SSE] Agent 0 REST fetch data:', data)
            set({ mapData: data })
          }
        } catch (err) {
          console.error('[SSE] Agent 0 REST fetch error:', err)
        }
      }
    })

    es.addEventListener('competitors_discovered', (e) => {
      const d = JSON.parse(e.data)
      console.log('[SSE] competitors_discovered received:', d)
      console.log('[SSE] competitors count:', d?.competitors?.length)
      set({ mapData: d })
    })

    es.addEventListener('pipeline_done', async (e) => {
      const d = JSON.parse(e.data)
      const rr = await fetch(`${API}/api/pipeline/${run_id}/report`)
      const html = rr.ok ? await rr.text() : ''
      const pdf = d.pdf_url ? `${API}${d.pdf_url}` : null
      set({ status: 'completed', reportHtml: html, pdfUrl: pdf })

      // Fallback: fetch competitor map data if SSE event was missed
      if (!get().mapData) {
        console.log('[SSE] mapData is null at pipeline_done, trying REST fallback...')
        try {
          const cr = await fetch(`${API}/api/pipeline/${run_id}/competitors`)
          console.log('[SSE] REST fallback status:', cr.status)
          if (cr.ok) {
            const fallbackData = await cr.json()
            console.log('[SSE] REST fallback data:', fallbackData)
            set({ mapData: fallbackData })
          }
        } catch (err) {
          console.error('[SSE] REST fallback error:', err)
        }
      } else {
        console.log('[SSE] mapData already set at pipeline_done, skipping fallback')
      }

      es.close()
    })

    es.addEventListener('error', (e: any) => {
      const d = e.data ? JSON.parse(e.data) : {}
      const isStrictNoMatch = d.message === 'STRICT_NO_MATCH'
      set({
        status: 'failed',
        error: isStrictNoMatch ? (d.detail ?? 'No exact competitors found.') : (d.message ?? 'Pipeline error'),
        strictNoMatch: isStrictNoMatch,
      })
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
